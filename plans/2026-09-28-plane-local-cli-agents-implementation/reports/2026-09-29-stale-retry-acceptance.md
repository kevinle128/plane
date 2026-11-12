# Stale retry acceptance

## Completion evidence

Story 2.19 meets its four accepted criteria through the shared API and Worker behavior, the actual browser flow, and native Claude recovery.
The [lease report](./2026-09-29-stale-retry-progress.md) proves the exact five-minute deadline, heartbeat renewal, retained last progress and history, and old-generation fencing.
The [browser and native claim report](./2026-09-29-stale-retry-browser-progress.md) proves keyboard Retry pickup, pending Stale after reload while the Worker is unavailable, registered process termination before a new claim, retained clone, and rejected old event and result with unchanged persisted state.
The combined browser check passes, and the current full lease suite passes all 19 checks in 6.11 seconds.
Scoped JavaScript lint, format, and syntax checks pass.
The native process fixture in that browser check is an explicit sleep process; it alone does not prove Harness resume.

## Actual Harness restart

The [Queue HTTP acceptance report](./2026-09-29-queue-http-acceptance.md#restart-before-persistence) provides the actual polling Worker and authenticated Claude recovery evidence.
It kills the old polling Worker after the current message is accepted but before the turn result reaches Plane.
The production stale task expires the lease, and the member requests Retry pickup through the actual HTTP endpoint.
The new polling Worker reconciles the retained process record and claims the same Run with recovery enabled.
It reconstructs the accepted current message and committed observations from the durable recovery context.
Claude completes that same accepted turn and the next queued turn without another dispatch or acceptance for the recovered message.
The check verifies the new recovery lease and acknowledged retry command.

## Protected effects

The [commit restart evidence](./2026-09-28-worker-foundation-progress.md#published-commit-recovery-through-the-live-http-control-plane) and [push restart evidence](./2026-09-28-worker-foundation-progress.md#published-push-restart-through-http) use actual polling Worker death and restart, native Git, retained results, and historical acknowledgement before capacity release.
They retain the exact commit and remote Run ref without another claim, command, or protected effect.
The [path recovery evidence](./2026-09-28-path-access-progress.md) covers external reads, replacement writes, and create-only writes with deleted sources or targets and retained human edits.
Recovery reports the retained result without reopening or recreating the external file.
The [network command recovery evidence](./2026-09-29-network-boundary-progress.md) covers completed-result loss, death during execution, and consumed permission before command creation.
Its execution counter remains one, or absent when launch never occurred, and historical reconciliation precedes journal clearance and capacity release.
Recovery does not launch the retained command.
Unknown or uncertain effects remain retained or are reported as unknown; recovery does not authorize a repeat.

## Acceptance mapping

| Criterion | Direct evidence |
| --- | --- |
| No Worker update for five minutes shows Stale, last progress, Retry pickup, and retained history | Exact deadline API test, actual stale task, browser timestamp comparison, retained event rows and clone |
| Retry creates a new fenced lease after prior process reconciliation | Native process and actual HTTP claim check; actual polling Worker and native Claude recovery in Queue HTTP acceptance |
| Recovery does not replay an external effect without a new user command | Actual polling Worker commit, push, path, and command restart checks with unchanged effect counts and retained results |
| Unavailable Worker leaves honest pending state | Actual browser Enter retry, one pending command, visible Stale/pending after full reload, disabled duplicate retry, unchanged persisted state |

The read-only review confirms all four criteria using this combined evidence.
This completion does not establish other Harness drivers, live GitHub transport, or complete network permission product flows.
Those remain in their separate unfinished stories.
The complete 43-story goal remains active.
The two focused timing and retry API checks pass again after review in 1.50 seconds.
The sprint generator records Story 2.19 as done, with twelve of 43 stories complete.

## Cleanup

The owned browser, web process, API container, Compose services, and network are stopped or removed.
No owned listener remains on ports 3000 or 8009.
The private Worker token, temporary Git clone, preparation script, and Compose override are removed.
The process check waits for its owned registered process before returning.
The archived database fixture is retained.
