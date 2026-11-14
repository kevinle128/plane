# Phase 2 implementation report

Branch `feat/local-cli-agents-phase-2` (worktree `plane-worktrees/local-cli-agents-phase-2`), based on `feat/local-cli-agents` (Phase 1, PR kevinle128/plane#3). One commit per story, pushed after each commit. Date 2026-11-13 (Asia/Saigon).

## Baseline (before any change)

- `pytest plane/tests/contract/app/test_api_token.py plane/tests/contract/app/test_agent_git_policy.py` -> 36 passed (Tests Before 2: `APIToken` auth and throttle unchanged).
- Tests Before 1 (settings index types and constants): `turbo check:types` web, blocks, types, constants -> 13/13 after the change.

## Per-story evidence

### 2.1 Connect Claude Code as a local Harness — `bb7499ac78`

- Test first: API tests -> conftest `ImportError: cannot import name 'AgentWorker'`; Worker tests -> 6 collection errors (`No module named plane_agent_worker.config` ...); blocks `connection-state.test.ts` -> `Cannot find module './connection-state'`.
- First green runs found two real defects: the request logger reads `request.user.id` (Worker principal now has `id = None`), and a user principal from another authentication path reached the Worker views (added `IsAgentWorker` permission; test `test_user_principal_is_refused_even_when_authenticated`).
- Green: API (settings, probe, worker auth, api_token) 77 passed; `makemigrations` -> `0130_agent_settings`, then `--check` clean; ruff clean. Worker 61 unit passed (macOS, and Linux in `python:3.12-slim` with uv 0.12.21); native 10 passed. Blocks 430 passed; typecheck 13/13; `pnpm check:lint` and `check:format` exit 0; i18n in sync.
- Fix removal proofs: without the read-time deadline and the report deadline check, `test_report_after_the_answer_deadline_returns_409` and `test_connecting_without_a_report_reads_failed_after_120_seconds` fail (the 119 s boundary test passes either way). Without the `IntegrityError` re-read, the threaded first-read race fails 3/3.
- Live evidence: a recorded native probe (`python -m plane_agent_worker probe --record`) passed all seven checks in 25 s; the transcripts in `apps/agent-worker/tests/transcripts/claude/` come from that run (scrubbed: no account data, signatures, usage, or home or Run root paths). End to end: the API ran in the test stack on `127.0.0.1:8765`, a token came from `create_agent_worker`, the real Worker loop claimed the probe, ran Claude Code 2.1.289 under the sandbox and reported; Plane stored `connected`, all 7 checks, 5 models, capabilities `midturn_input=false, native_resume=true, permission_prompt=true`, in 24 s. `APIActivityLog` count stayed 0. No probe process or probe directory was left.

### 2.2 Rename a workspace Agent — `205b02ff15`

- Test first: 9 failures with HTTP 405 (no PATCH).
- Green: settings 17 passed; with probe, worker auth and api_token 86 passed. The bot user takes the new name; the Agent and bot user IDs stay. Run identity (AC 3) is pending Phase 3.

### 2.3 Set a unique Agent mention handle — `7bfbf4e250`

- Test first: handle changes were ignored (200 instead of 400, old handle kept).
- Green: settings 30 passed, 3 runs. Threaded race (two Agents take one handle, `django_db(transaction=True)`) gives one 200 and one 400 `taken`; without the `IntegrityError` -> `HandleTaken` handling it fails 3/3. Total 99 passed. Run-level AC 3 is pending Phase 3.

### 2.4 Set an Agent's workspace instructions — `bdfb542e92`

- Test first: 4 failures (field ignored).
- Green: 104 passed. Multiline Unicode is kept exactly as typed; empty is allowed; more than 10,000 characters or a NUL character (PostgreSQL text cannot hold it) returns 400. The snapshot copy to Runs (AC 2-3) is pending Phase 3.

### 2.5 Toggle whether an Agent is mentionable — `e9f96bffb6`

- Test first: 2 failures (value not persisted; "maybe" accepted).
- Green: 108 passed. Off makes `available_for_mentions` false and keeps the connection. The picker reason (AC 2-3) is pending Phase 3.

### 2.6 Select a model reported by a connected Harness — `e2ccf9ba40`

- Test first: 200 instead of 400 for unreported models and for unconnected states; selection not persisted.
- Green: settings 48; total 117 passed. A choice must be a reported model of a connected Harness (`not_reported`, `not_connected`); clearing is always allowed; a later report without the chosen model clears it; disconnect keeps the choice for a later reconnect with the same model. Using the model in new Runs is Phase 3.

## Final verification

| Command                                                                                                                                                                      | Result                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `docker compose -f docker-compose-test.yml run --rm --build api-tests pytest test_agent_settings.py test_agent_harness_probe.py test_agent_worker_auth.py test_api_token.py` | 117 passed                                                    |
| `... pytest plane/tests/contract/app plane/tests/unit -k "agent or api_token or project_app or url_security"`                                                                | 515 passed                                                    |
| `... python manage.py makemigrations --check --dry-run`                                                                                                                      | No changes detected                                           |
| `... ruff check .` (test image)                                                                                                                                              | All checks passed                                             |
| `cd apps/agent-worker && uv sync && uv run pytest -m "not native and not docker"` (uv 0.12.21 through `uvx`)                                                                 | 61 passed                                                     |
| `uv run ruff check . && uv run ruff format --check .`                                                                                                                        | clean, 21 files formatted                                     |
| `uv run pytest -m native` (this Mac: macOS 26.6.2 arm64, Claude Code 2.1.289)                                                                                                | 10 passed (9 sandbox boundary, 1 real Claude probe) in 25.5 s |
| `pnpm --filter=@plane/blocks test`                                                                                                                                           | 42 files, 430 passed                                          |
| `pnpm turbo run check:types --filter=web --filter=@plane/blocks --filter=@plane/types --filter=@plane/constants`                                                             | 13/13                                                         |
| `pnpm check:lint`, `pnpm check:format`                                                                                                                                       | exit 0                                                        |
| `pnpm --filter=@plane/i18n check:sync`                                                                                                                                       | all locales in sync                                           |
| Copyright header on every new `.py/.ts/.tsx` (manual; `addlicense` not installed)                                                                                            | present                                                       |

## Deviations and open decisions

1. **Open decision (needs a person): Claude Code session directory is writable.** Under a deny-all-writes profile `claude --resume` fails ("No conversation found"), so the required follow-up and recovery checks cannot pass. The profile `qa-readonly.sb` allows writes only to the private temporary directory and to Claude's session directory for this probe's working directory (`~/.claude/projects/<cwd name>`), and denies reads of every other session directory, other Runs, the token file and the Plane checkout. The driver deletes the session directory after the probe. Q1 grants a disposable runtime directory only to Codex, Grok and Omp, so this is an AD-7 exception for Claude that nobody decided. Alternative: `CLAUDE_CONFIG_DIR` set to a Run-private directory (Q1-shaped), but it changes the keychain lookup and depends on how the Mini signs in. Until confirmed, "Claude Connected on the Mini" should not be claimed.
2. Related observation: Claude tried to create `~/.claude/.oauth_refresh.lock` and the sandbox denied it. With an environment token this has no effect; with a keychain OAuth login a token refresh may fail. Check on the Mini.
3. The live probe and the end-to-end run used this session's Anthropic environment token (allowlisted), not a Mini keychain login; nested agent-session variables were stripped.
4. The `Agent` model has all columns in the 2.1 migration `0130_agent_settings` (Phase 1 precedent); 2.2-2.6 expose the fields without new migrations.
5. `AgentConnection` stores the model list in `reported_models` (a field named `models` shadows `django.db.models` in the class body); the API field is `models`. Added `probe_claimed_at`, `probe_worker` (claim fencing) and `checks`.
6. Codex, Grok and Omp: Connect returns 409 `harness_probe_unavailable` and the page shows "The connection check for this agent is not available yet." The Worker claim lists its Harnesses, so it never claims a probe it cannot run.
7. The Enabled switch of the design is the Mentionable switch; it was added in 2.5 when the field became writable, not in 2.1.
8. Field errors carry `codes` (first DRF error code per field) for translated messages; the handle collision keeps the exact text "An agent with this handle already exists in this workspace.".
9. The model choice is saved with the settings form (one Save, fieldset disabled while saving), not on selection.
10. Files outside the phase list: `integrations/header.tsx` (neutral `title` prop for the breadcrumb), `db/models/user.py` (`BotTypeEnum.AGENT`), `tests/conftest.py` and `tests/agent_settings_fixtures.py` (fixtures), Worker `tests/test_process_registry.py`, `tests/test_loop.py`, `tests/conftest.py`, `.gitignore`, `.github/workflows/pull-request-build-lint-agent-worker.yml` (decision Q6).
11. The Worker has no third-party runtime dependency (stdlib `urllib`), pins uv `0.12.21` like `apps/api`; host uv is 0.10.9, so local commands ran through `uvx --from uv==0.12.21 uv`.
12. The probe uses the reported `haiku` model when present, for speed and cost.
13. Locales: the `translate` skill is not installed; non-English `agent.json` files carry the English text for the new keys.
14. No revoke command was added; revocation sets `revoked_at` (tests cover the 401).

## Not done

- Manual browser check (scene 11, Light and Dark, 375/768/1280 px, keyboard): NOT RUN, no browser driver in this session. Script: Integrations shows Essentials and a Harnesses group with four cards and text tags; Claude detail shows the Agent selector with tags, back link, Mentionable switch, Connection row in all four states (Connect, spinner, Connected with Disconnect confirm, failed with missing action, detail box and Retry), Name, Handle (collision message inline), Instructions, Model ("Available after connecting" or selector). Members see values and the read-only note, no actions. Check for nested interactive elements.
- Run-level criteria of 2.2 AC 3, 2.3 AC 3, 2.4 AC 2-3, 2.5 AC 2-3 and 2.6 AC 2 (new Runs use the model) and 4: pending Phase 3, as the phase file states.

## Review fixes and decisions (2026-11-14)

### Fix commits per review finding

| Finding                                                 | Commit                     | Note                                                                                                                                                           |
| ------------------------------------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend F1 (probe budget ignores the answer deadline)   | `8bb908ac99`, `c5278d9548` | Claim only while at least 60 of 120 s are left; the claim returns the seconds left and the Worker budget follows them                                          |
| Backend F2 (any workspace admin uses the Mini's Claude) | none                       | Closed by Q17 as an accepted risk while the instance is reachable only through Tailscale; recorded in the Worker README (`de4a004c5f`)                         |
| Backend F3 (no failing-path tests for three checks)     | `c5278d9548`               | Fakes `no_interrupt`, `crash_not_resumable`, `writes_despite_denial`, `prompts_for_write`                                                                      |
| Backend F4 (throttle test proves nothing)               | `8bb908ac99`               | Exemption proven directly and with a strict throttle on every other view                                                                                       |
| Backend F5, F6, F7, F8                                  | `c5278d9548`               | Folder error gives a failed report; restart removes stale probe and session folders; short commands in recorded process groups; `~` paths, CLI text in the log |
| Backend F9 (Worker CI job on a stacked PR)              | open                       | Process item: the PR against `preview` runs the job (remaining item 11)                                                                                        |
| Frontend C1 (polling never starts)                      | `a4b0641daa`               | Poll interval from the store Agents                                                                                                                            |
| Frontend I1, M1, M2, M3                                 | `5d22cc9939`               | Draft baseline of server values; one busy state; field error clears on edit; no label target without a control                                                 |
| Frontend I2 (tests miss the broken behavior)            | `a4b0641daa`, `5d22cc9939` | Pure poll, draft, error and store helpers with unit tests                                                                                                      |
| Frontend M4 (dead code, coupling)                       | `a4b0641daa`               | Shared fetch and poll module; unused single-Agent fetch removed                                                                                                |
| Frontend M5 (English text in non-English locales)       | none                       | Phase 1 convention                                                                                                                                             |

### Q16 rewrite: deviations 1 and 2 are resolved

- Deviation 1 (writable Claude session folder) is gone. `c5278d9548` replaced the outer macOS profile with Claude Code's built-in sandbox: the `claude` process runs outside the sandbox and writes its own session history, so no session-folder exception exists. Only Bash and its children run in the sandbox (`apps/agent-worker/plane_agent_worker/drivers/claude_boundary.py`).
- Deviation 2 (`~/.claude/.oauth_refresh.lock` denied) is gone for the same reason: the token refresh happens in the unsandboxed `claude` process.
- The outer-profile files were removed in `a4b0641daa` (pushed history is not rewritten): `git show --stat --format= a4b0641daa` lists `plane_agent_worker/sandbox/qa-readonly.sb` (-31), `plane_agent_worker/sandbox_macos.py` (-73) and `tests/test_sandbox_macos.py` (-120). Phase 6 restores an outer profile for Omp.

### Q18: quick check on Connect, suite once per CLI version

Commits `40f7d32e51` (split, no behavior change), `895e2063d7` (cache, lock, `ensure_verified`), `864f076e5f` (report version 2).

- Split: `uv run pytest -m "not native and not docker"` -> `79 passed, 1 deselected` before and after the split, with no test changed.
- Test first for the cache: `tests/test_suite_cache.py` -> `1 error during collection` (no `SuiteCache`); `tests/test_claude_probe.py` -> `4 failed, 19 passed`. After the change: `96 passed, 1 deselected`.
- Pin: changing `autoAllowBashIfSandboxed` in `claude_boundary.py` makes `test_suite_fingerprint_is_pinned_to_the_suite_version` fail (`1 failed`); the file was restored.
- Report version 2, test first in the API: `15 failed, 41 passed` in `test_agent_harness_probe.py` before the serializer change; after it, settings + probe + Worker auth + API token -> `141 passed`. Version 1 is refused (`{"version": 1}` in the malformed-report cases).
- Live check: the cache was proven with the fake CLI only, because the live check could not run (below).

### Q19: no midturn input for Claude

Commit `4badce1d0f`. Test first: `test_interruption_sends_no_message_during_the_turn` and `test_midturn_input_is_not_reported_for_claude` -> `2 failed, 2 passed`. After the change: `98 passed, 1 deselected`. The recorded `session-a.jsonl` is older than this change; `tests/transcripts/claude/README.md` says how it differs. It was not recorded again, because the only Claude login on this Mac cannot run a turn (below).

### Q21: one model request with a static fallback (accepted by the user on 2026-11-14)

Commits `411db61c00` (Worker), `c8355601ed` (web and i18n), `e7042d02d1` (API: each model needs `source`, `reported` or `fallback`).

- Real CLI check before the change: one `initialize` request with stdin closed right after it -> `control_response success plane-init` with 5 models, exit 0 (Claude Code 2.1.289).
- Worker, test first: `5 failed` (one-shot, fallback at Connect, cached model report, suite without a real report, `source` on reported models). After the change: `102 passed, 1 deselected`.
- Blocks, test first: `getModelSourceNoteKey` test failed (no export); after the change `connection-state.test.ts` -> `6 passed`; whole package `46 files, 452 passed`.
- API, test first: with the serializer of the previous commit, `test_agent_harness_probe.py` -> `4 failed, 54 passed` (fallback models stored with their source; a model without `source` or with an unknown one refused). With the change: settings + probe + Worker auth + API token + `plane/tests/unit/db` -> `161 passed`.
- i18n: `agent_settings.model.not_reported` ("Not reported by {harness}") in all 22 locales; `pnpm --filter=@plane/i18n check:sync` -> "All locales are in sync with English."

### Q25: Grok removed

Commits `899597a27f` (web: type, constants, the Grok blurb in 22 locales) and `effc64ac56` (API).

- API, test first: the list of exactly three Harnesses, the 404 for `grok` and the migration tests failed before the change (`6 failed, 100 passed`, and a collection error for the missing migration). After it: settings + probe + `plane/tests/unit/db` -> `121 passed`; `makemigrations --check --dry-run` -> "No changes detected".
- Migration `0131_remove_grok_harness` first deletes the Grok Agents that earlier builds of this branch created (with their connections and bot users, soft-deleted rows included), then changes the choices. It is needed because such a hidden Agent would keep the "Grok" handle in its workspace. On a database that never ran this branch it does nothing.

### Live check on this Mac (remaining item 8): PASSED after Q28 (2026-11-14)

Every `claude` run used a clean environment (`env -i HOME USER LOGNAME PATH LANG TERM`); the Worker never received a token, and the token was not read. Claude reads its own settings (Q28), so it uses the login and gateway that the user set up in `~/.claude/settings.json`.

Before Q28 the check could not pass: the Worker ran Claude with `--setting-sources ""` and `--restricted`, which hid the user settings, so Claude fell back to the keychain claude.ai login, an account on hold ("Your account is on hold and can't use Claude Code"). Evidence (one "Reply with the single word READY." prompt per case): `claude -p` and `claude -p --setting-sources user` answered READY; `claude -p --setting-sources ""` and `claude -p --restricted` answered with the hold notice.

After Q28 and Q29 (commits `f08b6e3cde`, `04a40a3301`, `053ccecee4`), two local probes on one Run root (`python -m plane_agent_worker probe`, Claude Code 2.1.289):

| Probe     | Time   | Result                                                                                                                                               |
| --------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Connect 1 | 48.8 s | exit 0; all seven checks passed; suite `{"suite_version": 2, "cli_version": "2.1.289", "verified_at": "2026-11-14T11:44:31+00:00", "ran_now": true}` |
| Connect 2 | 2.9 s  | exit 0; all seven checks passed; same suite record with `"ran_now": false`                                                                           |

Both reports list 5 models with source `reported` (`default`, `opus`, `claude-fable-5-1[1m]`, `sonnet`, `haiku`), capabilities `midturn_input=false`, `native_resume=true`, `permission_prompt=true`, and an empty failure hint. The times include the `uv run` start and the start of the user's MCP servers. `uv run pytest -m native` -> `1 passed` in 41.4 s (`test_real_claude_probe_passes_and_a_second_probe_uses_the_cached_suite`, second Connect under 10 s). The transcripts were recorded again from the first probe (`053ccecee4`); a scan of the recording found no home path, user name, email, key-like text, MCP tool names or temporary paths.

Not done: an end-to-end run through a real Plane API and the Worker poll loop with this setup; the probe ran locally. The last end-to-end run through the API was in Phase 2's first increment.

### Q28 and Q29: Claude runs as installed

Sources: code.claude.com docs (settings, permissions, sandboxing, env-vars, cli-reference), read directly because Context7 is not callable from this session.

- Removed flags: `--setting-sources ""`, `--restricted`, `--strict-mcp-config` and `--safe-mode`. The last one is needed for Q29: it turns off hooks, MCP servers, plugins, skills and CLAUDE.md. `disableAllHooks` is no longer set.
- The `--settings` file ranks above user, project and local settings; lists merge across scopes; deny rules are evaluated before allow rules.
- File tools: without `--restricted`, a scoped `Edit(<cwd>/**)` deny leaves Write open outside the working directory, and a user allow rule would merge in. The Worker now uses bare-name denies (`Edit`, `Write`, `NotebookEdit`). Checked natively: the tools are removed although `--tools Bash,Write` asks for Write, and Bash keeps its temporary folder. The permission check now requires that the `init` message does not offer them.
- Bash prompts: Claude Code 2.1.289 asks before a Bash write to a path the sandbox denies, and before code it cannot analyze (a `python3 -c` write). Checked natively: the prompt still comes with user hooks turned off, and after an allow the command runs in the sandbox, which denies the write (`operation not permitted`, `PermissionError: [Errno 1] Operation not permitted`). The probe allows only that Bash call and requires the sandbox denial. No earlier native run of the built-in-sandbox permission check had passed: the earlier passing runs used the outer sandbox.
- User settings cannot widen these points (unit test `test_user_settings_cannot_widen_the_boundary`, plus a native run with a local-scope settings file holding `allow: Write, Edit, Bash(*)`, `sandbox.enabled: false` and `allowWrite: <cwd>`: Write stayed removed and the Bash write was denied).
- Residual risk the Worker cannot close: settings lists merge, and only managed settings can lock them. A user `sandbox.filesystem.allowRead` entry re-opens a narrower part of a denied read path, and user `sandbox.excludedCommands` run outside the sandbox. Recorded in the Worker README.
- Open decision for Phase 3 (needs the user): in `claude -p`, a repository's `.claude/settings.json` `env` block and `apiKeyHelper` are used without workspace trust, so a cloned repository could redirect `ANTHROPIC_BASE_URL` or run a command on the Mini. `--setting-sources user` would keep Q28's reason (auth from user settings) and leave out project and local files. Phase 2 implements Q28 literally, which is equivalent here because the probe folder is created empty by the Worker.

### Final review fixes (code-review-phase-02-final.md)

- I1, reduced by the user (token exposure is a minor accepted risk): `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` is set for every `claude` process, covered by `test_harness_scrubs_credentials_from_its_subprocesses` and by `suite_fingerprint()`. No canary checks were added.
- M2: the Worker README says the Mini needs no managed Claude policy and that the suite cache must be deleted after a policy or settings change that affects the sandbox or permissions.
- M3: `test_record_with_a_failed_check_is_not_used`.
- M4: the Worker stops at start when `HOME` is missing, relative or not a directory (`04a40a3301`, 4 cases in `test_config.py`).
- M1 and M5: not done (M1 awaits a user decision; M5 is optional).
- Test first: after the test changes, `9 failed, 100 passed`; after the change `109 passed`; with the prompt handling `110 passed`. The fingerprint pin has entries for suite versions 1 and 2.

### Finding: an account on hold reads as a permission problem

With a login whose account is on hold, `auth status` passes, the model list arrives, and each turn ends with `result` subtype `success` whose text is the hold notice. The probe then reports `permission: Write was not attempted, so the permission rule was not proven` as the first failure (follow-up, progress, interruption and recovery fail too). An admin would read that as a sandbox defect. The probe still does not report Connected, so this is a wrong reason, not a wrong verdict.

Proposal (not implemented; it needs a decision on the matching rule and it touches the check contract):

1. In the first turn of session A, before the permission turns, compare the result text with known account-block replies ("Your account is on hold", "Not logged in · Please run /login", "Invalid API key"). Use a prefix match on Claude Code's exact strings, kept in one constant with the CLI version they were seen on.
2. On a match, stop the suite: set every suite check to "not run: Claude Code refused to run a turn for this login", and set the failure hint to "Claude Code is signed in, but the account cannot run turns. Sign in on the Mini with a working account, then retry." Keep the CLI text in the Worker log only. The suite result is not cached, because it did not pass.
3. Plane needs no change: the missing action stays the first failed check. An optional follow-up is a separate missing action `account_unusable` with its own message, which needs a new code in `harness_probe.py` and the blocks `KNOWN_MISSING_ACTIONS`.
4. Tests first: a fake scenario `account_on_hold` that answers every turn with the hold text; the report must name the account in its failure hint and must not blame the permission rule.

### Final gates (2026-11-14, branch head `e7042d02d1`; Worker rows updated at `053ccecee4`)

| Command                                                                                                                         | Result                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `docker compose -f docker-compose-test.yml run --rm --build api-tests pytest` settings, probe, Worker auth, API token           | 146 passed                                                                                      |
| `... pytest plane/tests/contract/app plane/tests/unit -k "agent or api_token or project_app or url_security"`                   | 546 passed, 1166 deselected                                                                     |
| `... python manage.py makemigrations --check --dry-run`                                                                         | No changes detected                                                                             |
| `... ruff check .` (test image)                                                                                                 | All checks passed                                                                               |
| Worker on macOS: `uv run pytest -m "not native and not docker"`, `ruff check .`, `ruff format --check .` (uv 0.12.21 via `uvx`) | 110 passed; clean; 22 files formatted                                                           |
| Worker on Linux: `python:3.12-slim` with `procps`, uv 0.12.21, non-root user, same three commands                               | 110 passed; clean; 22 files formatted                                                           |
| Worker native on this Mac: `uv run pytest -m native` (clean environment)                                                        | 1 passed (41.4 s)                                                                               |
| `pnpm --filter=@plane/blocks test`                                                                                              | 46 files, 452 passed                                                                            |
| `pnpm turbo run check:types --filter=web --filter=@plane/blocks --filter=@plane/types --filter=@plane/constants`                | 13/13                                                                                           |
| `pnpm check:lint`, `pnpm check:format`                                                                                          | exit 0                                                                                          |
| `pnpm --filter=@plane/i18n check:sync`                                                                                          | All locales are in sync with English                                                            |
| COPYRIGHT header on new `.py/.ts/.tsx` (manual; migrations are skipped by the check)                                            | present on `tests/test_suite_cache.py` and `tests/unit/db/test_remove_grok_agents_migration.py` |

Note on the Linux run: `python:3.12-slim` has no `ps`, which `process_registry.py:40` uses to record process start times, so without `procps` 31 tests fail with `FileNotFoundError: 'ps'`. The code before these changes (`f9ecdea65c`) fails the same way (22 failed). `ubuntu-latest` (the Worker CI runner) and macOS have `ps`, so this is a gap of the slim image, not a code defect. The earlier Linux result in this report (61 passed) does not record how its image was set up.

### Browser check of scene 11 (remaining item 9): NOT RUN

No browser tool is available in this session. The script in "Not done" above still applies, plus the fallback label "Not reported by Claude Code" in the model selector.
