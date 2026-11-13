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
