---
phase: 5
title: "Steering, Stop and stale recovery"
status: todo
priority: P1
effort: "8.5d"
dependencies: [4]
---

# Phase 5: Steering, Stop and stale recovery

## Goal

Members queue messages during active work, send a queued message now, remove an undelivered message, stop and resume a Run, and recover or fail a stale Run, with honest delivery states and lease fencing. One PR, one commit per story 2.14-2.20.

<!-- 2026-11-14 --> Decisions Q31-Q35 ([plan.md](./plan.md#docker-sandboxes-decisions-2026-11-14)): the Harness process runs inside a Docker Sandbox, and a signal to the host `sbx exec` client does not stop it (spike question 3). Interrupt, settle, Stop and reconcile use the in-sandbox pidfile of [architecture-contracts.md §12](./architecture-contracts.md#12-docker-sandboxes-for-runs). Effort 8.5d (was 7.5d).

## Context links

- Stories: [epics.md:957-1133](../2026-09-28-plane-local-cli-agents-epics/epics.md). Contracts: [architecture-contracts.md](./architecture-contracts.md) §3 (`AgentRunMessage`, lease fields), §10, §12. Spine AD-3, AD-5, AD-6.
- Design: Screen 2 (Queue block, input row, Stop button, live line, Stop dialog, stale banner); scenes 2, 8, 10.
- Prior lessons: [queue HTTP](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-queue-http-acceptance.md), [send now native](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-send-now-native-progress.md), [send now timeout](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-send-now-timeout-progress.md), [queue removal](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-queue-removal-acceptance.md), [Stop](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-stop-acceptance.md), [stopped resume](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-stopped-resume-acceptance.md), [stale retry](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-stale-retry-acceptance.md), [stale failure](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-stale-failure-acceptance.md).

## State machine (message)

`queued -> dispatching -> accepted`; `queued -> cancelled` (remove or Stop); `dispatching -> interrupted` (lease lost or Harness failed before acknowledgement). Only Plane writes these states. `accepted` requires a Harness acknowledgement event from the driver.

## Key decisions

- Composer mode: `in_progress` shows Queue labels; other states show Reply labels (design status sentences).
- Drain: the Worker takes the lowest `position` queued message at a safe point, sets `dispatching` through the API, sends it, then reports `accepted` after the driver acknowledgement.
- Send now: Plane records `send_now_requested_at` on the selected message. If the driver capability `midturn_input=true`, the Worker injects it into the active turn. Otherwise it cancels the turn, waits for process exit or a 30 s timeout, then sends the message as the next turn. On timeout it reports an actionable error and does not start a second process in the CWD. <!-- 2026-11-14 --> Claude (Q19): always cancel-then-next-turn. The Claude driver reports `midturn_input=false` (Phase 2) and has no inject method; no hook-based injection (Q19; operator-listed hooks of Q32 are not used for it). The inject path stays in `drivers/base.py` for Codex (`turn/steer`) and Omp (`steer`) in Phase 6 and is tested here with a fake that declares `midturn_input=true`. Spec effect: none; 2.15 AC 2 (epics.md:1005-1007) is the Claude path and AC 1 (epics.md:1001-1003) applies only to a driver with verified midturn input.
- <!-- 2026-11-14 --> Interrupt and settle inside the sandbox (Q31): the driver sends the stream-json `interrupt` first. To end the process it runs `sbx exec <sandbox> sh -c 'kill -TERM "$(cat <pidfile>)"'`, and `kill -KILL` after 10 s. Settled means the host `sbx exec` client has exited and `kill -0` on the pidfile pid fails inside the sandbox. The 30 s Send now timeout and the Stop wait use this test. The host client is cleaned up only after the inner process is gone. `ProcessRegistry` records (Run, sandbox name, pidfile) next to the host client pid.
- Stop: member confirms; Plane records a Stop command with actor and time and cancels all `queued` messages (count stored). The Worker interrupts the Harness (as above), blocks later tool calls in that turn, waits for exit, then acknowledges. Status becomes `stopped` with discarded count. Clone is kept.
- Resume from stopped: reply creates a new turn on the same Run; the Worker verifies clone path, remote and inode on the host and runs the sandbox health check (§12) before launch; the remote check compares with the snapshot `clone_url` (stored without credentials for every provider); failure is a recoverable error with Retry.
- Retry pickup: allowed only when derived Stale. Plane increments `lease_generation`, clears the lease owner, and returns the Run to pickup. A GitLab `git-credential` request with the old generation returns 409, so a stale Worker cannot fetch or push after Retry. The claiming Worker reconciles the process registry before it starts: <!-- 2026-11-14 --> for each recorded pidfile of the Run it kills the inner process in the sandbox (as above), then stops the old host client group. At Worker start it does the same for every pidfile under the scratch folders of its sandboxes whose Run it does not hold. Accepted messages and completed effects are never replayed without a new user command.
- Mark failed: allowed only when Stale; records actor, time, reason; old-generation writes return 409 and do not change the conclusion.
- Permission for all commands: work-item comment permission (same guest rule as `comment.py:103-118`).

## Files

Create (backend): `apps/api/plane/agent/services/{queue,stop,stale_recovery}.py`; migration `<next>_agent_run_commands` (generated, if fields change); tests `test_agent_run_queue.py`, `test_agent_run_send_now.py`, `test_agent_run_stop.py`, `test_agent_run_resume.py`, `test_agent_run_stale.py`.

Modify (backend): `apps/api/plane/app/views/agent/runs.py`, `apps/api/plane/agent/worker_api/views.py`, `apps/api/plane/agent/services/lease.py`.

Worker: extend `plane_agent_worker/{loop,process_registry,sandbox}.py`, `drivers/base.py` (interrupt, settle, inject), `drivers/claude.py`; tests `tests/test_queue_drain.py`, `tests/test_send_now.py`, `tests/test_stop.py`, `tests/test_recovery.py`.

Create (web): `packages/blocks/src/agent-run/{queue-state.ts,queue-section.tsx,stop-dialog.tsx,stale-banner.tsx}` with tests; `apps/web/components/agent-run/{queue-block,stop-button,live-line,stale-actions}.tsx`.

Modify (web): `apps/web/components/agent-run/composer.tsx`, `apps/web/components/agent-run/panel-header.tsx`, `apps/web/store/agent/run.store.ts`, `apps/web/services/agent/run.service.ts`, `packages/i18n/src/locales/*/agent.json`.

## API endpoints

| Path                                                                                                                  | Auth                 | Story      |
| --------------------------------------------------------------------------------------------------------------------- | -------------------- | ---------- |
| `POST .../agent-runs/<id>/messages/<mid>/send-now/`                                                                   | comment permission   | 2.15       |
| `DELETE .../agent-runs/<id>/messages/<mid>/`                                                                          | comment permission   | 2.16       |
| `POST .../agent-runs/<id>/stop/`                                                                                      | comment permission   | 2.17       |
| `POST .../agent-runs/<id>/retry-pickup/`, `POST .../agent-runs/<id>/mark-failed/`                                     | comment permission   | 2.19, 2.20 |
| `GET api/agent-worker/v1/runs/<id>/commands/`, `POST .../messages/<mid>/dispatching/`, `POST .../commands/<cid>/ack/` | Worker token + lease | 2.14-2.18  |

## Tests Before

1. Phase 4 follow-up tests pass unchanged (reply on idle Run still starts a turn).
2. Lease renewal and old-generation rejection tests from Phase 3 pass.

## Refactor

Protected by Tests Before 1-2: `lease.py` gains a generation bump for Retry pickup; the composer gains Queue mode; follow-up on an idle Run keeps the Phase 4 path.

## Story steps and Tests After

| Story | Steps                                                                                 | Tests After                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ----- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2.14  | Queue on active Run, positions, drain, accepted after ack, disclosure, restart safety | API: queued with order; no `accepted` without Worker ack; Worker: drain order; restart after accepted does not redeliver; blocks vitest: waiting count, Reply vs Queue labels, named actions                                                                                                                                                                                                                                                          |
| 2.15  | Send now with native injection or cancel-then-next-turn, pending states, timeout      | Worker: fake with `midturn_input=true` injects; fake without it cancels, waits, sends next turn; <!-- 2026-11-14 --> the Claude driver never injects, even when a fake Claude echoes a queued message during a turn (Q19); native (Mini): Claude Send now cancels, settles and sends the message as the next turn in the same session; stuck fake hits timeout and reports error with no second process; API: pending state visible, event order kept |
| 2.16  | Remove queued, conflict for dispatching/accepted                                      | API: queued -> cancelled and never claimed; dispatching/accepted returns 409 with actual state; audit event kept, waiting count excludes it                                                                                                                                                                                                                                                                                                           |
| 2.17  | Stop confirm, fenced command, interrupt, discarded count                              | API: guest without comment right 403 and state unchanged; stop records actor, time, count; Worker: interrupt sends the stream-json `interrupt`, then the pidfile kill through `sbx exec` (fake `sbx` records both), and blocks later tool calls; a host client killed first does not count as settled; native: Stop ends the process inside the sandbox; browser: confirm and Cancel paths, scene 10                                                                                                                                                                                                                                             |
| 2.18  | Resume stopped Run                                                                    | Worker: same clone path and inode; unverifiable clone gives recoverable error and no launch; a missing sandbox is recreated and the turn rebuilds context (Q35); API: new turn on same Run ID with history                                                                                                                                                                                                                                                                                                                |
| 2.19  | Derived Stale with last progress, Retry pickup with new generation, reconcile         | API (freezegun): 5 min without renewal reads Stale; retry increments generation; old generation 409 (events and `git-credential`); Worker: reconcile kills the old in-sandbox process by its pidfile before resume, and a Worker restart kills orphan pidfile processes it does not own; no replay of an accepted message; Worker absent keeps Stale/waiting                                                                                                                                                                                             |
| 2.20  | Mark failed                                                                           | API: records actor, time, reason; later old-generation event 409 and conclusion unchanged; guest 403                                                                                                                                                                                                                                                                                                                                                  |

## Verification

```bash
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app -k "agent_run"
docker compose -f docker-compose-test.yml run --rm api-tests python manage.py makemigrations --check --dry-run
cd apps/api && uv run ruff check .
cd apps/agent-worker && uv run pytest -m "not native and not docker" && uv run pytest -m native tests/test_stop.py tests/test_recovery.py   # Mini only
pnpm --filter=@plane/blocks test && pnpm turbo run check:types --filter=web --filter=@plane/blocks
pnpm check:lint && pnpm --filter=@plane/i18n check:sync
```

## Success criteria

- [ ] All Given/When/Then cases of 2.14-2.20 pass for Claude.
- [ ] The UI never shows a message as delivered before `accepted` (blocks test and browser check after reload).
- [ ] Mockup rows I025-I031, I044 pass browser review.

## Risks

| Risk                                      | L x I           | Mitigation                                                                            |
| ----------------------------------------- | --------------- | ------------------------------------------------------------------------------------- |
| Claude Send now loses in-flight tool work | High x Low      | Accepted by Q19; the session resumes, and the timeline shows the cancelled turn       |
| Process does not exit after interrupt     | Medium x High   | Timeout, in-sandbox `kill -KILL` by pidfile, registry record kept; Run shows error; no competing turn |
| <!-- 2026-11-14 --> Pidfile missing or stale (process ended, pid reused in the VM) | Low x Medium | The pidfile is written by the `sh -c` wrapper that `exec`s the CLI, so the pid is the CLI; the Worker removes the pidfile when the client exits; a missing pidfile with a live client falls back to the stream-json `interrupt` and the timeout |
| Late poll restores an older status        | Medium x Medium | Store applies projections by `seq` only (prior lesson)                                |

## Rollback

Revert the PR. If the migration adds fields, migrate `db` back to the Phase 4 migration. Queued messages created during the phase become plain stored messages that the Phase 4 code delivers as follow-ups.
