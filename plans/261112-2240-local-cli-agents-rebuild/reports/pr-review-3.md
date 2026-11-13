# PR review: kevinle128/plane#3 (feat/local-cli-agents -> preview)

Reviewed head `b2d9819f0e` on 2026-11-13 (Asia/Saigon). The review is read-only: no code changes and no GitHub posts.

## Summary

The PR covers Phase 1 of local CLI agents: connect GitHub (App, device flow) and self-hosted GitLab (Group Access Token), and bind one repository when a project is created. This review covers the 6 fix commits after `a98363f6f5`, a spot check of the rest of the code diff, and the PR body.

Most fixes are correct and have good tests: GitLab attach refused, release of installations on a GitHub user change, token revoke when the identity check fails, `created_at`, Plane-host refusal before the allowlist, untrusted JSON shapes, and the frontend F1 and F3-F13 fixes. The exception is the slow-body budget (backend F3). It holds only for `Content-Length` bodies. A hostile server can choose chunked framing or slow headers, and then the per-call budget has no effect. I reproduced this with the pinned `urllib3==2.8.0` / `requests==2.33.0`. The PR body says that this control works.

Diff size: 278 files, +151,534 / -113. Code (`apps/`, `packages/`) is +15,665. The other +135,869 (90%) are docs and design under three new top-level directories, and 105,648 of those lines are one generated JS bundle.

## Risk level

**High.** With the default instance settings (`ENABLE_SIGNUP=1`, `DISABLE_WORKSPACE_CREATION=0`), any user who signs up can stop Celery workers for all tenants, without a time limit. Everything else is Medium or lower.

## Checks run by this reviewer

| Check                                                                                                                                                                  | Result                                                                                                                                                                             |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pnpm --filter=@plane/blocks test`                                                                                                                                     | 425/425 passed (matches the PR body)                                                                                                                                               |
| Slow-server probe with the `_read_capped` / `_limit_socket_wait` logic copied as-is, `urllib3 2.8.0`, `requests 2.33.0`, Python 3.12, budget 3 s, per-read timeout 2 s | `Content-Length` body drip: stops at 3.0 s (fix works). Chunk-size line drip: 10.1 s. Trailer drip after `0\r\n`: 10.1 s and returns **success**. Status/header drip: 10.1 s       |
| `curl --http1.1 -H 'Accept-Encoding: identity'` on `api.github.com/meta`, `api.github.com/repos/...`, `gitlab.com/api/v4/projects`                                     | All plain `Content-Length`, no `Content-Encoding`. The new rule that refuses encoded bodies does not break the real providers                                                      |
| CI (`gh pr checks 3`)                                                                                                                                                  | 14/14 green, but **there is no pytest job and no Vitest job**. The backend numbers in the PR body (1877 passed, 378 phase tests) come from the author and I did not run them again |

## Findings

### Critical

**C1. The 30 s provider budget does not hold. A hostile GitLab host can stop the request thread and the Celery worker with no time limit.**

- `apps/api/plane/agent/git_providers/http.py:150` (`_read_capped`), `:143` (`_limit_socket_wait`), `:242`. The header phase runs inside `pinned_fetch` (`apps/api/plane/utils/url_security.py:221`).
- Evidence: `read1` makes one _raw_ read only for plain body bytes. With `Transfer-Encoding: chunked`, `http.client` reads each chunk-size line and the whole trailer with `readline()`, and `readline()` makes many socket reads. Each read resets the per-read timeout (`min(10 s, remaining)`), and the deadline is checked only between `read1` calls. Trailer discard has no line-count limit, so that phase has no upper bound. After the last chunk `read1` returns `b""`, and the loop returns success without a final deadline check. The status line and headers are read before `_read_capped` runs, so the deadline is never checked there. The probe above shows all three cases. The only real-socket test (`apps/api/plane/tests/unit/bg_tasks/test_url_security.py:448`, `:474`, `:584`) sends `Content-Length`, so it cannot find this.
- Who can do it: GitLab connect accepts any public HTTPS host (`gitlab_connection.py:96` refuses only the Plane host and the disallowed domains). The attacker's server answers the connect checks correctly, so `enqueue_catalog_refresh` runs (`apps/api/plane/app/views/agent/git.py:144`). The catalog task (`apps/api/plane/bgtasks/agent_git_catalog_task.py:31`, `MAX_PAGES = 200`) runs on the shared Celery pool. The worker starts with no time limit (`apps/api/bin/docker-entrypoint-worker.sh`: `celery -A plane worker -l info`), and `refresh_agent_git_catalog` sets none.
- Failure scenario: a user signs up and creates N workspaces. They are Admin of each. In each workspace they connect GitLab to `https://evil.example` (valid Let's Encrypt certificate). The server answers the connect checks, then answers `/groups/:id/projects` with `Transfer-Encoding: chunked`, `0\r\n`, and one trailer line every 9 s that never ends. Each catalog task keeps a prefork worker. When N is equal to the worker concurrency, emails, webhooks and notifications stop for all workspaces until the operator restarts the workers, and the attacker can do it again. The connect request itself can also be held with a header drip, which keeps an API thread and its DB connection.
- Severity: Critical with the default open signup and workspace creation, because one tenant affects all tenants and the PR says the control works. On a closed instance (only trusted admins), this is Important. In both cases it blocks the merge.
- Fix: a per-read timeout cannot limit a parse that makes many reads. Use an absolute deadline that closes the socket when the time is over. For example, start a timer that calls `sock.shutdown(SHUT_RDWR)` at the deadline. Arm it where the connection is created (`PinnedIPAdapter` / `_request_to_ip`), so that it also covers the status line and headers. Cancel it in `finally`. Also check the deadline once more after `_read_capped` returns. As a second limit, add `soft_time_limit`/`time_limit` to `refresh_agent_git_catalog`. Add a test that uses `_DrippingServer` with chunked framing (slow chunk-size line, slow trailer) and with slow headers.

### Important

**I1. The PR body claims things that the evidence does not support.**

- PR body, Safety line: "a 30 s budget that also covers slow body reads". C1 shows that this is false for chunked bodies and does not apply to headers.
- PR body, Test Scenarios: "All fixed with tests except one". The fix table in `phase-01-implementation-report.md` marks frontend F7, F10, F11 and F13 as "type check only" / "type check and lint". F12 "passes at once by design". So 4 fixes have no behavior test.
- PR body: "Code review ... 0 Critical": correct for the earlier reviews, but C1 is a Critical that remains after the fix.
- CI is green but does not run pytest or Vitest. The body does not say that the test numbers are local only.
- Fix: correct the Safety line, write "fixed; F7/F10/F11/F13 checked by type check only", and say that the test counts are from local runs.

**I2. The docs and design payload does not belong in this feature PR.**

- 146 files, +135,869 lines under `plans/`, `_bmad-output/` and `claude-design/`. None of these three directories exists on `preview` (`git ls-tree 6190932e2b`). This includes `claude-design/design_handoff_local_cli_agents/_ds/.../_ds_bundle.js` (105,648 lines, a generated Propel design-system bundle), `support.js`, a nested `_adherence.oxlintrc.json`, and 8,266 + 2,125-line JSON manifests.
- Cost: 90% of the diff is not reviewable code. The bundle stays in the history and adds to every clone. A nested oxlint config and loose `.js` files at the repo root can be picked up by later tool changes. `git log -p` and blame on these directories become noise.
- Fix: move the spec, plan and design handoff to a separate docs PR (or keep them outside the repo). Do not commit generated bundles: link to the source or store them as a release or artifact. Keep only the plan files that this PR references (`plans/261112-2240-local-cli-agents-rebuild/`), if the fork wants plans in the tree.

### Suggestion

**S1. Total time across chained budgets is still long where C1 does not apply.** `agent_git_catalog_task.py:31` `MAX_PAGES = 200` x `CALL_BUDGET_SECONDS = 30` (`http.py:47`) gives up to 100 min per account. `github_connection.py:309` `MAX_INSTALLATION_PAGES = 50` x 30 s runs in `_sync_after_connect` (`:223`, `:380`) while the device-authorization row lock and the connection row lock are held. The "known limit" in the PR body (about 60 s) describes only the identity-failure path. GitHub is a trusted host, so the risk is low. Add a shared deadline per task and per sync, or state the real limit in the body.

**S2. Catalog task: `except Exception` gives Plane errors a provider error code.** `agent_git_catalog_task.py:114`. This branch also catches DB errors from `_swap_snapshot`, and the admin then sees `<provider>_unexpected_response`. Use a separate code (for example `catalog_store_failed`), or catch only the shape errors.

**S3. The GitHub client does not guard `urlsplit` the way the GitLab client does.** `github.py:48`, `:77`. A hostile or malformed `clone_url` (for example `https://[::1`, or a value that is not a string) raises `ValueError`/`TypeError`. The whole account then fails through the catch-all in S2, but GitLab skips only that one repository (`gitlab.py` try/except around `urlsplit` and `.port`). Make the two clients act the same.

**S4. The Plane-host refusal uses the client-supplied Host header.** `gitlab_connection.py:96`, with `request.get_host()` at `views/agent/git.py:140` and `ALLOWED_HOSTS` defaulting to `"*"` (`settings/common.py:107`). A caller can send any `Host` and skip the check. Also, an IPv6 Host header (`[::1]:8000`) gives a host of `[`. The webhook serializer does the same (`app/serializers/webhook.py:51`), and the IP pinning is the real control, so this is defense in depth only. Use the host of `WEB_URL`/`APP_BASE_URL`.

**S5. Domain anchor of the shared UI logic.** Git-connection helpers (device flow, `git-errors.ts`, token expiry, provider terms) are in `packages/blocks/src/agent-run/`. "agent run" is a later-phase concept. A `git-connection/` (or `agent-git/`) subpath matches the content better and prevents a dumping-ground directory for all agent features. This is a judgment call, not a blocker.

**S6. PR body sections.** The body follows `.github/pull_request_template.md`, so this is not a blocker. Compared with the evidence-rich contract, the body has no "Deviations from plan" (against `phase-01-github-connection-and-repository.md`), no "Technical decisions" section, and no delegation note. It has a good "Not done / human actions" list and the "Relates to #1" / "Follow-up #2" links.

## Fix commits: verified correct (no finding)

- GitLab attach refused with 400 `account_attach_not_supported` before any lock or enqueue (`apps/api/plane/app/views/agent/git.py:203-208`). The test checks that the old group stays unattached.
- Reconnect as another GitHub user: `_store_connection` (`github_connection.py:270`) compares `account_external_id`, sets `attached` back to `candidate` (`:294`) in the same transaction, and leaves `detached` as it is. The repository list filters on `account__state=ATTACHED` and `connection__status=CONNECTED`, so stale repositories are not shown. All 3 tests check DB state.
- Identity failure (`_identity_or_revoke`, `:249`): the authorization becomes `denied`/`github_identity_failed`, the revoke is best-effort, and no connection row is stored. A second poll makes no token call. The tests check the revoke body (`{"access_token": ...}`) and the call count. The poll uses a blocking `select_for_update` (no 409 path), so the frontend rule "409 = stop" cannot end a valid flow.
- `created_at` is a read-only serializer field. The test sends a value from the client and shows that the server ignores it. Frontend `getDeviceCodeDeadline` uses `expires_at - created_at` and falls back correctly.
- Plane host is refused before the allowlist bypass, and an allowlisted host skips only `WEBHOOK_DISALLOWED_DOMAINS`. The README matches. The tests cover both orders.
- Untrusted JSON: `json_object()`, item-shape checks, `RecursionError`, `access_level`/`scopes` type checks, and `fits_catalog` column limits. Each has parametrized tests that check the error code and that nothing is stored.
- Frontend: `toAgentGitError` keeps `status`. Poll errors with 5xx/408/429/no status poll again, and other errors stop with a message. Denied reasons, the GitLab-only expiry warning, the connections error with Retry, Propel `Select`, and Enter in the search field were read in the diff. Each is consistent with its finding.
- `Accept-Encoding: identity` plus refusing encoded bodies: real GitHub and GitLab honor `identity` (curl check above).

## Verdict

**Request changes.** Blockers: C1 (fix the budget for chunked and header reads, and add a test), I1 (correct the PR body), I2 (move the docs and design payload to a separate PR, and drop the generated bundle). S1-S6 can follow later.

## Unresolved questions

- Does this fork run with open signup? If it is private, C1 is Important, but it still blocks because the PR body says the control works.
- Do you want the plans and design in this repo at all, or in a separate docs repo or branch?

Status: DONE
Summary: Request changes. The slow-body budget fix is bypassed by chunked framing and slow headers (reproduced). The PR body overstates the fix and its tests, and 90% of the diff is docs/design payload, including a 105k-line generated bundle.

## Re-review of the deadline fix

Commit `87777c8342` ("fix: end provider calls at an absolute deadline and limit the catalog task"), reviewed on 2026-11-13 (Asia/Saigon). Scope: the `apps/api` part only (6 source files, 2 test files).

### Checks run by this reviewer

- New and changed tests in the test container: `pytest plane/tests/unit/bg_tasks/test_url_security.py plane/tests/contract/app/test_agent_git_catalog.py` gives **110 passed in 18.55 s**. Each slow-server case takes about 1.01 s against a 1.0 s budget.
- Mutation check: the source files from `87777c8342^` with the new tests gave **14 failed, 4 passed**. All 8 slow-server cases that need the fix fail (chunk-size line, trailer lines, status line and headers; plain and TLS). The other new tests fail at import or on the missing constants. The 4 passes are expected: the 2 `fixed-length-body` cases (the old code already handled them), the complete-chunked-response test (a non-regression test), and the no-hook adapter test. So the tests are real and catch a regression.
- Connect probe (real sockets, in the container): a listener with a full accept queue (Linux drops the SYN, so `connect` hangs), 4 resolved addresses, `CALL_BUDGET_SECONDS = 1.5`, `CONNECT_TIMEOUT_SECONDS = 1.0`. Result: `gitlab_url_unreachable/timeout` after **4.04 s**, which is 4 times the connect timeout. The budget was 1.5 s. See I1-R.
- Read in urllib3 2.8.0 / requests 2.33.0 (the versions in `uv.lock`): `HTTPSConnection.connect` calls `_new_conn()` before the TLS wrap, and requests 2.33 calls `get_connection_with_tls_context` for both schemes. So the hook covers the TLS handshake, status line, headers, chunk-size lines, body and trailers.

### Critical

None.

### Important

**I1-R. The deadline does not cover TCP connect. Each resolved address can add a full connect timeout after the deadline.**

- `apps/api/plane/utils/url_security.py:141` (`_HookedConnection._new_conn`) calls `on_socket` only _after_ `super()._new_conn()` returns, that is, after TCP connect succeeded. `apps/api/plane/utils/url_security.py:316` (`for ip in ips`) tries every resolved address. `apps/api/plane/agent/git_providers/http.py:220` computes the connect timeout once, before the first address (`min(5 s, remaining)`).
- Result: a socket that is still in `connect` is not attached, so the timer cannot shut it down. When the deadline passed, the next address still gets a full connect timeout. Only after that connect succeeds does `attach` shut the socket down. The commit message ("from TCP connect to the last trailer byte") and the module docstring of `url_security.py` ("connect, TLS handshake, ...") claim more than the code does.
- This is not a regression: the connect behavior is the same as before the commit (the old `_timeouts()` computed the same value once, and the address loop did not change). The finding is that the commit says it covers connect, and the review task asked for connect coverage, but the code does not cover it.
- Evidence: the probe above. With 4 black-hole addresses, the call ends after 4.04 s for a 1.5 s budget. The overrun grows by `CONNECT_TIMEOUT_SECONDS` (5 s) for each address.
- Who can do it: the same actor as in C1. GitLab connect accepts any public HTTPS host, so the attacker controls DNS and can return tens of public A/AAAA records that drop SYN packets. `resolve_and_validate` does not limit the number of addresses. For example, 30 records give about 150 s for one provider call, not 30 s.
- Impact: much smaller than C1, because the time is now finite. The catalog task is also limited by the Celery soft limit (360 s, `agent_git_catalog_task.py:145`), and the shared deadline stops the later calls before they start. The remaining exposure is the synchronous GitLab connect request: each provider call there can hold an API thread for 5 s times the number of addresses, and the attacker can repeat it. This is the "connect request ... keeps an API thread" path of C1, and the fix says that it is closed.
- Fix (small): limit each connect attempt to the remaining deadline. For example, give `SocketDeadline` a `remaining()` method and pass the deadline object (not only `attach`) to the adapter. In `_HookedConnection._new_conn`, before `super()._new_conn()`, set `self.timeout = min(self.timeout, remaining)`, and raise `urllib3.exceptions.ConnectTimeoutError` when the deadline passed. Then the address loop ends fast after the deadline. Add a test with the full-accept-queue listener and 3-4 addresses (the probe is about 25 lines). Or, if you accept the bound, correct the commit text, the docstring and the PR body: "from the first byte after TCP connect; connect is limited to 5 s for each resolved address".

### Suggestion

**S1-R. S1 is fixed only for the catalog task.** `apps/api/plane/agent/services/github_connection.py:312` (`_list_installations`, `MAX_INSTALLATION_PAGES = 50`) still gives each page its own 30 s budget, and it runs in `_sync_after_connect` while row locks are held. GitHub is a trusted host, so the risk stays low. Pass one `new_deadline(...)` to all pages, as the catalog task does, or state the limit in the PR body.

**S2-R. After the shared deadline passes, the accounts that were not read get a timeout error.** `agent_git_catalog_task.py:120`, `:131`. For each later account, `_remaining` raises before any network call, and `_record_failure` writes `<provider>_url_unreachable` on it. The previous snapshot stays, so no data is lost, and the admin sees that the refresh did not run. This is acceptable. For a clearer message, stop the loop when the deadline passed, or use a reason such as `catalog_budget_exceeded`.

**S3-R. Timing margin in the slow-server tests.** `test_url_security.py:690` and `:712` assert `elapsed < budget + 0.5` with a 1.0 s budget. The measured time is 1.01 s, so the margin is large on a normal machine. On a loaded CI runner, the timer thread and the TLS handshake can use part of the 0.5 s. A margin of 1.0 s still proves the fix, because the server needs 5 s (`max_seconds`). The fork CI does not run pytest now, so the risk is low.

**S4-R. DNS resolution is outside the deadline.** `getaddrinfo` in `resolve_and_validate` runs before the first socket, and Python sets no timeout on it. The resolver timeouts in `resolv.conf` limit it (about 5 s per attempt and name server). This existed before the fix. Mention it in the docstring if you keep the list of phases.

### Verified correct (no finding)

1. Phases after connect: the hook in `_new_conn` runs before the TLS wrap (urllib3 2.8.0 `HTTPSConnection.connect`), so `shutdown` on the duplicate also ends a blocked TLS read. Plain HTTP uses `_SocketHookAdapter`, which requests 2.33 calls through `get_connection_with_tls_context`; the plain status-line/header case passes, so this is proven. Slow trailers: the `_remaining` check after the empty read (`http.py:167`) and the `expired` check (`http.py:256`) both turn a cut trailer into a timeout. Errors after expiry map to timeout first (`_fetch_error`; `http.py:262` for the body read).
2. `SocketDeadline` (`url_security.py:55-115`): `attach`, `_expire` and `cancel` change state under one lock. `cancel` sets `_closed` before it closes the duplicates, so `_expire` cannot shut down a closed duplicate. A socket attached after expiry or after `cancel` is shut down at once, and no duplicate is kept. `cancel` joins the timer (except on the timer thread itself), and a test checks that no `plane-socket-deadline` thread remains. When `dup()` fails, the socket is closed and the call fails as a connection error, so the call never runs without a deadline. The duplicate fds are closed on every exit path of the `with` block (`http.py:231`). When the timer fires during the normal close, it only shuts down a connection that is already closing. When it fires after a complete read but before the check at `:256`, the call returns a timeout; that agrees with the budget. Note: a duplicate keeps the connection of a failed address open until the call ends (the `close` of the original sends no FIN). This lasts one call only, so it is not a finding.
3. Callers that do not pass `on_socket` (webhooks `webhook_task.py:317`, link unfurl `work_item_link_task.py:96` and `:194`, auth adapter `authentication/adapter/base.py:156`): for HTTPS, `PinnedIPAdapter` overrides `get_connection_with_tls_context` without `super()`, and `_hook_pool` does nothing when `on_socket` is `None`. For HTTP, no adapter is mounted, and a test checks that `session.mount` is not called. The behavior is the same as before.
4. Catalog task: one `new_deadline(300)` for all pages and accounts (a test checks that all 3 calls get the same deadline). Soft limit 360 s, hard limit 390 s. `except SoftTimeLimitExceeded` comes before `except Exception`, so the catch-all cannot hide it and go on. A soft limit inside `_swap_snapshot` rolls back its `transaction.atomic` block. Then only the current account gets `url_unreachable`, and the earlier snapshot stays (the test checks the snapshot and the other account). The worker uses the default prefork pool (`bin/docker-entrypoint-worker.sh`), where soft limits work.
5. Tests: real local sockets, plain and TLS (self-signed certificate passed as `ca_bundle`). A broken client fails after `max_seconds = 5`; it does not hang. The mutation check shows that the new cases fail on the old code.

### Verdict

**Request changes (one Important).** C1 is fixed for every phase after TCP connect, and real-socket tests prove it. The catalog-task part of S1 is fixed. I1-R is open: connect is not covered when a host has several addresses, but the commit message and the docstring say that it is. Either limit each connect to the remaining deadline (a small change and one test), or correct the claim and accept the bound of 5 s for each address. S1-R to S4-R can follow later.

### Unresolved questions

- Do you accept the connect bound of 5 s for each resolved address in the synchronous GitLab connect request? If yes, I1-R becomes a documentation fix only.

Status: DONE
Summary: The deadline fix holds for the TLS handshake, status line, headers, chunk-size lines, body and trailers (110 tests pass, and the new cases fail on the old code). One Important remains: TCP connect is outside the deadline, and each resolved address adds up to 5 s (probe: 4.04 s for a 1.5 s budget).

## Final re-review of the connect deadline fix

Commit `c4d3cb156a` ("fix: limit TCP connect on every resolved address to the call deadline"), reviewed on 2026-11-13 (Asia/Saigon). Scope: the `apps` part only (3 source files, 2 test files). It closes I1-R, S1-R and S3-R of the section above.

### Checks run by this reviewer

- Tests in the test container: `pytest test_url_security.py test_agent_git_catalog.py test_agent_github_installations.py` gives **136 passed in 27.05 s**. The new connect test ran (it was not skipped) and took 1.81 s, including about 0.3 s to fill the accept queue.
- Read in urllib3 2.8.0 (the container version): `HTTPConnectionPool._make_request` sets `conn.timeout` to the connect timeout before the connect and to the read timeout after the request is sent. `HTTPConnection._new_conn` passes `self.timeout` to `create_connection`, and `timeout` is a plain attribute (no property in the MRO). So the value set in `_DeadlineConnection._new_conn` is the value that `connect` uses.
- Connect probe (real sockets, full accept queue, 4 addresses, `CONNECT_TIMEOUT_SECONDS = 1.0`), with `create_connection` instrumented:
  - Budget 1.5 s: address 1 waits 1.0 s, address 2 gets `timeout=0.493` and ends at 1.502 s, addresses 3 and 4 raise before `create_connection`. Result `gitlab_url_unreachable/timeout` at **1.505 s** (was 4.04 s before the fix).
  - Budget 1.1 s: **1.106 s**.
  - Same probe without the clamp line: **2.02 s** for both budgets.
- Mutation checks on a copy of the code in the container: see S1-F.
- Tested tree: HEAD `52db1522f5`. That commit changes only `phase-01-implementation-report.md`, so the `apps` code is the code of `c4d3cb156a`.
- Note on the method: the `api-tests` service bind-mounts `./apps/api` to `/code`. My first mutation run edited the worktree file through the mount. I restored it with `git checkout -- apps/api/plane/utils/url_security.py` and confirmed a clean `git status` (only this report is untracked). The 136-pass run was made before that run. The probe numbers above come from the restored code. All later mutations ran on a copy in `/tmp` inside the container.

### Critical

None.

### Important

None.

### Suggestion

**S1-F. The connect test does not detect removal of the clamp.** `apps/api/plane/tests/unit/bg_tasks/test_url_security.py:758-779`. Two mechanisms limit the connect: the clamp (`url_security.py:164`, `self.timeout = min(self.timeout, remaining)`) and the stop when no time remains (`url_security.py:158` in `_new_conn`, `url_security.py:340` in the address loop). Mutation results for the three new tests (hanging connect, no address after the deadline, `remaining()`):

- Clamp removed only: **3 passed**. Without the clamp, the call takes 2.02 s, which is less than the assertion `budget + 1.0 = 2.5 s`.
- Clamp and the loop check removed: 1 failed (`test_no_address_is_tried_after_the_deadline`).
- Clamp, loop check and the check in `_new_conn` removed: 2 failed (the hanging-connect test fails at about 4 s).

So the real-socket test proves "no address after the deadline", and the clamp has no test. Without the clamp, the overrun is at most one `CONNECT_TIMEOUT_SECONDS` (5 s), not one per address, so the risk is small. Fix (preferred): use `CONNECT_TIMEOUT_SECONDS = 2.0` with `budget = 2.5` and keep the margin of 1.0 s (clamped about 2.5 s, unclamped about 4.0 s). It costs 1 s more test time and keeps the margin for a loaded runner. Alternative: `CONNECT_TIMEOUT_SECONDS = 1.0` with `budget = 1.1` and assert `elapsed < budget + 0.6` (clamped 1.106 s, unclamped 2.02 s; only about 0.3 s between the limit and the unclamped time).

**S2-F. The installation sync deadline test checks only an upper bound.** `apps/api/plane/tests/contract/app/test_agent_github_installations.py:171-176` asserts `deadline <= started + 61`. A smaller shared budget (for example 30 s) also passes. Add `deadline >= started + INSTALLATION_SYNC_BUDGET_SECONDS - 1` if the 60 s value matters. Low value; optional.

**S3-F. Lock hold time in the device poll is still more than 60 s in the worst case.** `github_connection.py:164-224`: the poll holds the authorization row lock (and, from `_store_connection`, the connection row lock) through the token exchange (own 30 s budget), the identity call (30 s), a possible revoke (30 s) and now the installation sync (60 s, shared). The worst case is about 150 s, down from about 25 min (50 pages x 30 s). All hosts are the fixed `github.com` / `api.github.com`, so only a GitHub outage can cause it, and a second poll waits on the lock and then sees the terminal state. Acceptable; no change requested. The explicit sync endpoint (`app/views/agent/git.py:186`) holds no row lock.

**S4-F. The connect test needs Linux.** `_FullAcceptQueueListener` (`test_url_security.py:551`) skips only when 127.0.0.1 does not hold a connect. It does not check 127.0.0.2-4. On macOS, those addresses are not configured on `lo0` by default, so a local run outside Docker probably fails with a connection error and does not skip (not tested). The documented test path is the Linux container, so this is informational.

### Verified correct (no finding)

1. Connect limit on every address: `_DeadlineConnection._new_conn` (`url_security.py:156-167`) reads `remaining()` per connection, so each resolved address gets `min(connect timeout, remaining)`. It raises `ConnectTimeoutError` when no time remains, and `_fetch_validated_hop` (`url_security.py:339-342`) stops the loop before it builds another session. Probe: 1.505 s for a 1.5 s budget. The clamp also limits the TLS handshake, because `create_connection` sets the same socket timeout and the pool changes it only after the request is sent. Each address uses a new `Session`, so no pooled connection skips `_new_conn`.
2. Error mapping: `ConnectTimeoutError` from `_new_conn` goes through urllib3 `urlopen` (no retry: requests uses `Retry(0, read=False)`) and becomes `requests.exceptions.ConnectTimeout`. The loop check raises `ConnectTimeout` directly. Both are `requests.exceptions.Timeout`, so `_fetch_error` (`http.py:186`) returns the existing timeout reason, also when the timer has not set `expired` yet. The probe and the test assert `("gitlab_url_unreachable", "timeout")`.
3. Callers without a deadline: `pinned_fetch` in `webhook_task.py:317` and `work_item_link_task.py:194`, and `pinned_fetch_following_redirects` in `authentication/adapter/base.py:156`, pass no `deadline`. `_hook_pool` does nothing when `deadline` is `None`, plain HTTP mounts no adapter, and `_request_to_ip` does not pass `deadline` to `session.request` (`test_url_security.py:927`). The no-deadline path is the same as before.
4. No leftover `on_socket`, `socket_hook`, `_SocketHookAdapter` or `_connection_class_with_hook` in `apps/` or `packages/`. Only a test name (`test_without_a_socket_hook_the_plain_http_adapter_is_kept`) still uses "socket hook"; harmless.
5. `remaining()` thread safety (`url_security.py:92-96`): it reads `_ends_at` (set once in `__init__`, before the timer starts) and the bool `_expired`, and calls `time.monotonic()`. It needs no lock. A stale read while the timer fires can return a small positive value; then the connect starts, and `attach` shuts the new socket down at once because the deadline already expired. The same monotonic clock is used by `http.new_deadline`, so the two deadlines agree.
6. Installation sync: one `new_deadline(60)` for all pages (`github_connection.py:317-325`); the test proves both pages get the same deadline. A timeout in `_sync_after_connect` is caught as `ProviderError` and logged; the connection stays and the admin can sync again.
7. Test stability on Linux: with `listen(0)`, the second filler times out after 0.3 s and the queue stays full, so later SYNs are dropped and `connect` waits. If the queue fill fails on a loaded host, the request is accepted into the queue and waits on the read, and the deadline still ends it with the timeout reason. The 1.0 s margins of the slow-server tests (S3-R) leave a large gap to the 5 s that the server needs.

### Verdict

**Approve.** No Critical or Important finding. I1-R is fixed: the connect on each resolved address waits at most the remaining time, and no address is tried after the deadline (probe 1.505 s for a 1.5 s budget, was 4.04 s). S1-R and S3-R are fixed. The docstrings now state the real coverage (TCP connect to the last trailer byte, DNS outside), which also closes S4-R. S1-F (a test for the clamp) is recommended but does not block.

### Unresolved questions

- None.

Status: DONE
Summary: The connect deadline fix is correct; real-socket probes give 1.505 s for a 1.5 s budget across 4 hanging addresses, and 136 tests pass. Approve; one suggestion: the connect test does not catch removal of the per-address clamp (it passes at 2.02 s), so tighten its budget or margin.
