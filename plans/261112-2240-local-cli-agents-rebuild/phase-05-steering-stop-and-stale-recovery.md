---
phase: 5
title: "Steering, Stop and stale recovery"
status: todo
priority: P1
effort: "8d"
dependencies: [4]
---

# Phase 5: Steering, Stop and stale recovery

## Goal

Members queue messages during active work, send a queued message now, remove an undelivered message, stop and resume a Run, and recover or fail a stale Run, with honest delivery states and lease fencing. One PR, one commit per story 2.14-2.20.

## Context links

- Stories: [epics.md:957-1133](../2026-09-28-plane-local-cli-agents-epics/epics.md). Contracts: [architecture-contracts.md](./architecture-contracts.md) §3 (`AgentRunMessage`, lease fields), §10. Spine AD-3, AD-5, AD-6.
- Design: Screen 2 (Queue block, input row, Stop button, live line, Stop dialog, stale banner); scenes 2, 8, 10.
- Prior lessons: [queue HTTP](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-queue-http-acceptance.md), [send now native](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-send-now-native-progress.md), [send now timeout](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-send-now-timeout-progress.md), [queue removal](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-queue-removal-acceptance.md), [Stop](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-stop-acceptance.md), [stopped resume](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-stopped-resume-acceptance.md), [stale retry](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-stale-retry-acceptance.md), [stale failure](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-stale-failure-acceptance.md).

## State machine (message)

`queued -> dispatching -> accepted`; `queued -> cancelled` (remove or Stop); `dispatching -> interrupted` (lease lost or Harness failed before acknowledgement). Only Plane writes these states. `accepted` requires a Harness acknowledgement event from the driver.

## Key decisions

- Composer mode: `in_progress` shows Queue labels; other states show Reply labels (design status sentences).
- Drain: the Worker takes the lowest `position` queued message at a safe point, sets `dispatching` through the API, sends it, then reports `accepted` after the driver acknowledgement.
- Send now: Plane records `send_now_requested_at` on the selected message. If the driver capability `midturn_input=true`, the Worker injects it into the active turn. Otherwise it cancels the turn, waits for process exit or a 30 s timeout, then sends the message as the next turn. On timeout it reports an actionable error and does not start a second process in the CWD.
- Stop: member confirms; Plane records a Stop command with actor and time and cancels all `queued` messages (count stored). The Worker interrupts the Harness, blocks later tool calls in that turn, waits for exit, then acknowledges. Status becomes `stopped` with discarded count. Clone is kept.
- Resume from stopped: reply creates a new turn on the same Run; the Worker verifies clone path, remote and inode before launch; failure is a recoverable error with Retry.
- Retry pickup: allowed only when derived Stale. Plane increments `lease_generation`, clears the lease owner, and returns the Run to pickup. The claiming Worker reconciles the process registry (stop old process group) before it starts. Accepted messages and completed effects are never replayed without a new user command.
- Mark failed: allowed only when Stale; records actor, time, reason; old-generation writes return 409 and do not change the conclusion.
- Permission for all commands: work-item comment permission (same guest rule as `comment.py:103-118`).

## Files

Create (backend): `apps/api/plane/agent/services/{queue,stop,stale_recovery}.py`; migration `<next>_agent_run_commands` (generated, if fields change); tests `test_agent_run_queue.py`, `test_agent_run_send_now.py`, `test_agent_run_stop.py`, `test_agent_run_resume.py`, `test_agent_run_stale.py`.

Modify (backend): `apps/api/plane/app/views/agent/runs.py`, `apps/api/plane/agent/worker_api/views.py`, `apps/api/plane/agent/services/lease.py`.

Worker: extend `plane_agent_worker/{loop,process_registry}.py`, `drivers/base.py` (interrupt, settle, inject), `drivers/claude.py`; tests `tests/test_queue_drain.py`, `tests/test_send_now.py`, `tests/test_stop.py`, `tests/test_recovery.py`.

Create (web): `packages/blocks/src/agent-run/{queue-state.ts,queue-section.tsx,stop-dialog.tsx,stale-banner.tsx}` with tests; `apps/web/components/agent-run/{queue-block,stop-button,live-line,stale-actions}.tsx`.

Modify (web): `apps/web/components/agent-run/composer.tsx`, `apps/web/components/agent-run/panel-header.tsx`, `apps/web/store/agent/run.store.ts`, `apps/web/services/agent/run.service.ts`, `packages/i18n/src/locales/*/agent.json`.

## API endpoints

| Path | Auth | Story |
| --- | --- | --- |
| `POST .../agent-runs/<id>/messages/<mid>/send-now/` | comment permission | 2.15 |
| `DELETE .../agent-runs/<id>/messages/<mid>/` | comment permission | 2.16 |
| `POST .../agent-runs/<id>/stop/` | comment permission | 2.17 |
| `POST .../agent-runs/<id>/retry-pickup/`, `POST .../agent-runs/<id>/mark-failed/` | comment permission | 2.19, 2.20 |
| `GET api/agent-worker/v1/runs/<id>/commands/`, `POST .../messages/<mid>/dispatching/`, `POST .../commands/<cid>/ack/` | Worker token + lease | 2.14-2.18 |

## Tests Before

1. Phase 4 follow-up tests pass unchanged (reply on idle Run still starts a turn).
2. Lease renewal and old-generation rejection tests from Phase 3 pass.

## Refactor

Protected by Tests Before 1-2: `lease.py` gains a generation bump for Retry pickup; the composer gains Queue mode; follow-up on an idle Run keeps the Phase 4 path.

## Story steps and Tests After

| Story | Steps | Tests After |
| --- | --- | --- |
| 2.14 | Queue on active Run, positions, drain, accepted after ack, disclosure, restart safety | API: queued with order; no `accepted` without Worker ack; Worker: drain order; restart after accepted does not redeliver; blocks vitest: waiting count, Reply vs Queue labels, named actions |
| 2.15 | Send now with native injection or cancel-then-next-turn, pending states, timeout | Worker: fake with `midturn_input=true` injects; fake without it cancels, waits, sends next turn; stuck fake hits timeout and reports error with no second process; API: pending state visible, event order kept |
| 2.16 | Remove queued, conflict for dispatching/accepted | API: queued -> cancelled and never claimed; dispatching/accepted returns 409 with actual state; audit event kept, waiting count excludes it |
| 2.17 | Stop confirm, fenced command, interrupt, discarded count | API: guest without comment right 403 and state unchanged; stop records actor, time, count; Worker: interrupt stops process group and blocks later tool calls; browser: confirm and Cancel paths, scene 10 |
| 2.18 | Resume stopped Run | Worker: same clone path and inode; unverifiable clone gives recoverable error and no launch; API: new turn on same Run ID with history |
| 2.19 | Derived Stale with last progress, Retry pickup with new generation, reconcile | API (freezegun): 5 min without renewal reads Stale; retry increments generation; old generation 409; Worker: reconcile stops old process before resume; no replay of an accepted message; Worker absent keeps Stale/waiting |
| 2.20 | Mark failed | API: records actor, time, reason; later old-generation event 409 and conclusion unchanged; guest 403 |

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

| Risk | L x I | Mitigation |
| --- | --- | --- |
| Claude has no verified midturn input | High x Low | Capability flag false; cancel-then-next-turn path is the default and fully tested |
| Process does not exit after interrupt | Medium x High | Timeout, process-group kill, registry record kept; Run shows error; no competing turn |
| Late poll restores an older status | Medium x Medium | Store applies projections by `seq` only (prior lesson) |

## Rollback

Revert the PR. If the migration adds fields, migrate `db` back to the Phase 4 migration. Queued messages created during the phase become plain stored messages that the Phase 4 code delivers as follow-ups.
