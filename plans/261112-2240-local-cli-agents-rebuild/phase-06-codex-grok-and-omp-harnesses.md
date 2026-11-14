---
phase: 6
title: "Codex, Grok and Omp Harnesses"
status: todo
priority: P1
effort: "7d"
dependencies: [5]
---

# Phase 6: Codex, Grok and Omp Harnesses

> **2026-11-14, decision Q25:** Grok is dropped. Stories 2.23 and 2.24 and every Grok driver, fake, transcript, profile and test in this file are out of scope. Build only Codex (2.21, 2.22) and Omp (2.25, 2.26). Effort 7d.

> **2026-11-14, decisions Q31-Q35:** Codex and Omp run inside Docker Sandboxes like Claude ([plan.md](./plan.md#docker-sandboxes-decisions-2026-11-14), [architecture-contracts.md §12](./architecture-contracts.md#12-docker-sandboxes-for-runs)). Q1 (disposable runtime folder and outer macOS profile), Q20 (per-Run `CODEX_HOME` with a link to the host login) and Q23 (Codex `read-only` sandbox and its proofs) are superseded. `sandbox_macos.py` is not restored. The Codex login path inside the sandbox is open (plan.md Docker Sandboxes open question 3).

## Goal

Codex CLI, Grok CLI and Omp each pass the AD-4 connection check and run read-only Q&A Runs with follow-up, queue, Send now, Stop and resume through their own verified control paths. One PR, one commit per story 2.21-2.26.

<!-- 2026-11-14 --> Decisions that change this phase: Q18 (quick check on Connect, suite once per CLI version), Q20 (per-Run `CODEX_HOME`, superseded by Q31), Q21 (Codex model listing), Q23 (Codex Q&A in Codex's own read-only sandbox, superseded by Q31), Q24 (Plane MCP server for questions), Q31-Q35 (Docker Sandboxes). See [plan.md](./plan.md#multica-comparison-decisions-2026-11-14).

## Blocker

<!-- 2026-11-14 --> Superseded by Q31. The prior native checks (Codex 0.157.1 `Operation not permitted`, Grok 1.0.41 `FS_PERMISSION_DENIED`, Omp 18.1.21 `SQLITE_READONLY`, [runtime decision](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-harness-runtime-decision.md)) came from a read-only boundary around the whole CLI. Inside a sandbox the VM file system is writable, so runtime state works; only the clone mount is read-only. The remaining blocker is the Codex login inside the sandbox (plan.md Docker Sandboxes open question 3); without an answer Codex stays Connection failed with the login missing action.

## Context links

- Stories: [epics.md:1135-1273](../2026-09-28-plane-local-cli-agents-epics/epics.md). Contracts: [architecture-contracts.md](./architecture-contracts.md) §5, §7, §10. Spine AD-4 table, AR13 (epics.md:229).
- Protocol references (from Spine AD-4): Codex app-server README, Grok headless guide and CLI reference, Omp RPC doc. Re-read the current versions before coding; record CLI versions in the check report. Codex on the development Mac is 0.167.0 (2026-11-14), newer than the 0.157.1 of the prior evidence. <!-- 2026-11-14 --> From Q31 the version that counts is the one inside the sandbox kit.
- [Multica research](./reports/research-multica-agent-integration.md) §1.2 (Codex app-server invocation, per-task `CODEX_HOME`), §1.5 (model listing), §4 F4 and F7.

## Key decisions

- One driver module per Harness under `plane_agent_worker/drivers/`. Each implements the `drivers/base.py` contract from Phases 2-5: quick check, suite, models, start/resume, send, inject (optional), interrupt, settle, permission response, shutdown, event mapping.
- <!-- 2026-11-14 --> Connection check (Q18): Connect runs the quick check (CLI found, `--version`, login status, model list). The seven AD-4 checks run as the per-version suite through `ensure_verified` (Phase 2), keyed by (Harness, CLI version, suite version of that driver). Each driver has its own `SUITE_VERSION` and hash pin test. Run turns call `ensure_verified` as in Phase 3. Spec effect: stories 2.21, 2.23 and 2.25 connect fast when the version has a passing record; their criteria are otherwise unchanged.
- Codex: app-server JSON-RPC over stdio (`codex app-server`); login status from `codex login status`; steering candidate `turn/steer`; approvals mapped to deny in Q&A.
  - <!-- 2026-11-14 --> Models (Q21): `model/list`; if it fails, `codex debug models`. Both are reports from the CLI, so 2.21 has no fallback deviation. No static list.
  - <!-- 2026-11-14 --> Runtime directory (Q20 superseded by Q31): Codex keeps `~/.codex` inside the VM. At sandbox creation the Worker writes the VM's `~/.codex/config.toml` with full permissions inside the VM (`sandbox_mode = "danger-full-access"`, `approval_policy = "never"`; exact keys re-read from the kit's Codex version), the Q32 MCP servers and nothing from the host `~/.codex/config.toml`. The Plane MCP server and its per-turn handle are passed per process with `-c` overrides (`[UNVERIFIED]` key names for 0.167; task 0 below checks them). Threads live in the VM, so `thread/resume` works while the sandbox exists (Q35).
  - <!-- 2026-11-14 --> Login (Q31): the host `~/.codex/auth.json` cannot be linked into the VM. The login path is plan.md Docker Sandboxes open question 3: (a) Worker config key or gateway, as for Claude; (b) `sbx secret set openai`, so only the proxy holds the key; (c) a ChatGPT login inside each Codex sandbox. Task 0 tests the chosen path.
  - <!-- 2026-11-14 --> Q&A boundary (Q23 superseded by Q31): the sandbox mounts of §12. The clone is read-only at the mount, so a shell write and an `apply_patch` to the clone both fail at the mount, and secrets on the host are not in the VM. No per-version boundary proof.
- Grok: headless streaming JSON turns with session resume; `midturn_input=false`; Plane queue and cancel-then-next-turn; model list from `grok models`. Connected requires a proven permission pause and safe response path (2.23 AC 3); otherwise Connection failed.
- Omp: stdio RPC (`prompt`, `steer`, `follow_up`, `abort`, UI response, `get_available_models`); questions map to `AgentRunQuestion(kind=harness)` from Phase 4.
- <!-- 2026-11-14 --> Runtime state for Omp (Q1 superseded by Q31): Omp writes its runtime state (SQLite) inside the VM. Omp has no built-in `sbx` agent (`sbx create --help` lists claude, codex, copilot, cursor, devin, docker-agent, droid, kiro, opencode, shell), so the Worker uses the `shell` agent with a small local kit that installs a pinned Omp version (`sbx create --kit ./kits/omp`); exact kit format is checked in task 0.
- Plane tools (comments, questions) reach each Harness through MCP when the Harness supports MCP; otherwise the check fails and names it. Q24 keeps the question card, so a Harness without MCP cannot ask a structured question and is not Connected. Codex gets the Plane MCP server through `-c` overrides per process (Q31, see the runtime directory item). MCP support of Grok and Omp is `[UNVERIFIED]`; Omp UI-response maps to a question without MCP.

## Task 0: sandbox check for Codex and Omp (first task)

<!-- 2026-11-14 --> Effort 1d, after the user answers plan.md Docker Sandboxes open question 3. Same method and report rules as [Phase 3 task 0](./phase-03-claude-qa-run-and-timeline.md#task-0-sbx-verification-first-task); report `reports/sbx-codex-omp-verification.md`. Pass criteria per Harness: (1) the control protocol runs over pipes through `sbx exec -i` (Codex `app-server` JSON-RPC; Omp stdio RPC); (2) the chosen login path completes a real turn with no secret in host argv; (3) resume (`thread/resume`; Omp session recovery) works across two `exec` calls and after `sbx stop`; (4) interrupt (`turn/interrupt`, Omp `abort`) and the pidfile kill both end work; (5) the Plane MCP server over HTTP answers inside the sandbox (Codex `-c` override; Omp MCP support is `[UNVERIFIED]`, and the UI-response path is the fallback for questions); (6) a write to the read-only clone mount fails. If a criterion fails, that Harness stays Connection failed with the named missing action and the user decides.

## File ownership

This phase owns only: `apps/agent-worker/plane_agent_worker/drivers/{codex,omp}.py`, `drivers/__init__.py` (registry entries), `apps/agent-worker/kits/omp/` (Omp sandbox kit), the Codex and Omp kit entries in `plane_agent_worker/sandbox.py`, `tests/fakes/{fake_codex,fake_omp}.py`, `tests/transcripts/{codex,omp}/`, `tests/test_{codex,omp}_driver.py`. <!-- 2026-11-14 --> Removed by Q31: `drivers/codex_home.py`, `sandbox_macos.py`, `runtime_dir.py`, `sandbox/qa-readonly.sb`, `tests/test_sandbox_macos.py`; removed by Q25: every Grok file. It does not touch `plane_agent_worker/code/` (Phase 7). Backend and web need no new files: harness cards, probe API and Run UI already support all four harnesses; add the three harnesses to `PROBE_HARNESSES` (`apps/api/plane/agent/services/harness_probe.py:26`) and i18n strings for harness-specific hints.

## Tests Before

1. Claude driver suite from Phases 2-5 passes unchanged.
2. Base driver contract tests run against the fake Claude to prove the shared contract does not change.
3. <!-- 2026-11-14 --> The Phase 3 sandbox tests (`tests/test_sandbox.py`) pass unchanged before the Codex and Omp kit entries are added.

## Refactor

Protected by Tests Before 1-3: only `drivers/__init__.py` (registry), `sandbox.py` (kit entries) and `harness_probe.py` (`PROBE_HARNESSES`) change outside new files. The base driver contract does not change; if a Harness needs a contract change, stop and update Phases 2-5 tests first.

## Story steps and Tests After

| Story | Steps                                                                                                                                                                                             | Tests After                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2.21  | Codex quick check (transport, login status, `model/list` with `codex debug models` fallback) and suite (events, follow-up, steer, cancel, approval reading, recovery) inside the Codex sandbox | Fake Codex: full pass sets Connected with models; unauthenticated fake fails with recovery hint; `model/list` failure uses `codex debug models`; both failing fails the model check; cached version runs no suite; the VM `config.toml` written by the Worker has full permissions, only the Plane MCP server and listed servers, and no key from a host `config.toml`; the permission check asserts that no approval request arrives in the suite turn (Q31 reading of AD-4); fake `sbx` records the Codex sandbox create with `--skills=off` and the read-only clones mount; native (Mini): real check passes inside the sandbox with the chosen login path |
| 2.22  | Codex Q&A turns, queue, Send now via `turn/steer` if verified, Stop, resume, restart                                                                                                              | Fake Codex: ordered conversation, steer acknowledgement before `accepted`, restart keeps Run ID, clone and cursor; `thread/resume` failure (also after a recreated sandbox, Q35) starts a new thread from the transcript; Stop uses the pidfile kill; native turn, and a write to the clone fails at the mount                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2.23  | (Removed by Q25) Grok quick check and suite with permission pause/resume proof                                                                                                                                     | Fake Grok: missing permission pause keeps Connection failed with named action; full pass sets Connected with live model list                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2.24  | (Removed by Q25) Grok Q&A, resumed follow-up, Send now as cancel-then-next-turn, effect outside boundary blocked                                                                                                   | Fake Grok: resume or rebuild; Send now cancels and settles first; write attempt blocked and recorded as event; native: outer profile denies writes outside the runtime directory                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2.25  | Omp quick check (`get_available_models`) and suite (prompt, steer, follow-up, abort, UI response, events, session recovery) inside the Omp sandbox kit                                            | Fake Omp: full pass; missing control fails with named action; fake `sbx` records the `shell` agent with the Omp kit; native: real check passes inside the sandbox                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2.26  | Omp Q&A, queue, Send now, question answer, Stop, restart                                                                                                                                          | Fake Omp: UI-response maps to question and answer; order kept; restart keeps Run ID and cursor; unrecoverable turn becomes error                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

## Verification

```bash
cd apps/agent-worker && uv run pytest -m "not native and not docker" && uv run ruff check . && uv run ruff format --check .
cd apps/agent-worker && uv run pytest -m native tests/test_codex_driver.py tests/test_omp_driver.py   # Mini only, signed in to sbx, Codex login path set up
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app -k "agent_harness_probe or agent_run"
pnpm --filter=@plane/i18n check:sync
```

Live check on the Mini: Connect each Harness in Integrations (first Connect runs the suite, second uses the cache), mention it, follow up, Send now, Stop and resume. Record results and CLI versions per Harness in `reports/`.

## Success criteria

- [ ] All Given/When/Then cases of 2.21-2.26 pass with real CLIs on the Mini, or the Harness stays Connection failed with the named missing action and the user accepts that outcome.
- [ ] Q&A boundary holds for each connected Harness (AR13): <!-- 2026-11-14 --> a native test shows that a write to the clone fails at the read-only mount and that the Worker token path does not exist in the VM (Q31; replaces the Q23 proofs).
- [ ] Task 0 report exists for Codex and Omp.
- [ ] Mockup rows I063, I064 (Codex states) and I075 pass browser review.

## Risks

| Risk                                                                                                                                             | L x I           | Mitigation                                                                                                                                                                                                                                         |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| (Removed by Q25) Grok headless JSON route | - | - |
| <!-- 2026-11-14 --> Codex login inside the sandbox is lost when the sandbox is removed (option c of Docker Sandboxes open question 3) | Medium x Medium | Prefer option (a) or (b); with (c), Connect names the login missing action after a recreate |
| <!-- 2026-11-14 --> Omp kit breaks on an Omp or kit format update | Medium x Medium | Pinned Omp version in the kit; a new version runs the suite (Q18); task 0 records the kit format |
| <!-- 2026-11-14 --> Codex `-c` overrides for the Plane MCP server change between versions | Low x Medium | Task 0 checks the keys; the suite fails with the MCP check named on a new version |
| <!-- 2026-11-14 --> (Removed by Q31) runtime directory rows | - | - |
| CLI protocol change between versions                                                                                                             | High x Medium   | Version recorded in report; a new version runs the suite (Q18); driver refuses unknown major versions; transcripts re-recorded                                                                                                                     |
| (Removed by Q25) Grok cannot pause for permission | - | - |

## Rollback

Before the revert, select Disconnect for Codex and Omp in Integrations so no new mention targets a driver that will disappear. Then revert the PR. The Worker claim query filters by registered drivers, so it does not claim their pending Runs; those Runs stay readable and a member can mark them failed after they become Stale. <!-- 2026-11-14 --> Remove the Codex and Omp sandboxes (`sbx rm --force` for `plane-*` names of those kits); Claude sandboxes stay.
