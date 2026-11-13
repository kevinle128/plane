# Red team review: Local CLI Agents rebuild plan

- Date: 2026-11-12 (Asia/Saigon)
- Plan: `plans/261112-2240-local-cli-agents-rebuild/` (plan.md, phase-01..07, architecture-contracts.md, story-coverage.md)
- Codebase: worktree `local-cli-agents`, branch `feat/local-cli-agents` at `febd8b8071` (on `preview` `6190932e2b`)
- Lenses: Assumption Destroyer, Failure Mode Analyst, Scope & Complexity Critic, Security Adversary (7 phases, so all 4)
- Execution note: the workflow asks for 4 parallel reviewer subagents and an `ask_user` step. This run had no subagent or ask-user tool, so one reviewer applied the 4 lenses in sequence. The lead's brief authorised direct edits for findings that do not touch user decisions; those edits are applied and marked `<!-- red-team 2026-11-12 -->` in the phase files. Surface-to-user items are not applied.
- Focus: Phase 1 (implemented next). Every Phase 1 path, model parent, endpoint parent, migration number and test command was checked against the worktree.

## Phase 1 fact check (what was verified correct)

| Plan claim | Evidence | Result |
| --- | --- | --- |
| Next migration is `0126` | `apps/api/plane/db/migrations/0125_reset_project_deploy_board_identity.py`; `apps/api/migrations_lockfile.txt` `db: 0125_...` | Correct |
| `encrypt_data` at `encryption.py:20` | `apps/api/plane/license/utils/encryption.py:20` | Correct (but see F5) |
| GitHub login keys at `core.py:73` | `apps/api/plane/utils/instance_config_variables/core.py:65-96` | Correct |
| `ProjectViewSet.create` at `base.py:259-313`, `allow_permission([ADMIN, MEMBER])` | `apps/api/plane/app/views/project/base.py:258-313` | Correct |
| `ProjectSerializer` at `project.py:31` | `apps/api/plane/app/serializers/project.py:31-37`, `fields = "__all__"` | Correct |
| Settings routes `core.ts:258-285` | `apps/web/app/routes/core.ts:258-285` | Correct |
| Settings tabs `workspace.ts:29-81` | `packages/constants/src/settings/workspace.ts:29-81` | Correct |
| Integrations page admin gate at `page.tsx:39` | `.../settings/(workspace)/integrations/page.tsx:34-40` | Correct |
| Test dirs `plane/tests/contract/app`, `plane/tests/unit` | exist; `pytest.ini` strict markers `unit`, `contract` | Correct |
| Docker pytest command and paths | `docker-compose-test.yml`: `working_dir: /code`, mount `./apps/api:/code`, entrypoint ends `exec "$@"` | Correct |
| `pnpm --filter=@plane/blocks test` | `packages/blocks/package.json` `test: vitest run --project=unit --project=dom`; `repository-list.test.ts` matches `src/**/*.test.ts` | Correct |
| `pnpm --filter=@plane/i18n check:sync` | `packages/i18n/package.json` `check:sync` | Correct |
| `./agent-run` blocks export builds | `packages/blocks/tsdown.config.ts` entry `src/*/index.ts`; exports point at `dist/`; turbo `check:types` dependsOn `^build` | Correct |
| `pnpm check:format`, `pnpm check:lint` | root `package.json` scripts | Correct |
| Settings access key for `/settings/integrations/github` | `apps/web/components/settings/helper.ts:30-35` takes path segments 1-2, so one `integrations` entry gates both routes | Correct |

## Findings

Severity: Critical blocks success; High is significant risk; Medium is notable. Sorted by severity. Cap 15 kept by merging related items.

### F1. Project create plus repository binding is not atomic; a bind race returns 500 and leaves a project with no binding (High, Failure)

- Location: Phase 1, Refactor and story 1.5.
- Flaw: The plan extends `ProjectViewSet.create` with a nested `repository` but does not say that the project row, members, states and binding commit together.
- Evidence: `apps/api/plane/app/views/project/base.py:262-296` saves the project, then `ProjectMember.objects.create`, then `State.objects.bulk_create`, with no `transaction.atomic`. No `ATOMIC_REQUESTS` in `apps/api/plane/settings/` (grep empty; also recorded in `architecture-contracts.md:27`). The binding has a partial unique constraint (workspace, github_repository_id) (`architecture-contracts.md:52`).
- Failure scenario: Two members create projects bound to the same repository at the same time. Both pass the serializer "already bound" check. The second insert of the binding raises `IntegrityError` after its project, member and state rows already exist. The client gets HTTP 500 and a project exists without the repository the user selected. The plan's "duplicate bind 409" test (phase-01:95) passes in a serial test and does not catch this.
- Also: `ProjectSerializer` uses `fields = "__all__"` (`project.py:35`). A nested `repository` field must be popped before `Project.objects.create`, or the save raises `TypeError`.
- Action: fixed-in-plan. Phase 1 Refactor now requires one `transaction.atomic` block for project, members, states and binding, `IntegrityError` mapped to 409, and the `model_activity.delay` call kept after the block. Test added: concurrent bind of one repository gives one 201 and one 409 and leaves no orphan project.

### F2. Binding trusts client input: cross-workspace repository IDs and an unvalidated `base_ref` reach later git commands (High, Security)

- Location: Phase 1, story 1.5; consumer Phases 3 and 7.
- Flaw: The plan says the API "stores one identity and base ref" but does not say where the identity comes from or how `base_ref` is validated.
- Evidence: Binding stores `github_repository_id`, `full_name`, `clone_url`, `base_ref` (`architecture-contracts.md:52`). Phase 3 clones from the binding (`phase-03:28`); Phase 7 creates a Worktree and branch from it (`phase-07:37`). 1.5 tests (`phase-01:95`) cover duplicate and unavailable only.
- Failure scenario A: a member posts a `github_repository_id` from another workspace's catalog, or posts `full_name`/`clone_url` directly. If the view copies client fields, the Worker later clones an attacker-chosen URL. Failure scenario B: `base_ref = "--upload-pack=..."` or `"main;..."` is stored and later passed to `git fetch`/`git worktree add`, which is git argument injection on the Mac Mini.
- Action: fixed-in-plan. 1.5 now requires: the request carries only the catalog row ID and an optional `base_ref`; `full_name`, `clone_url` and installation come from the workspace's own catalog row under an active grant; `base_ref` defaults to the repository `default_branch` and must pass `git check-ref-format` rules (no leading `-`, no `..`, no control characters, max length). Tests added: other-workspace catalog ID returns 404; client-supplied `clone_url` is ignored; invalid `base_ref` returns 400.

### F3. GitHub App refresh tokens are single-use; concurrent refresh breaks the connection (High, Failure)

- Location: Phase 1, story 1.1 ("token encrypt, refresh"); consumers Phase 1 catalog task, Phase 7 PR creation and mirror task.
- Flaw: No serialisation of token refresh is specified.
- Evidence: GitHub docs (https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/refreshing-user-access-tokens): "Once you use a refresh token, that refresh token and the old user access token will no longer work." Access tokens expire after 8 h. Plan callers that need a fresh token at the same time: catalog Celery task (`phase-01:27`), PR creation (`phase-07:41`), mirror Celery task (`phase-07:42`). Connection model has one refresh token (`architecture-contracts.md:48`).
- Failure scenario: 8 h after connect, the catalog refresh task and a PR creation both see an expired token and both refresh. One succeeds and rotates the pair; the other sends the now-dead refresh token, gets `bad_refresh_token`, and marks the connection failed or writes its stale result over the good pair. All GitHub access stops until an admin reconnects. A crash between the GitHub response and the DB save has the same result.
- Action: fixed-in-plan. Phase 1 key decision added: refresh runs in `github_connection.py` under `select_for_update` on the connection row, re-reads the token after the lock, refreshes only if still expired, and saves the new pair in the same transaction. Test added: two concurrent refresh calls cause one GitHub refresh call.

### F4. Disconnect with the grant endpoint also disconnects every other workspace connected by the same GitHub user (Medium, Assumption)

- Location: Phase 1, story 1.4 ("revoke token at GitHub").
- Evidence: GitHub docs (https://docs.github.com/en/rest/apps/oauth-applications): "Deleting an application's grant will also delete all OAuth tokens associated with the application for the user." `DELETE /applications/{client_id}/token` revokes one token. Both use Basic auth with client ID and secret, which Q3 supplies. Connection is per workspace (`architecture-contracts.md:48`), so one GitHub user can connect several workspaces on one instance.
- Failure scenario: an admin connects workspaces W1 and W2 with the same GitHub account. Disconnect in W1 calls the grant endpoint, and W2's next GitHub call fails with 401.
- Action: fixed-in-plan. 1.4 now names `DELETE /applications/{client_id}/token` and adds a test that disconnect of W1 sends only W1's token. Follow-up: the body needs the access token, which expires after 8 h, and GitHub documents only 204 and 422 for this endpoint. The plan now refreshes an expired token through the locked function before revoke, treats 404 or invalid-token 422 as already revoked, and keeps the connection only on network errors or 5xx; tests added.

### F5. `encrypt_data`/`decrypt_data` swallow errors and return an empty string (Medium, Failure)

- Location: Phase 1 key decision "Store tokens and device codes with `encrypt_data`".
- Evidence: `apps/api/plane/license/utils/encryption.py:20-31` and `:34-44` catch every exception, log it, and return `""`.
- Failure scenario A: encryption fails, the connection is saved as `connected` with an empty token, and every later call fails with a misleading GitHub 401. Failure scenario B: `SECRET_KEY` changes; `decrypt_data` returns `""`; the client sends `Authorization: token ` and loops on 401 instead of showing "reconnect required".
- Action: fixed-in-plan. 1.1 now requires the service to reject an empty ciphertext before `status=connected`, and to treat an empty decrypt of a non-empty stored value as `reconnect_required`. Tests added for both.

### F6. Q3 fallback is not what `get_configuration_value` does (Medium, Assumption)

- Location: Phase 1 key decision and Files (`core.py`); decision Q3.
- Evidence: `apps/api/plane/license/utils/instance_value.py:17-39`: with `SKIP_ENV_VAR`, a key that exists in the DB returns its stored value, also when that value is `""`; env is used only as the default when the key row is absent. `apps/api/plane/license/management/commands/configure_instance.py:28-37` copies env into the DB once, at row creation, and then never again.
- Failure scenario: the operator boots once without the env vars, so empty rows are created. Later they set `GITHUB_APP_CLIENT_ID` in env as Q3 allows. Plane still reads `""` and the device flow fails with a misleading "not configured" error.
- Action: fixed-in-plan. This implements Q3 exactly; it does not change it. Phase 1 adds one accessor in `github_connection.py` that returns the DB value when it is non-empty and the env value otherwise, with a test for "DB empty, env set". New keys use distinct names (not the existing `GITHUB_CLIENT_ID` login keys at `core.py:74-85`) so GitHub login and the GitHub App do not share credentials.

### F7. Phase 1 Files list misses files that typecheck, i18n loading and Q3 need (Medium, Fact check)

- Location: Phase 1, Files.
- Evidence and failure:
  - `packages/types/src/settings.ts:13` defines `TWorkspaceSettingsTabs` as a closed union. Adding an `integrations` key in `workspace.ts` without this file fails typecheck.
  - `apps/web/components/settings/workspace/sidebar/item-icon.tsx:19` is `Record<TWorkspaceSettingsTabs, ...>`. After the union grows, a missing `integrations` icon fails typecheck.
  - `packages/i18n/src/constants/namespaces.ts:7-36` lists every namespace that loads (`core/instance.ts:21` imports `locales/<lang>/<namespace>.json`). A new `agent.json` that is not in this list never loads; the UI shows raw keys. `check:sync` does not detect this.
  - `packages/constants/src/index.ts` re-exports each module; `agent.ts` is not exported without an edit.
  - Q3 names the admin app as the source of the App credentials. The existing admin GitHub form is `apps/admin/app/(all)/(dashboard)/authentication/github/form.tsx` and `apps/admin/components/authentication/github-config.tsx`, typed by `packages/types/src/instance/auth.ts`. The instance PATCH (`apps/api/plane/license/api/views/configuration.py:43-59`) only updates keys that already exist, so the new keys must be in `core.py` and need an admin form to be set.
- Action: fixed-in-plan. Files list extended. Phase 1 lines that used `app/(all)/...` without the `apps/web/` prefix are normalised.

### F8. Installation removal cannot call GitHub with the Q3 credentials (Medium, Assumption)

- Location: Phase 1, story 1.3 ("GitHub error keeps installation and returns actionable error").
- Evidence: GitHub docs (https://docs.github.com/en/rest/apps/apps#delete-an-installation-for-the-authenticated-app): "You must use a JWT to access this endpoint." A JWT needs the App private key; Q3 supplies client ID, secret and slug only (`plan.md:68`). Story 1.3 says "remove one GitHub installation from Plane" (epics.md:438).
- Failure scenario: the implementer tries to uninstall at GitHub, cannot authenticate, and either adds a private-key setting outside Q3 or ships a test against a call that can never succeed in production.
- Action: fixed-in-plan. 1.3 is defined as a Plane-side detach (`removed_at`), with a link to the GitHub installation settings for a full uninstall. The "removal fails" AC is tested as a failed detach transaction (installation stays visible, error returned). Q3 is unchanged. Follow-up: `/user/installations` still returns a detached installation, so sync must never clear `removed_at`; an admin re-adds it explicitly. Test added: detach, then sync, installation stays removed. This explicit re-add is the same gesture as option (b) of F13.

### F9. Device-flow poll has no concurrency guard (Medium, Failure)

- Location: Phase 1, story 1.1, `POST device-authorizations/<id>/poll/`.
- Evidence: `phase-01:70` and `:91` describe start, poll, cancel with no lock or terminal-state rule. GitHub returns the token once per device code.
- Failure scenario: two browser tabs (or a double click on "I entered the code") poll at the same time. Poll A gets the token and creates the connection. Poll B gets an error for the used code and writes `denied`/`expired` over `completed`, so the UI shows a failure while a connection exists, or a second connection insert hits the workspace 1:1 constraint and returns 500.
- Action: fixed-in-plan. Poll takes `select_for_update` on the authorization row, returns the stored result when the row is already terminal, and upserts the connection. Test added.

### F10. Phase 3 verification command skips all agent contract tests (Medium, Fact check)

- Location: Phase 3, Verification line 86.
- Evidence: `pytest plane/tests/contract/app -k "agent_run or ..." plane/tests/unit -k "mention"`. pytest keeps only the last `-k`, so both paths run with `-k mention`. Every `agent_run`, `agent_worker` and `agent_conclusion` contract test is deselected and the command still exits 0.
- Action: fixed-in-plan. Split into two invocations.

### F11. Two Epic 1 acceptance criteria have no test in any phase (Medium, Scope audit)

- Location: story-coverage.md rows 1.4 and 1.8; Phases 3 and 7.
- Evidence: epics.md:472 (1.4: "new Agent launches or pending pull-request delivery fail with a clear missing-connection reason") and epics.md:588 (1.8: "that Run keeps its existing branch name"). No phase Tests After names either (grep of phase-03..07 for `branch_format`, `github_disconnected`, `keeps its existing branch`: no match). Phase 1 cannot test them because Runs do not exist yet.
- Failure scenario: Phase 1 is marked done with these ACs unproven, and Phase 7 never adds them.
- Action: fixed-in-plan. Phase 7 3.1 Tests After gains both cases; Phase 3 2.7 gains "launch with a disconnected connection fails with `github_disconnected`"; story-coverage notes the deferral. Phase 1 success criteria note that 1.4 AC 2 and 1.8 AC 4 close in Phases 3 and 7.

### F12. Local `makemigrations --check` command does not run as written (Medium, Fact check)

- Location: Phase 1 Verification line 104 and the same line in Phases 2-5 and 7; architecture-contracts §7.
- Evidence: `apps/api/manage.py:10` defaults to `plane.settings.production`; settings do not load `.env` (no `dotenv` in `plane/settings/common.py`); CI supplies `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL` (`.github/workflows/migration-check.yml:33-39`). `uv` must be exactly the version pinned in `apps/api/pyproject.toml` (AGENTS.md). In this environment the command failed on the uv version (0.10.9 installed vs 0.12.21 required); that part is environment, not plan.
- Action: fixed-in-plan. Phase 1 runs the check in the test container, where the env and uv are correct: `docker compose -f docker-compose-test.yml run --rm api-tests python manage.py makemigrations --check --dry-run`. Ruff stays on the host with the note that uv must match. Architecture-contracts §7 updated so later phases inherit the fix.

### F13. Installation scoping: one admin's GitHub token decides what every member can bind (High, Security) - surface to user

- Location: Phase 1 key decision 1 and story 1.2; architecture-contracts.md:48-50.
- Evidence: the connection is workspace 1:1 with one admin's user-to-server token (`architecture-contracts.md:48`). `/user/installations` returns every installation of the App that this GitHub user can access, including their personal account and other organisations. Story 1.2 (epics.md:432) says "only repositories granted to this workspace". Decision Q8 (`plan.md:73`) governs which members see a granted repository; it does not say which installations attach to the workspace.
- Failure scenario: an admin who belongs to several GitHub organisations connects a workspace. Sync attaches all their installations. Every Admin or Member who can create projects can see and bind private repositories from organisations unrelated to this workspace, and later Agent Runs clone them.
- Not applied: the choice is product scope next to Q8. Options: (a) keep "attach all installations the connecting user can see"; (b) attach only installations the admin selects on the detail page (sync shows candidates, admin confirms each). Option (b) changes the I047/I050 flow slightly.

### F14. Connection outlives the admin who connected it (Medium, Security) - surface to user

- Location: Phase 1 data model `connected_by` (`architecture-contracts.md:48`).
- Evidence: no plan text covers removal or demotion of `connected_by`. Workspace member removal does not touch new agent tables.
- Failure scenario: the admin who connected GitHub leaves the company and is removed from the workspace. Plane keeps using their personal GitHub token for repository listing and, in Phase 7, PR creation under their GitHub identity.
- Not applied: options are (a) keep, show "connected by <name>" so admins can reconnect; (b) mark the connection `disconnected` when `connected_by` loses the admin role or leaves. Needs a product decision.

### F15. Minor Phase 1 test placement and log assertion scope (Medium, Scope audit)

- Location: Phase 1 Tests Before 3; 1.1 "token absent from `caplog`".
- Evidence: Tests Before are regression tests for existing behavior; endpoints in "Tests Before 3" do not exist yet. `apps/api/plane/middleware/logger.py:130-135` persists bodies only for `X-Api-Key` requests, so the real leak paths are the GitHub client logger, exception logging, and Celery task arguments.
- Action: fixed-in-plan. Tests Before 3 moved into Tests After. The 1.1 log test now targets the GitHub client and service loggers and asserts Celery tasks take IDs only, never tokens.

## Rejected or not raised

| Item | Reason |
| --- | --- |
| Scope & Complexity: additions beyond the 43 stories | None found. Every Phase 1 file maps to a story or a verified integration point. Seven phases and four migrations follow from the 43-story HOLD scope. |
| Reverse Q8 (members see all workspace-granted repositories) | User decision. F13 is about which installations attach, which Q8 does not cover. |
| Trigram index now | Plan already measures first (`phase-01:27`); no evidence of need. |
| Catalog snapshot swap fields | Plan states the rule ("swap after the last page; resume from saved page"); the field shape is an implementation detail. Not raised. |
| AD-8, Q1, Q2, Q7 exceptions in Phases 6-7 | User decisions; no new evidence. |

## Unresolved questions (for the user)

1. F13: attach all installations the connecting admin can see, or only those the admin selects for this workspace?
2. F14: when the admin who connected GitHub leaves or is demoted, keep the connection or mark it disconnected?

## Scope change detected during the review (not reviewed)

`gitlab-scope-decisions.md` appeared in the plan folder at 23:09 during this review (untracked). It adds self-hosted GitLab to Phase 1 with a provider-neutral data model. None of the phase files reflect it yet, so this review covers the GitHub-only plan. Consequences:

- F1, F2, F5, F7, F9, F11, F12, F15 apply to the neutral model unchanged. F3, F4, F6, F8 are GitHub-specific and stay valid for the GitHub provider.
- New attack surface that the next red-team pass must cover once the phase files include GitLab: a workspace-admin-supplied GitLab base URL is a server-side request target from the Plane API and the Worker. It needs the existing SSRF guard (`apps/api/plane/utils/url_security.py:198` `pinned_fetch`, as used by `bgtasks/webhook_task.py`), not plain `requests`, which contradicts `architecture-contracts.md:38` ("GitHub host is fixed; ... uses `requests`"). The optional custom CA bundle must not disable verification for other hosts. A Group Access Token is a bearer secret with group-wide scope; F5 (empty encrypt/decrypt) and F14 (who owns the credential) apply to it.
- Recommendation: update phase-01 and architecture-contracts for GitLab, then rerun the red-team gate on Phase 1 before implementation.

## Follow-up edits after self-review

- Concurrency tests (F1, F3, F9) need `@pytest.mark.django_db(transaction=True)` and real threads; the default per-test transaction hides row locks and `IntegrityError` races. Added to architecture-contracts §2 test-markers row.
- Phase 3 2.7 uses `github_disconnected` for a disconnected connection and `repository_unavailable` for a removed grant, so Phase 4 2.11 (awaiting repository question) does not contradict it.

## Evidence status

- Proven by reading: every Phase 1 path and parent, migration number, script names, vitest include globs, blocks export build, settings access key helper, test container `working_dir` and `exec "$@"`.
- Proven by GitHub docs fetch: single-use refresh tokens; grant vs token revoke scope; uninstall needs JWT; token-delete documents only 204/422.
- Not proven: no pytest, docker, pnpm or typecheck run (plan review only). Local `uv run python manage.py ...` could not start because host uv is 0.10.9 and `apps/api/pyproject.toml` requires 0.12.21 (environment, not plan).

## Addendum (2026-11-12, after the review)

- F13 and F14 were decided by the user on 2026-11-12: plan.md User decisions Q9 (admin selects attached installations; sync never attaches) and Q10 (connecting admin leaves or is demoted: GitHub connection becomes `reconnect_required`). Both are applied with tests in phase-01. GitLab: Q10 does not apply to a Group Access Token.
- The GitLab scope is now in the phase files (provider-neutral model in Phase 1, provider boundary in architecture-contracts §11). The `phase-01:NN` line citations above refer to the file before that change. This red-team gate has not run on the GitLab additions yet.

## Addendum: GitLab red-team pass (2026-11-12)

- Date: 2026-11-12 (Asia/Saigon). Scope: `git diff d6f6b43d25 acd8965582 -- plans/261112-2240-local-cli-agents-rebuild` (Phase 1 G1-G5 and the neutral model, Phase 3 Worker git transport, Phase 7 G6-G7 and Worker token handling, architecture-contracts §11, gitlab-scope-decisions.md).
- Lenses: Assumptions, Failure, Scope, Security. One reviewer, applied in sequence. Findings F1-F15 above are not repeated.
- Rules kept: no user decision changed (Q1-Q10, GitLab scope items 1-6). Open questions 1-4 not decided; evidence added to 4. One new trade-off surfaced as open question 5.
- Edits carry `<!-- red-team 2026-11-12 gitlab -->`. Line numbers below are for the files before this pass unless stated.
- Sources read: worktree code (`apps/api/plane/...`); GitLab source at `gitlab.com/gitlab-org/gitlab` master (`lib/api/api.rb`, `lib/api/metadata.rb`, `lib/api/personal_access_tokens/self_information.rb`, `lib/gitlab/auth.rb`, `lib/api/protected_branches.rb`, `doc/security/tokens/access_token_scopes.md`); git docs at `github.com/git/git` master (`Documentation/config/http.adoc`, `Documentation/gitcredentials.adoc`). Fetched 2026-11-12.

### GL1. `/version` refuses tokens without `api`/`read_api`, so G1 AC2 cannot happen as planned (High, Assumptions)

- Location: phase-01:63 (check order), G1 AC2, G1 tests (phase-01:215).
- Evidence: the API base allows only `api` and `read_api` (`lib/api/api.rb:57-58`); `/version` adds only `read_user`, `ai_features`, `ai_workflows` (`lib/api/metadata.rb:8`). `/personal_access_tokens/self` allows every scope (`self_information.rb:13-16`). The plan calls `/version` first and maps only 401, 404 and non-JSON.
- Failure: an admin pastes a `write_repository`-only token. `/version` returns 403 `insufficient_scope`, which has no mapping, so the user sees a generic error or a 500, not `gitlab_scope_missing`. The contract test still passes, because its "missing scope" fixture is hand-written for the `self` response, which the real flow never reaches.
- Action: fixed-in-plan. Order is now `self` first (401 = invalid, scope and expiry checks), then `/version`; a 404 on `self` falls back to `/version` to tell "too old" from "not GitLab"; unknown statuses map to `gitlab_unexpected_response`. Fixtures add a recorded `/version` 403 and a pre-15.5 `self` 404. Decision item 4 (minimum version check) is kept.

### GL2. A Worker token in `X-Api-Key` stores the GitLab token in Celery and `APIActivityLog` (High, Security)

- Location: phase-02:34 (Worker token, no header named); phase-03 and phase-07 `git-credential` endpoint; architecture-contracts §4.
- Evidence: `APITokenLogMiddleware` is active for every request (`plane/settings/common.py:134`). For any request that has `X-Api-Key`, it sends the request body and the response body to `process_logs.delay` (`plane/middleware/logger.py:130-153`). The `git-credential` response body is the GitLab token (architecture-contracts:221).
- Failure: the implementer copies the existing external-API pattern and sends the Worker token as `X-Api-Key`. Each clone and push writes the raw group token to the broker and to the `APIActivityLog` table. The plan's "no token in a log line" tests check `caplog` only and miss this.
- Action: fixed-in-plan. Phase 2 and §4 fix the header to `Authorization: Bearer` and add a test that a Worker request causes no `process_logs.delay` call.

### GL3. The Code container can redirect the Worktree's git metadata and run commands on the Host (High, Security)

- Location: phase-07:49 (Worktree is the writable bind mount), phase-07:51,53 (Worker runs commit and push on the Host with the token), architecture-contracts §11.
- Evidence: a git Worktree root contains a `.git` file with a `gitdir:` pointer; the container may write anywhere in the Worktree (phase-07:49). The plan has no rule about how the Worker finds the git directory (search for `gitdir`, `hooksPath`, `fsmonitor` in the plan: no result).
- Failure: an agent command in the container rewrites the `.git` file to a directory in the Worktree with a `config` that sets `credential.helper=!curl ...` or `core.fsmonitor=<cmd>`. The member then approves "commit" or "push". The Worker runs git on the Mini, git loads that config, and the attacker command runs on the Host with the GitLab token on the helper pipe or with the Mini-held GitHub credentials. This defeats "the container has no credentials" and the AD-8 boundary.
- Action: fixed-in-plan. Worker git on a Worktree uses explicit `--git-dir`/`--work-tree` from Run state, `core.hooksPath=/dev/null`, `core.fsmonitor=false`; the `.git` file is compared with the written value before commit and push (`worktree_tampered`); the clone and the worktree metadata are never mounted. Test added to G6.

### GL4. Worker git transport leaks the token to the system helper and has no SSRF guard (High, Security)

- Location: architecture-contracts:221-223 (credential helper on a pipe), phase-03:28,44.
- Evidence: an empty `credential.helper` value is needed to reset helpers from lower-priority config (`gitcredentials.adoc:199-201`); the plan adds a helper but does not reset the list. `http.followRedirects` defaults to `initial`, and git then uses the redirected URL as the base for later requests (`http.adoc:370-378`). The Plane API guard (`pinned_fetch`, operator allowlist) runs only in the API; the Worker clones with plain git. `AgentWorker` has no workspace field (architecture-contracts:56), so one Worker serves every workspace.
- Failure A: on the Mini, a system or global helper (for example `osxkeychain`) receives `store` after a successful clone and writes the GitLab token into the keychain. Linux CI has no such helper, so all Worker tests pass. Failure B: a workspace admin connects a public GitLab-like server whose clone URL passes the host check but answers with a redirect to `http://127.0.0.1:<port>` or a LAN host; the Mini follows it. Failure C: the same server changes DNS between the API check and the Worker clone (the Worker resolves again). `[UNVERIFIED]` whether git asks helpers for the redirect host; the fixes apply either way.
- Action: fixed-in-plan. Phase 3 and §11: `-c credential.helper=` before the pipe helper; the helper answers only for `https` and the clone-spec host; `http.followRedirects=false`; the Worker applies the blocked-address rule with a Worker-config allowlist and pins with `http.curloptResolve` (`http.adoc:141-147`); `GIT_TERMINAL_PROMPT=0`. Tests: recording helper injected through `GIT_CONFIG_SYSTEM`, redirect to a second server, loopback clone host.

### GL5. GitLab reconnect with another group leaves the old group attached (Medium, Failure)

- Location: phase-01:67 (different base URL needs Disconnect), phase-01:70 (one token = one group), G4 AC3 (covers base URL change only).
- Evidence: availability = account `attached` + connection `connected` + same host (phase-01:41). Nothing detaches the old group account when the same connection reconnects.
- Failure: admin disconnects, reconnects the same base URL with a token for group B. Group A's account is still `attached`, so group A bindings show as available. Their Runs fail at clone with `git_not_found`, or, if the new token can also read group A, run through a token the admin meant for group B.
- Action: fixed-in-plan. Connect sets all other accounts of the connection to `detached` in the same transaction; G1 test added.

### GL6. Hostile GitLab server limits are missing in `http.py` (Medium, Failure/Security)

- Location: phase-01:38, 63, 68.
- Evidence: `pinned_fetch` reads the full body unless the caller streams (`url_security.py:127-157`); `_fetch_validated_hop` retries every resolved address with the full timeout (`url_security.py:183-192`); the webhook serializer blocks the Plane request host and `WEBHOOK_DISALLOWED_DOMAINS` (`plane/app/serializers/webhook.py:49-55`), and the plan does not reuse that rule. Any user who can create a workspace is its admin.
- Failure: a server with 8 A records that never answers keeps a gunicorn worker for 8 x 6 checks x timeout; a server that returns a multi-GB `/version` body exhausts API memory; a base URL on Plane's own public host makes the API call itself with the pasted token.
- Action: fixed-in-plan. 1 MiB body cap with `stream=True`, 5 s connect and 10 s read per call, 30 s total budget, request-host and disallowed-domain rule, redirect message shows scheme and host only. G1 tests added.

### GL7. Phase 3 verification never runs the fetch-credential contract tests (Medium, Failure)

- Location: phase-03:89 (`-k "agent_run or agent_worker or agent_conclusion or entity_search"`), phase-03:48 (`test_agent_git_credential_fetch.py`).
- Evidence: no `-k` term matches `agent_git_credential`. Same class as F10, new instance introduced by the GitLab additions.
- Failure: lease, old-generation and `credential_mode=host` refusals of the token endpoint are never run in the Phase 3 PR check; the command is green.
- Action: fixed-in-plan. `agent_git_credential` added to the `-k` expression.

### GL8. Live GitLab smoke checks pass as skips (Medium, Failure)

- Location: phase-01:141 (`skipif` on `PLANE_TEST_GITLAB_TOKEN`), phase-01:232, phase-01:243 (success criterion), phase-07:121.
- Evidence: `docker compose run -e VAR` forwards nothing when `VAR` is unset; the test then skips and pytest exits 0. `pytest.ini` has no `-rs`. The Phase 7 command runs pytest on the host, unlike every other API command (`docker-compose-test.yml` `api-tests`).
- Failure: the operator runs the documented command without the secret loaded, sees exit 0, and records "smoke check passes" against git.oceanlabs.dev with zero tests run.
- Action: fixed-in-plan. `PLANE_TEST_GITLAB_REQUIRED=1` turns the skip into a failure, `-rs` prints skips, the Phase 7 command uses the test container, and the success criterion says a skip does not count.

### GL9. `ps` capture of git argv is a phantom test (Medium, Scope/Failure)

- Location: phase-07:102 ("`ps` capture of the git process"); same claim in phase-03 2.7.
- Evidence: phase-07:102 and phase-03:82 name a `ps` sample as the argv check; no step holds the git process open or records its argv and environment in a deterministic way.
- Failure: a fetch on a local remote ends in milliseconds; a `ps` sample usually sees no git process and the assertion "token not in argv" passes without data.
- Action: fixed-in-plan. A git shim first on the test `PATH` records argv and environment, then runs real git.

### GL10. Separate DNS-failure and blocked-address codes are an internal-name oracle (Medium, Security) - surface to user

- Location: G1 AC4 (`gitlab_dns_failed`), AC5 (`gitlab_url_blocked`).
- Evidence: the webhook path gives one message for both cases, "Invalid or disallowed webhook URL." (`plane/app/serializers/webhook.py:37`); `resolve_and_validate` raises different messages for the two cases (`plane/utils/ip_address.py:136-155`).
- Failure: any workspace admin learns whether `db.internal` or `vault.corp` exists in the instance's DNS by comparing the two codes.
- Action: surface-to-user. GitLab scope item 4 asks for a clear connection-failed reason, so merging the codes changes a user-accepted outcome. Options are in plan.md open question 5; the plan keeps two codes until the user decides.

### GL11. Minor: unused provider method, 401/403 rule, protected-branch pages (Low, Scope/Assumptions)

- `get_repository(external_id)` (architecture-contracts:204) has no caller in any phase step or story. Removed; the interface has five methods. The rest of §11 is justified: each remaining method has a Phase 1 or Phase 7 caller and two real providers.
- phase-01:74 says any 401 sets `reconnect_required`; phase-01:259 says 401/403. A 403 on one merge request (bot role lower on one project) would then stop all GitLab work. Fixed: only 401 changes status; 403 fails that operation.
- `GET /projects/:id/protected_branches` is paginated (`lib/api/protected_branches.rb:31,46`). Reading only page 1 misses rules after the first 20; the server-side refusal (`git_push_rejected`) is the backstop, but the user would approve a push that cannot succeed. Fixed: read all pages; test with 25 rules.
- Action: fixed-in-plan.

### GL12. Custom CA bundle widens trust for other hosts (Low, Security) - rejected

- Checked: `_request_to_ip` mounts a new `PinnedIPAdapter` on a throwaway `requests.Session` for each request (`url_security.py:121-124`), so a per-call `verify=<path>` cannot reach another host's request. On the Worker, `http.<url>.sslCAInfo` applies only to URLs that match the key (`http.adoc:380-382`). The admin's bundle can only affect that admin's own connection. Rejected: no failure path. The plan's planned unit test (second host keeps system trust) stays.

### Open-question evidence (no decision)

- Q4 (`api` vs `write_repository` for push): GitLab Git-over-HTTP token auth (`lib/gitlab/auth.rb:126`, `:308-329`) uses `abilities_for_scopes`, which maps `api` to `full_authentication_abilities` (`:350-352`) that include `push_code` (`:475-486`). So `api` alone likely permits push; the docs table (`access_token_scopes.md:41,44`) is silent. Recorded in plan.md and phase-01.
- `[UNVERIFIED]` group token on `/personal_access_tokens/self`: the endpoint refuses only tokens whose `token_type` is not `PersonalAccessToken` (`self_information.rb:19-23`); a group token is a `PersonalAccessToken` of the bot user. Supports the plan's expectation; the live check still decides. Mark kept.

### Evidence status (this pass)

- Proven by reading: `url_security.py` (verify hard-coded at `:133`, throwaway session, per-IP retry), `logger.py` middleware, `settings/common.py` middleware and allowlist parse, `webhook.py` message and request-host guard, `ip_address.py` messages, `pytest.ini` markers, existence of `plane/tests/smoke/` and `bg_tasks/test_url_security.py`.
- Proven by GitLab and git source or docs: GL1, GL4 (git config behaviour), GL11 pagination, Q4 evidence.
- Not proven: git credential fill on the redirect target (GL4, marked); `osxkeychain` present in the Mini's system config (fix applies regardless). No test, docker or typecheck run (plan review only).

### Unresolved (this pass)

- Open question 5 (GL10) needs the user.
- Not edited, Low: phase-01 writes the API-side CA bundle to a file named by its SHA-256 with no atomic-write rule. Two API workers that write the same name at once can give a partial file to a reader. Write to a temporary file, then rename. Apply at implementation time.
