# Code review: Phase 2 backend and Worker

- Date: 2026-11-13 (Asia/Saigon)
- Scope: `git diff origin/feat/local-cli-agents...HEAD -- apps/api apps/agent-worker .github` (57 files, +5309/-1), branch `feat/local-cli-agents-phase-2` at `a3aa9da4c4`.
- Reviewer: code-reviewer (fresh context). No code edited; mutation runs on a copy in `/tmp`.
- Scope update (coordinator, 2026-11-13, decision Q16): the outer `sandbox-exec` profile around `claude` is replaced by Claude Code's built-in sandbox plus permission deny rules. Profile details are not reviewed in depth; items the rewrite must keep are listed in "Rewrite must preserve".

## Verification run by the reviewer

| Command                                                                                                                                           | Result                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Worker copy: `uv sync --locked`, `pytest -m "not native and not docker"` (uv 0.12.21)                                                             | 61 passed, 10 deselected                                                                        |
| Worker copy: `ruff check .`, `ruff format --check .`                                                                                              | clean                                                                                           |
| Sandbox profile, scratch dir: hard link of token / other session / checkout file into the writable tmp or session dir, then read                  | denied (`ln: Operation not permitted`), no bypass                                               |
| Worker mutation: interruption check always passes                                                                                                 | 61 passed (survives)                                                                            |
| Worker mutation: recovery check always passes                                                                                                     | 61 passed (survives)                                                                            |
| Worker mutation: permission check ignores "file was written after the denial"                                                                     | 61 passed (survives)                                                                            |
| Worker mutation: session directory not deleted after the probe                                                                                    | 61 passed (survives)                                                                            |
| Worker mutation: loop reports a constant generation                                                                                               | 1 failed (caught)                                                                               |
| API, Docker test stack (unmodified worktree mount): `test_agent_settings`, `test_agent_harness_probe`, `test_agent_worker_auth`, `test_api_token` | 117 passed                                                                                      |
| API mutation (copy from `git archive HEAD`, mounted at `/code2`): remove `throttle_classes = []`                                                  | 14/14 Worker-auth tests pass (survives)                                                         |
| API control mutation: remove `IsAgentWorker`                                                                                                      | 4 failed (copy is the code under test)                                                          |
| API mutation: remove the `IntegrityError` re-read in `_create_agent`                                                                              | race test fails (report claim confirmed)                                                        |
| DRF pin `djangorestframework 3.18.3` (`apps/api/uv.lock:484-485`)                                                                                 | `many=True` `max_length` is enforced; 51-model case tested at `test_agent_harness_probe.py:285` |

Hygiene: the compose project `cr-phase2` was taken down with `down -v`; scratch copies removed. `git status` after the runs shows only untracked review reports; no tracked file changed through the mount (ignored `__pycache__` may be new).

## Findings

(Appended as confirmed.)

### F1 Important: Worker probe budget ignores the server answer deadline

- Where: `apps/agent-worker/plane_agent_worker/loop.py:79-88`, `conformance.py:27,72-90`; server `apps/api/plane/agent/services/harness_probe.py:94-104,141-142`.
- Problem: Plane accepts a claim until 120 s after `probe_requested_at` and rejects any report after that. The Worker gets `requested_at` in the claim but ignores it and always gives the probe a fixed 100 s budget from claim time. The Worker runs probes one at a time, and it does not stop a probe that a Retry or Disconnect replaced.
- Failure scenario: Workspace A and workspace B press Connect at t=0. A's probe is slow (turn timeouts, 45 s each) and takes 90 s. The Worker claims B at t=90 (still valid), runs about 25-100 s, reports at t>=115-190, and Plane returns 409 `probe_expired`. B shows "Connection failed: Worker did not answer" while the Harness is healthy, and the Claude spend for B is lost. The same happens to every probe queued behind a replaced probe that keeps running.
- Fix: in `claim_probe`, claim only probes with enough time left (for example `probe_requested_at >= now - (120 - minimum_probe_seconds)`), return the absolute deadline in the claim, and have the Worker use `min(PROBE_BUDGET_SECONDS, deadline - now - report_margin)`; skip the probe when the remainder is too small. Add a test for a claim close to the deadline.

### F2 Important: any workspace Admin can make the shared Worker spend the operator's Claude account, without limit

- Where: `apps/api/plane/app/views/agent/settings.py:71-79` (Connect: Admin of any workspace, no throttle), `harness_probe.py:66-77,92-116` (one global queue, any Worker claims any workspace's probe), `plane/settings/common.py:152-158` (session users are not throttled by `AnonRateThrottle`).
- Problem: one Worker serves every workspace (architecture-contracts §11). Each Connect or Retry starts a new generation and is claimed again. There is no instance-level allowlist of workspaces that may use the Mini, no rate limit on Connect, and no per-workspace fairness. With Plane defaults (`ENABLE_SIGNUP=1`, `DISABLE_WORKSPACE_CREATION=0`) any person who signs up becomes Admin of a new workspace.
- Failure scenario: an outside user signs up, creates several workspaces and calls `POST .../agents/claude_code/connect/` in a loop for each. The Worker runs Claude probes continuously (about 8 model turns per probe) on the operator's subscription, and the legitimate workspace's Connect waits behind them and then expires (F1). The outside workspace can also become `connected`, which in Phase 3 lets it start Runs on the Mini.
- Fix: decide the tenancy rule before Phase 3. Minimal: an instance setting (God-mode or env, for example `AGENT_WORKER_ALLOWED_WORKSPACES`) that Connect and `claim_probe` both check, plus a throttle on Connect/Retry per workspace. If the deployment is single-tenant by policy, record that in the plan and lower this to Minor.
- Note: this needs a product decision on who may use the Mini; it is not a code-only fix.

### F3 Important: three of the seven AD-4 checks have no failing-path test in the Worker suite

- Where: `apps/agent-worker/plane_agent_worker/drivers/claude.py:461` (permission "written after the denial"), `:488-499` (interruption), `:540-550` (recovery), `:352` (session directory delete); tests `apps/agent-worker/tests/test_claude_probe.py` (fake scenarios: ok, no_permission_prompt, writable boundary, not_logged_in, no_models, no_resume, missing CLI, unsupported version).
- Evidence: on a copy, each of these mutations leaves all 61 unit tests green: interruption always passes; recovery always passes; permission ignores a file written after the denial; session directory not deleted.
- Failure scenario: a future Claude CLI version ignores `interrupt` (or the rewrite to the built-in sandbox changes the event order). The driver regresses to "interruption passed" and Plane shows Connected for a Harness that cannot be stopped. No unit test fails; only the Mini-only native test could catch it.
- Fix: add fake scenarios `no_interrupt`, `crash_not_resumable` and `writes_despite_denial`, and assert the session directory is gone after the probe. This matters more now because the Q16 rewrite changes these code paths.

### F4 Minor: the "120 calls are not throttled" test passes without the exemption it claims to prove

- Where: `apps/api/plane/tests/contract/app/test_agent_worker_auth.py:35-39`, `apps/api/plane/agent/worker_api/views.py:31`.
- Evidence: on a copy with `throttle_classes = []` removed, all 14 Worker-auth tests pass (control mutation that removes `IsAgentWorker` fails 4 tests, so the copy was used). The default `AnonRateThrottle` (`plane/settings/common.py:153`) skips authenticated principals, so the Worker is never throttled either way.
- Failure scenario: none at runtime today. The test gives false assurance: if a later change adds a user/scope throttle to the Worker base class, this test still passes when the throttle has a high limit, and it never exercised the `ApiKeyRateThrottle` risk that the plan names.
- Fix: assert `WorkerAPIView.throttle_classes == []` and `get_throttles() == []` directly, or patch `DEFAULT_THROTTLE_CLASSES` to include a `UserRateThrottle` at 60/min and show 120 calls still return 200. Same note for `test_worker_request_is_not_sent_to_the_api_activity_log` (`:78-85`): the test client never sends `X-Api-Key`, so it passes regardless of the Worker code; keep it as a middleware guard but do not cite it as Worker evidence.

### F5 Minor: a filesystem error before the probe starts stops the Worker process

- Where: `apps/agent-worker/plane_agent_worker/conformance.py:82` (`prepare_workspace` runs outside the `try`), `loop.py:80-87,98-101` (no guard in `run_once`/`run_forever`).
- Failure scenario: the Run root volume is full, or `probes/<key>` has a file Worker cannot remove. `mkdir`/`rmtree` raises `OSError`, the exception leaves `run_forever`, and the Worker exits. The claimed probe reads "Worker did not answer" after 120 s and every later Connect fails until someone restarts the Worker.
- Fix: move `prepare_workspace` inside the `try` and report a failed probe with an internal-error hint; add a last-resort `except Exception` with logging in `run_forever` so one bad probe cannot stop polling.

### F6 Minor: a Worker crash leaves probe directories and Claude session folders behind

- Where: `apps/agent-worker/plane_agent_worker/process_registry.py:113-128` (reconcile stops process groups only), `conformance.py:89`, `drivers/claude.py:352`.
- Failure scenario: the Worker is killed during a probe. On restart `reconcile` stops the orphan `claude` processes, but `run_root/probes/<id>-<gen>/` and `~/.claude/projects/<encoded probe cwd>/` (session transcript) stay. Each crash adds one more; nothing removes them because the next probe has a new key.
- Fix: at start, remove `run_root/probes/*` (no probe survives a restart) and record the session directory in the process record so `reconcile` deletes it. Keep this in the Q16 rewrite, which still writes session data.

### F7 Minor: short CLI commands are not in a process group and are not recorded

- Where: `apps/agent-worker/plane_agent_worker/drivers/claude.py:295-305` (`--version`, `auth status` through `subprocess.run`), `sandbox_macos.py:63-65` (`verify_write_denied`).
- Failure scenario: `claude auth status` hangs and starts a helper child. `subprocess.run(timeout=...)` kills only the direct child; the helper keeps running, and `reconcile` does not know it.
- Fix: run these through `ProcessRegistry.spawn` (new session, record, `release` on timeout), like the stream sessions.

### F8 Minor: members of every workspace see Mini paths and raw CLI stderr

- Where: `apps/api/plane/app/serializers/agent.py:24-38` (`location`, `failure_hint`, `checks[].detail` to Admin and Member), Worker sources `drivers/claude.py:322,360,515`.
- Failure scenario: `location` is the absolute path of `claude` on the Mini (for example `/Users/<operator>/.local/bin/claude`), and `failure_hint` can carry up to 1000 characters of `claude --version` or resumed-session stderr. With one Worker for every workspace, a Member of any workspace reads the operator's home path and CLI error text.
- Fix: send `location` and stderr text only to Admins, or have the Worker replace the home directory with `~` and keep stderr out of the hint (show a fixed message, log stderr locally).

### F9 Minor: the Agent Worker CI job does not run on a stacked PR

- Where: `.github/workflows/pull-request-build-lint-agent-worker.yml:5-7` (`branches: ["preview"]`).
- Failure scenario: Phase 2 is stacked on `feat/local-cli-agents` (PR #3, base `preview`). If the Phase 2 PR targets `feat/local-cli-agents`, no Worker lint or test job runs until it is retargeted. The other workflows have the same filter, so this is a process note.
- Fix: open the Phase 2 PR against `preview` after Phase 1 merges, or run the workflow with `workflow_dispatch` on the branch before merge. The uv pin (`version-file` reads `required-version ==0.12.21`), `uv sync --locked`, ruff, format check and the unit marker filter are correct, and the job needs no secret.

## Checked and not a finding

- Token: `secrets.token_urlsafe(32)` (256 bits), SHA-256 stored, unique hash index; lookup by hash, so no byte compare of secrets happens in Python (timing-safe by construction). `revoked_at__isnull=True` and the soft-delete manager are honored (`authentication.py:60`). Bearer only; `X-Api-Key` returns 401; session users get 401/403 (`IsAgentWorker`). The token file is created `O_CREAT|O_EXCL|O_NOFOLLOW`, mode 0600, removed on failure, never printed (`create_agent_worker.py:43-65`).
- Worker writes do not take audit columns from the principal (`disable_auto_set_user=True` on `claim_probe` and `apply_report`; heartbeat uses `.update`).
- Probe fencing: generation, state, claimant and deadline all checked under `select_for_update` (`harness_probe.py:133-142`); Disconnect and Retry bump the generation under a row lock; `claim_probe` uses `skip_locked`. Report validation bounds every string and list, rejects non-boolean `passed`, duplicate checks/models, unknown capabilities and other report versions; model IDs cannot start with `-` (argv-safe).
- Connected needs all seven checks plus a non-empty model list and no blocking issue (`_missing_action`); a failed report stores no models.
- Lazy creation: verified by mutation that removing the `IntegrityError` re-read fails the threaded race test. GET endpoints run on the primary DB (`BaseAPIView.use_read_replica = False`), so the write-on-read is safe with read replicas.
- Handle: DB constraint on `Lower(handle), workspace` (partial, live rows) plus serializer `iexact` check; concurrent collision mapped to 400 `taken`.
- Save semantics server-side: `update_agent_settings` (`agent_settings.py:118-134`) locks the Agent row, applies only the sent fields to the fresh row and saves; the bot user name follows in the same transaction. There is no version or `updated_at` precondition, so two Admins saving at once give last-writer-wins per field. The spec asks only for the client fieldset lock, so this is not a finding.
- Permissions: GET Admin/Member, PATCH/Connect/Disconnect Admin only; guest 403 (tests present).
- Migration `0130_agent_settings` depends on `0129_agent_git_policy`; lockfile updated; reviewer's Docker run: 117 passed (`test_agent_settings`, `test_agent_harness_probe`, `test_agent_worker_auth`, `test_api_token`).
- Sandbox profile (pre-Q16): direct reads and hard links of the token file, another session file and a checkout file are denied.

## Rewrite must preserve (Q16: Claude built-in sandbox)

1. Environment allowlist (`drivers/claude.py:74-97`): no Worker token path, no `PLANE_AGENT_WORKER_*`, no outer agent-session variables; `TMPDIR` points to the probe-private tmp. Keep a unit test like `test_harness_gets_an_allowlisted_environment`.
2. The Worker token file and the Plane checkout must stay unreadable to the `claude` process and every tool it starts. Claude's `denyRead` covers its Read tool and sandboxed Bash; also confirm that `--tools` stays limited (no Bash) where the built-in sandbox does not cover a tool, and that `--restricted`, `--safe-mode`, `--strict-mcp-config` and `--disable-slash-commands` still apply (hooks and MCP off).
3. The "permission" check must still prove an OS-level denial, not only a denied prompt: AD-7 says the Harness's own approval is an additional control, not the only boundary. If the built-in sandbox covers Bash only, an Edit/Write denial is a permission rule, not an OS boundary; the check and its report detail must state which control was proven, and `verify_write_denied` must test the same boundary the Run uses.
4. Settings that grant the built-in sandbox and deny rules must come from a Worker-owned `--settings` file (managed by the Worker, outside the clone, not writable by the Harness), because `--restricted` ignores user/project/local settings files.
5. Probe semantics: Connected only with all seven checks; interruption requires both an interrupted result and a following turn; recovery requires a kill during a turn and a resumed recall; add the missing negative fakes (F3).
6. Cleanup: process groups through `ProcessRegistry` (F7), probe directory and session directory removal after the probe and on restart (F6).
7. Session folders: other Runs' session folders must stay unreadable (`denyRead`), and the folder Claude writes for this Run must be the only writable one outside the private tmp.

## Counts and verdict

- Critical 0, Important 3 (F1, F2, F3), Minor 6 (F4-F9).
- F1 blocks merge: a code fix (claim cutoff plus deadline-aware budget) and a test; otherwise a healthy Harness can read "Connection failed".
- F2 needs a user decision on who may use the Mini (open signup and workspace creation are Plane defaults). Do not merge Phase 3 Run start without that decision; Phase 2 can merge if the user records single-tenant use.
- F3 is a required deliverable of the Q16 sandbox rewrite (negative fakes for interruption, recovery, written-after-denial, session cleanup).
- Verdict: not ready to merge until F1 is fixed and F2 is decided; the rest of the backend (auth, fencing, validation, settings, migration, CI) is sound.
