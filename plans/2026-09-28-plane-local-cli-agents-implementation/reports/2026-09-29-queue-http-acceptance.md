# Ordered queue HTTP acceptance

## Scope and environment

Complete the native delivery checks identified in the [Queue UI report](./2026-09-29-queue-ui-progress.md).
Extend the existing paired HTTP fixture with `queue_restart` and `queue_active_restart` modes.
Both use the actual polling Worker, authenticated Claude, the production private MCP app, the Host OS boundary, real HTTP, and an isolated PostgreSQL database.
The initial Run, repository binding, and local Git clone are fixtures.
The API binds only to localhost port 8009.
No GitHub connection, browser mention creation, other Harness execution, or protected Code effect is claimed.

## Ordered delivery and restart after persistence

Hold the initial result request before Plane persists it.
While the Run remains in progress, submit two member messages through the real HTTP endpoint.
The pending queue reports their IDs in Plane order with positions 1 and 2 and state queued.
Release the initial result to reach the safe turn boundary.
The Worker dispatches the first message and native Claude reads the actual source through the Plane tool.
Plane records acceptance and completes turn 2 with the message's `QUEUE_1` marker.

Hold the turn-2 result response after Plane persists it.
The member API reports the first message accepted, the second queued, and the Run created for its next turn.
Kill the polling Worker and start a new Worker process.
The new Worker claims the same Run and delivers only the second message.
Claude returns its `QUEUE_2` marker in turn 3.
The pending queue is empty after completion.

The native side passes in 32.73 seconds and the API side passes in 32.74 seconds.

## Restart before persistence

Use the same initial ordered queue, but hold turn 2's result before Plane persists it.
The first message is already accepted, the second remains queued, and only turn 1 has a stored conclusion.
Kill the polling Worker.
Expire its lease through the production stale-run task in the isolated fixture.
The member sees stale and requests Retry pickup through the actual HTTP endpoint.
Release the old result request after lease expiry, then start the new polling Worker.

The new Worker reconciles the retained process record and claims the same Run with recovery enabled.
It reconstructs the accepted current message and committed observations through the production recovery context.
It completes turn 2 without a new queue dispatch or acceptance for that message.
It then dispatches the second queued message for turn 3.
Plane stores the correct `QUEUE_1` and `QUEUE_2` answers for those turns.
This is recovery of an accepted turn, not a second queue delivery.

The final native check passes in 43.33 seconds and the API check passes in 33.15 seconds.
Both modes store exactly one dispatch event and one acceptance event per message, in message order.
The API checks exact stored message states, turn numbers, completed conclusions, and lease generations.
The active mode also checks the recovery claim and acknowledged Retry pickup command.
No permission request is created and the source file remains unchanged.

## Fixture corrections and checks

The first API assertion expected a Worker ID in a claim event, but that event stores the lease generation and recovery flags.
The next assertion expected consecutive claim generations, but production result completion also increments the generation.
Read the event producer and result endpoint, then correct the fixture to the actual fenced sequences: 1, 3, 5 for completed-turn restart and 1, 3, 5, 7 for active-turn recovery.
The production behavior was unchanged.
Both corrected paired modes pass.
Focused Ruff lint and formatting pass for the changed fixture files.
The [Queue UI report](./2026-09-29-queue-ui-progress.md) retains the 16 API contracts, four Worker control checks, nine web checks, web types, focused lint, and direct browser evidence.

## Story 2.14 completion audit

| Acceptance criterion | Direct evidence |
| --- | --- |
| Active composer stores an ordered queued message without claiming acceptance | Real browser Enter submission and PostgreSQL state in the Queue UI report; two active-Run HTTP submissions and queue positions above |
| Composer distinguishes Queue and Reply | Same open production panel changes its input and send labels between active and awaiting states in the Queue UI report |
| Safe drain preserves Plane order and acceptance follows Harness acknowledgement | Actual native Claude turns, ordered HTTP dispatch and acceptance events above; Worker control check confirms no acceptance on init or failed result and acceptance after Harness output |
| Disclosure and durable queue survive reopen | Production browser Enter/Space, close/reopen, and full reload checks in the Queue UI report |
| Keyboard and screen reader queue controls are named and operable | Production browser keyboard disclosure, Send now, removal, visible focus, count, and ordered list checks in the Queue UI report |
| Worker restart does not deliver an accepted message twice | Both native restart boundaries above, including active accepted-message recovery and subsequent queued-message drain |

All six Story 2.14 criteria have direct evidence.
Other Harness conversation and steering stories retain their own conformance requirements.

## Review

**Summary:** Native queue delivery and two Worker restart boundaries now support all six Story 2.14 criteria.
**Critical issues:** None found in the delivered queue flow.
**Major issues:** The remaining 40 stories and four-Harness goal still require their own evidence.
**Minor issues:** The native flow starts from a seeded Run and local clone.
**Positive feedback:** The checks reuse the actual queue, lease, context, acknowledgement, and recovery contracts without a production test bypass.
**Questions:** AD-7 and DNS decisions remain pending and are not assumed.
**Verdict:** Mark Story 2.14 done and keep the complete goal active.

## Cleanup

Both owned native and API processes exit.
The isolated Compose containers and network are removed.
Private fixture directories and the temporary override are removed.
No owned listener remains on ports 8009, 8769, or 8811.
No Worker token or member session is stored in the report or checkout.
