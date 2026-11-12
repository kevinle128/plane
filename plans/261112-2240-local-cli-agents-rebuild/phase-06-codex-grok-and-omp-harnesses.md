---
phase: 6
title: "Codex, Grok and Omp Harnesses"
status: todo
priority: P1
effort: "10d"
dependencies: [5]
---

# Phase 6: Codex, Grok and Omp Harnesses

## Goal

Codex CLI, Grok CLI and Omp each pass the AD-4 connection probe and run read-only Q&A Runs with follow-up, queue, Send now, Stop and resume through their own verified control paths. One PR, one commit per story 2.21-2.26.

## Blocker

Decision Q1 (AD-7 disposable-runtime exception) must be made before this phase starts. Prior native checks show all three CLIs fail to start under a full read-only boundary ([runtime decision](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-harness-runtime-decision.md): Codex 0.157.1 `Operation not permitted`, Grok 1.0.41 `FS_PERMISSION_DENIED`, Omp 18.1.21 `SQLITE_READONLY`). Without a decision, each Harness stays Connection failed with the missing action named, which meets the failure ACs but not the success ACs.

## Context links

- Stories: [epics.md:1135-1273](../2026-09-28-plane-local-cli-agents-epics/epics.md). Contracts: [architecture-contracts.md](./architecture-contracts.md) §5, §7, §10. Spine AD-4 table, AR13 (epics.md:229).
- Protocol references (from Spine AD-4): Codex app-server README, Grok headless guide and CLI reference, Omp RPC doc. Re-read the current versions before coding; record CLI versions in the probe report.

## Key decisions

- One driver module per Harness under `plane_agent_worker/drivers/`. Each implements the `drivers/base.py` contract from Phases 2-5: probe, models, start/resume, send, inject (optional), interrupt, settle, permission response, shutdown, event mapping.
- Codex: app-server JSON-RPC over stdio; models from `model/list`; steering candidate `turn/steer`; approvals mapped to deny in Q&A.
- Grok: headless streaming JSON turns with session resume; `midturn_input=false`; Plane queue and cancel-then-next-turn; model list from `grok models`. Connected requires a proven permission pause and safe response path (2.23 AC 3); otherwise Connection failed.
- Omp: stdio RPC (`prompt`, `steer`, `follow_up`, `abort`, UI response, `get_available_models`); questions map to `AgentRunQuestion(kind=harness)` from Phase 4.
- Runtime state (if Q1 accepts the exception): a per-Run, per-turn private runtime directory under the Run root (or tmpfs), writable only for that process, deleted after the turn; clone, credentials and other Runs stay read-only. The probe asserts writes to clone, Host, credentials and another Run fail.
- Plane tools (comments, questions) reach each Harness through MCP when the Harness supports MCP; otherwise the probe fails the matching check and names it. MCP support of Grok and Omp is [UNVERIFIED].

## File ownership

This phase owns only: `apps/agent-worker/plane_agent_worker/drivers/{codex,grok,omp}.py`, `drivers/__init__.py` (registry entries), `tests/fakes/{fake_codex,fake_grok,fake_omp}.py`, `tests/transcripts/{codex,grok,omp}/`, `tests/test_{codex,grok,omp}_driver.py`, and a runtime-directory helper `plane_agent_worker/runtime_dir.py` if Q1 accepts the exception. It does not touch `plane_agent_worker/code/` (Phase 7). Backend and web need no new files: harness cards, probe API and Run UI already support all four harnesses; add only i18n strings for harness-specific hints.

## Tests Before

1. Claude driver suite from Phases 2-5 passes unchanged.
2. Base driver contract tests run against the fake Claude to prove the shared contract does not change.

## Refactor

Protected by Tests Before 1-2: only `drivers/__init__.py` (registry) changes outside new files. The base driver contract does not change; if a Harness needs a contract change, stop and update Phases 2-5 tests first.

## Story steps and Tests After

| Story | Steps | Tests After |
| --- | --- | --- |
| 2.21 | Codex probe: transport, auth, `model/list`, events, follow-up, steer, cancel, approval, recovery | Fake Codex: full pass sets Connected with models; unauthenticated fake fails with recovery hint; native (Mini): real probe |
| 2.22 | Codex Q&A turns, queue, Send now via `turn/steer` if verified, Stop, resume, restart | Fake Codex: ordered conversation, steer acknowledgement before `accepted`, restart keeps Run ID, clone and cursor; native turn |
| 2.23 | Grok probe with permission pause/resume proof | Fake Grok: missing permission pause keeps Connection failed with named action; full pass sets Connected with live model list |
| 2.24 | Grok Q&A, resumed follow-up, Send now as cancel-then-next-turn, effect outside boundary blocked | Fake Grok: resume or rebuild; Send now cancels and settles first; write attempt blocked and recorded as event |
| 2.25 | Omp probe: `get_available_models`, prompt, steer, follow-up, abort, UI response, events, session recovery | Fake Omp: full pass; missing control fails with named action |
| 2.26 | Omp Q&A, queue, Send now, question answer, Stop, restart | Fake Omp: UI-response maps to question and answer; order kept; restart keeps Run ID and cursor; unrecoverable turn becomes error |

## Verification

```bash
cd apps/agent-worker && uv run pytest -m "not native and not docker" && uv run ruff check . && uv run ruff format --check .
cd apps/agent-worker && uv run pytest -m native tests/test_codex_driver.py tests/test_grok_driver.py tests/test_omp_driver.py   # Mini only, CLIs installed and logged in
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app -k "agent_harness_probe or agent_run"
pnpm --filter=@plane/i18n check:sync
```

Live check on the Mini: Connect each Harness in Integrations, mention it, follow up, Send now, Stop and resume. Record results per Harness in `reports/`.

## Success criteria

- [ ] All Given/When/Then cases of 2.21-2.26 pass with real CLIs on the Mini, or the Harness stays Connection failed with the named missing action and the user accepts that outcome.
- [ ] Q&A boundary probe passes for each connected Harness (AR13).
- [ ] Mockup rows I063, I064 (Codex states) and I075 pass browser review.

## Risks

| Risk | L x I | Mitigation |
| --- | --- | --- |
| Q1 not decided | High x High | Phase blocked; Phase 7 can proceed with Claude |
| CLI protocol change between versions | High x Medium | Version recorded in report; driver refuses unknown major versions; transcripts re-recorded |
| Grok cannot pause for permission | Medium x High | Grok stays Connection failed with "permission pause" named (2.23 AC 3) |
| Runtime directory leaks state between turns | Medium x High | Directory per Run and turn, deleted after exit; probe checks a second turn cannot read the first turn's runtime files |

## Rollback

Before the revert, select Disconnect for Codex, Grok and Omp in Integrations so no new mention targets a driver that will disappear. Then revert the PR. The Worker claim query filters by registered drivers, so it does not claim their pending Runs; those Runs stay readable and a member can mark them failed after they become Stale.
