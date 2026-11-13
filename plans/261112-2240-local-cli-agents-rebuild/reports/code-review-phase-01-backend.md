# Code review: Phase 1 backend (local CLI agents)

Date: 2026-11-13 (Asia/Saigon). Reviewer: code-reviewer (fresh context).
Scope: `git diff origin/preview...HEAD -- apps/api` (65 files, +6755/-56).
Status: COMPLETE. Counts: Critical 0, Important 3 (F1-F3), Minor 5 (F4-F8). Verdict: approve after F1-F3 are fixed; Minor items can follow.

## Findings

### F1 [Important] GitLab group can be re-attached through the generic attach endpoint (breaks "one token = one group")

- Where: `apps/api/plane/app/views/agent/git.py:194-206` (`AgentGitAccountAttachEndpoint.post`), contrast `:217-222` (remove refuses GitLab) and `apps/api/plane/agent/services/gitlab_connection.py:260-277`.
- Scenario: admin connects GitLab with group A, reconnects with group B on the same base URL (A becomes `detached` per the GL5 fix). `POST agent-git/gitlab/accounts/<A-id>/attach/` succeeds: A is `attached` again with token B. Old A bindings pass `binding_availability` (attached, connected, same host) and the catalog task calls `groups/<A>/projects` with token B. This is exactly the failure GL5 was written to prevent.
- Fix: refuse attach when `provider != github` (400 `account_attach_not_supported`, same as remove), plus a contract test.

### F2 [Important] GitHub reconnect by another GitHub user keeps the previous user's attached installations attached and their stale catalog bindable

- Where: `apps/api/plane/agent/services/github_connection.py:241-265` (`_store_connection` replaces token/identity, never touches accounts), `:290-325` (sync only adds/renames), `apps/api/plane/bgtasks/agent_git_catalog_task.py:101-108` (non-401 error keeps old snapshot).
- Scenario (the normal Q10 path): admin X connects, attaches org O. X leaves -> `reconnect_required`. Admin Y reconnects with a GitHub user that cannot see installation O. O stays `attached`; `/user/installations/O/repositories` returns 404 -> `github_unexpected_response` -> `catalog_error`, old snapshot kept. `GET repositories/` still lists O's repos and project create binds them (`resolve_binding_request` checks only state+status), `binding_availability` reports `available=true`. Failure surfaces only at clone/PR time in Phase 3/7. Q9 intent (the attachment is backed by the current token's visibility) is not held.
- Fix: when `connection.account_external_id` changes on connect, set the old accounts to `candidate` (or `detached`) in the same transaction, then sync; or after sync, demote attached accounts that `/user/installations` no longer returns. Add a test "reconnect as another GitHub user".
- F2 fix note: demote to `candidate`, never auto-attach (Q9).

### F3 [Important] The 30 s connect budget and the hostile-server limits do not bound the body read (slow trickle holds an API worker; catalog task has no budget at all)

- Where: `apps/api/plane/agent/git_providers/http.py:127-135` (`_read_capped` loops on `iter_content`; only the per-recv 10 s read timeout applies), `:199-202` (deadline checked only after the full read; the comment says so); `apps/api/plane/agent/git_providers/gitlab.py:46-55` + `apps/api/plane/bgtasks/agent_git_catalog_task.py:35-44` (catalog calls pass `deadline=None`).
- Scenario: any user who can create a workspace (allowed by default) is its admin. They point the GitLab connect form at a server they control that sends headers, then 1 byte every 9 s. Each recv returns before the 10 s read timeout, so `POST gitlab/connection/` holds a gunicorn worker for up to 1 MiB x 9 s; a few parallel requests exhaust the API pool. The same server, once connected, stalls a Celery worker per page (`MAX_PAGES=200`). Red-team GL6 required "one total budget of 30 s for all connect checks"; it is enforced only between calls. Seam test `test_budget_spent_during_a_call_fails_the_call` (`test_url_security.py` ~:523) patches `time.monotonic` around a completed read, so it cannot catch this.
- Fix: check `deadline` inside the chunk loop in `_read_capped` (raise `<provider>_url_unreachable`/timeout), and give each catalog page call its own deadline (for example `new_deadline(30)`). Add a seam test with an `iter_content` that yields slowly while `monotonic` advances past the deadline.

### F4 [Minor] Device-flow success is lost when the follow-up `/user` call fails

- Where: `apps/api/plane/agent/services/github_connection.py:189-217`, `:241-246`.
- Scenario: GitHub returns `access_token` (the device code is now consumed), then `GET api.github.com/user` times out or returns 5xx -> `ProviderError` -> the atomic block rolls back (status stays `pending`, the token pair is never stored or revoked) and the API returns 502. The next poll sends the consumed device code; GitHub answers with an error other than pending/slow_down/expired -> status `denied`. The admin entered the code correctly but must start again; an unused grant stays at GitHub until it expires. No secret leaks.
- Fix: on a token response, store the token pair (or mark the authorization terminal with `last_error`) before the identity call, or best-effort revoke via `DELETE /applications/{client_id}/token` when `_store_connection` fails.

### F5 [Minor] Untrusted provider JSON shapes crash with non-`ProviderError` exceptions

- Where: `apps/api/plane/agent/git_providers/gitlab.py:71-89` (`response.json() or []` iterated; `item["path_with_namespace"]`, `item["id"]`), `apps/api/plane/agent/git_providers/github.py:62-74`, `apps/api/plane/bgtasks/agent_git_catalog_task.py:101-109` (only `ProviderError` caught), `apps/api/plane/agent/services/gitlab_connection.py:198` (`int(access_level)`), `apps/api/plane/agent/git_providers/http.py:61-66` (`json.loads` on deeply nested 1 MiB body raises `RecursionError`, not caught).
- Scenario: a self-hosted GitLab (admin-chosen, untrusted per the plan) returns a dict instead of a list, an item without `path_with_namespace`, a `path_with_namespace` > 512 chars (`DataError` in `_swap_snapshot`), or a non-numeric `access_level`. The catalog task dies with a traceback and never sets `catalog_error`, so the admin sees a stale catalog with no reason; the connect endpoint returns a generic 500 instead of `gitlab_unexpected_response`.
- Fix: validate shapes in the clients (skip/raise `gitlab_unexpected_response`), truncate or skip over-length values, catch `RecursionError` in `HttpResponse.json`, and record `catalog_error` for any exception in the per-account loop.

### F6 [Minor/test] The IntegrityError -> 409 + rollback branch has no deterministic test

- Where: `apps/api/plane/app/views/project/base.py` (`_create_project_records`, `except IntegrityError: raise _RepositoryAlreadyBound()`), pre-check `apps/api/plane/agent/services/git_connection.py:134-137`; tests `apps/api/plane/tests/contract/app/test_agent_repository_binding.py:293-331` and `:450-...`.
- Scenario: both threaded tests (`transaction=True`, real threads, Barrier) pass through the `exists()` pre-check path whenever thread 1 commits before thread 2 resolves the binding. Then the second request gets 409 from `resolve_binding_request` before any project insert, and the rollback branch never runs. Deleting the `try/except IntegrityError` would leave these tests green on most runs (they become flaky, not red). The "no orphan project" red-team fix is therefore not pinned.
- Fix: add a test that patches the pre-check to miss (for example make `resolve_binding_request` skip the `exists()` or create the competing binding right after it) so the DB constraint fires, then assert 409 and zero new Project/ProjectMember/State rows.

### F7 [Minor] Bind and `binding_availability` ignore the Q10 connecting-admin rule until something else runs the check

- Where: `apps/api/plane/agent/services/git_connection.py:83-98`, `:122-127`; the check lives only in `github_connection.usable_token` and `GET connections/` (`apps/api/plane/app/views/agent/git.py:76-79`).
- Scenario: the admin who connected GitHub leaves. Until someone opens the Integrations page or a token user runs, members still bind GitHub repositories and the create response says `available: true`. The plan scopes Q10 to token users and `GET connection/`, so this is within the letter of the spec; impact is a misleading `available` flag.
- Fix (optional): call `github_connection.ensure_connected_admin(connection)` in `resolve_binding_request` and `binding_availability` for GitHub.

### F8 [Minor/docs] README overstates the host deny rule

- Where: `apps/api/plane/agent/git_providers/README.md` last paragraph vs `apps/api/plane/agent/services/gitlab_connection.py:92-100`.
- Scenario: README says "The Plane host itself and the domains in `WEBHOOK_DISALLOWED_DOMAINS` are always refused", but a host listed in `AGENT_GIT_ALLOWED_HOSTS` skips both checks. An operator who reads the README can wrongly assume the Plane host stays blocked.
- Fix: change the README sentence ("unless listed in `AGENT_GIT_ALLOWED_HOSTS`"), or apply the request-host check before the allowlist bypass.

## Verified as correct (no finding)

- Q15: DNS failure and blocked address both surface as `ValueError` from `resolve_and_validate` (`apps/api/plane/utils/ip_address.py:136-144`) -> one code `gitlab_url_not_allowed_or_unresolved` (`http.py:180-182`); the host-deny check uses the same code.
- `pinned_fetch` `verify` change: default `True` at every layer (`url_security.py:103,163,209`); existing callers pass no `verify`, so behavior is unchanged.
- CA bundle: private 0700 dir with owner/symlink check, mkstemp + chmod 0600 + `os.replace` (`http.py:74-104`); applies per request only.
- Encryption `""` handling: `encrypt_secret` raises, `decrypt_secret` returns `None` -> `reconnect_required` before any provider call (`git_connection.py:32-48`, `github_connection.py:417-419`, `gitlab_connection.py:292-294`).
- Serializers: explicit field lists, no token/device_code/ca_bundle fields; `_NoSecretsMixin` second guard. Celery task args carry the connection ID only. Log lines carry method/scheme/host/path/status only.
- Authorization: every write endpoint is `ROLE.ADMIN`; reads are ADMIN+MEMBER (guest 403); every object lookup is scoped by `workspace`/`workspace__slug` -> cross-workspace IDs give 404. Project create keeps its existing permission and the binding row is looked up with `workspace=workspace`.
- Refresh lock (`usable_token` `select_for_update`, re-read, save in same transaction) and device-poll lock (terminal state returned without a GitHub call) match the red-team fixes; both have `django_db(transaction=True)` + real-thread tests.
- GitHub disconnect uses `DELETE /applications/{client_id}/token` (not `/grant`), 404/422 treated as revoked, Q10 path clears without a call. GitLab disconnect makes no HTTP call.
- GitLab connect order: URL form -> host deny/allowlist -> CA -> `personal_access_tokens/self` -> `version` -> `user` -> group -> member; scopes `api`+`write_repository`; non-bot warning; other groups detached in the same transaction.
- `base_ref`: validated by `is_valid_ref_name` (leading `-`, `..`, `@{`, space, control chars, 255 bytes, `.lock`).
- Migrations 0126->0129 linear from `0125_reset_project_deploy_board_identity` (preview tip); lockfile `db: 0129_agent_git_policy`; conditional unique constraints and the `agent_git_repo_ws_owner_name` index match `agent_git.py`.
- Unrequested additions: `gitlab_url_invalid` (spec check 1 "URL form" had no code; leaks nothing) and `gitlab_disconnect_first` (implements "A different base URL needs Disconnect first") are acceptable. `git_providers/README.md` is acceptable apart from F8.
- Project soft-delete: `soft_delete_related_objects` soft-deletes a reverse OneToOne CASCADE row (`plane/bgtasks/deletion_task.py:63-80`), so the binding gets `deleted_at` and the conditional unique constraint and the `exists()` pre-check free the repository again. It runs in Celery, so the repository stays "already bound" for a short window after a project delete.
- `APITokenLogMiddleware` (`plane/middleware/logger.py:130-136`) persists bodies only when `X-Api-Key` is present; the new endpoints use session auth only (`plane/app/views/base.py:74`), so the GitLab connect body (token) is not logged on the normal path. A caller who sends `X-Api-Key` to a session endpoint still gets its body stored: pre-existing behavior, not a new path.
- Tests that passed on their first run (disconnect 2 cases, G3 10 cases, G5 3 cases, disclosed in the implementation report) assert behavior that earlier stories delivered; they are acceptance guards, not phantom tests. Seam tests call the real `http.request` and patch only `pinned_fetch`. The only weak spots are F3 (deadline test) and F6 (rollback branch).
