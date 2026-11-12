# Stop acceptance

## Browser and persisted state

The [durable browser check](../../../apps/web/tests/agent-stop.e2e.mjs) uses the production web app and actual API with the isolated AGENT-1 fixture.
The prior lease, repository grant records, and private Worker token are explicit test state.
The test uses a real local Git clone outside the Plane checkout.
It does not replace API responses or claim that its acknowledgement client is a full Harness.

Native Enter opens Stop confirmation with the exact explanation that the action is interrupted, the repository is kept, and the message queue clears.
The background panel is inert while the named confirmation is open.
Native Cancel closes it and leaves the complete Run, message, command, and event rows unchanged.
Confirmed Stop clears all queued messages and disables duplicate Stop.
Before Worker acknowledgement, the Run remains in progress and the panel says that Stop is requested and waits for the current action to settle.
Full reload retains that pending state and the complete persisted state.

The native production PlaneClient reads the fenced Stop command and acknowledges it through actual HTTP.
Plane records Stopped with the signed-in member identity and the exact discarded message count.
The command acknowledgement time equals the Run finish time.
The original clone path, Git HEAD, clean worktree status, and README remain equal.
A late old-lease event receives 409 and leaves all persisted state unchanged.
After another full reload, the panel still shows Stopped and the same-Run reply explanation.
The [reload screenshot](./stop-ui/stopped-after-reload.png) records that retained timeline.
The complete browser and native acknowledgement check passes.
Scoped JavaScript lint, formatting, and syntax checks pass.

## Native Harness and protected action evidence

The [Worker HTTP report](./2026-09-28-worker-foundation-progress.md#published-commit-recovery-through-the-live-http-control-plane) records the passing normal approval and Stop regression with the actual polling Worker and authenticated Claude.
The corresponding native check reaches an unused pending write permission, sends confirmed Stop through the member endpoint, and waits for Stopped.
It verifies the retained Worktree and content, released capacity, and absent command container.
The actual Worker stops the Harness before acknowledging the fenced Stop command.
The later [active network-command Stop evidence](./2026-09-29-network-boundary-progress.md#active-network-command-stop) also interrupts a real running Docker command under native Claude and the polling Worker.
It confirms one execution, historical unknown settlement before capacity release and Stop acknowledgement, retained human edits and Git HEAD, and no later command or commit.

The [control report](./2026-09-29-stop-control-progress.md) records all 20 passing lease/control checks and six pending-Stop permission boundaries.
Its active Run has retained queue and Send now state before outsiders or restricted project guests attempt Stop.
Their 403 responses leave all persisted state unchanged.
The Worker settlement test records one cancelled queued message, one interrupted dispatched message, exact actor and acknowledgement time, and retained clone path.
The three focused authorization and settlement cases pass again in 2.11 seconds.

## Acceptance mapping

| Criterion | Direct evidence |
| --- | --- |
| Stop asks for confirmation and explains interruption, queue clearing, and retained clone | Actual keyboard browser dialog and explanation above |
| Fenced Stop interrupts Harness, prevents later effects, and records actor/time/discard count | Actual polling Worker and Claude pending-write and active-command Stop; permission rejection checks; exact browser/API event and timestamp assertions |
| Cancellation leaves Run running with no Stop command | Native Cancel with exact Run/message/command/event equality |
| Missing comment permission is rejected without changing state | Outsider and restricted guest 403 with existing queue and command equality |

The read-only review confirms all four Story 2.17 criteria and finds no concern within that scope.
Other Harness drivers and live GitHub behavior remain in their own unfinished stories.
The [stopped banner report](./2026-09-29-stopped-banner-progress.md) adds the design-specific member/time wording with exact acknowledgement time and pagination-independent API checks.
The actor and time are recorded and visible in the retained Stop timeline.
The complete 43-story goal remains active.
The sprint generator records Story 2.17 as done, with thirteen of 43 stories complete.

## Cleanup

The owned browser and web process are stopped.
The owned API container, Compose services, and network are removed.
No owned listener remains on ports 3000 or 8009.
The private Worker token, temporary Git clone, preparation script, and Compose override are removed.
The archived database fixture is retained.
