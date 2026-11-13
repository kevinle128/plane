# Stale retry browser and native claim progress

## Runtime check

The extended [durable browser check](../../../apps/web/tests/agent-stale-failure.e2e.mjs) now covers Retry pickup before Mark failed.
It uses the actual web app, Plane API, and isolated AGENT-1 fixture described in the [failure acceptance report](./2026-09-29-stale-failure-acceptance.md).
The current lease, repository grant records, and private Worker token are explicitly prepared test state.
The clone is a native Git clone outside the Plane checkout.
No API response is replaced.

After the production stale task runs, the panel shows the last progress time matching the exact database timestamp.
Native Enter on Retry pickup creates one pending retry command through the actual member API.
With no polling Worker running, the panel shows Stale and Retry pickup pending.
After full reload, it still shows Stale and pending, disables duplicate retry, and leaves the complete Run/event/turn/comment state unchanged.

## Reconciliation before a new lease

The test registers an actual isolated process group under the old lease as declared prior-process test state.
This process runs /bin/sleep; it is not a CLI Harness.
The native production PlaneClient cannot claim the pending retry without reconciliation and receives 409.
The process is still alive at that rejection.
Under the production Worker root lock, ProcessRegistry reconciles the registered process.
The test waits for its exit and verifies the record is cleared before asking Plane for a reconciled claim.
Plane grants a newer lease generation and reports recovered=true.
A progress event under the new lease is accepted.
The pending retry command is acknowledged, and the actual Run is in progress.

The original Worker then sends a late event and result through the native authenticated client.
Both return 409.
The complete persisted Run/event/turn/comment state remains equal to the reclaimed state.
The Git HEAD, worktree status, and README contents remain equal to their original values.
The test expires this new lease through the actual stale task and then repeats the complete failure acceptance flow.
The combined retry and failure check passes.
Scoped JavaScript lint, formatting, and syntax checks pass.

## Protected effect evidence to reconcile

The [Worker report](./2026-09-28-worker-foundation-progress.md#published-commit-recovery-through-the-live-http-control-plane) records actual polling Worker death and restart at commit receipt and delivery boundaries.
It verifies unchanged commits and branches, historical reconciliation before capacity release, and no new claim or effect.
The [push restart section](./2026-09-28-worker-foundation-progress.md#published-push-restart-through-http) records the equivalent actual polling Worker restart with an unchanged remote Run ref and no new command.
The [path report](./2026-09-28-path-access-progress.md) records external read, replacement write, and create-only restart modes.
Its deleted source or target checks prove that recovery reports retained results instead of reopening or recreating the external path.
These checks use actual protected effect implementations and native polling Worker recovery.
They do not prove every Harness or live GitHub publication.

The [lease progress report](./2026-09-29-stale-retry-progress.md) records the exact five-minute deadline, heartbeat renewal, recovery context, and old-generation API fencing.
The [completion report](./2026-09-29-stale-retry-acceptance.md) now reconciles these checks with the actual polling Worker and native Claude accepted-turn recovery and protected effect restart evidence.
