# Send now browser acceptance progress

## Scope

Close the production queue and timeline checks for Story 2.15 with the [durable browser check](../../../apps/web/tests/agent-send-now.e2e.mjs).
Use the actual web app, member session, production API and isolated PostgreSQL.
Worker responses are declared HTTP fixtures.
Actual CLI cancellation, acknowledgment ordering and selected-then-FIFO execution are proved by the [native check](./2026-09-29-send-now-native-progress.md).
The [timeout check](./2026-09-29-send-now-timeout-progress.md) separately proves the unverified-process response with a declared stop fault.
The browser fixture represents operator resolution before acknowledging the interruption; it does not prove native timeout recovery.

## Browser evidence

Queue two messages with the production composer and keyboard Send.
Focus Send message 2 now and press Enter.
The selected row becomes Send now pending while both messages remain queued and no acceptance timestamp exists.
The pending state survives a full browser reload.

Publish the actual Worker error event through its authenticated endpoint.
The timeline shows the process verification error and operator instructions while the queue stays pending and the Run stays on turn 1.
Both error and pending selection survive a full reload.

The declared Worker fixture acknowledges the interruption, claims turn 2 and dispatches the selected message through actual endpoints.
The row changes to Sending · not yet accepted, removal is disabled, and no message is accepted early.
That state survives another full reload.
Acknowledge the message and record its result, then dispatch and complete the remaining message in turn 3.
After full reload, both conclusions appear in selected-then-FIFO order, no pending queue remains, and the complete historical event prefix is unchanged.

## Review and verification

The complete browser check passes before review and again after fixing its result-presence assertion.
Review identified that an absent selected result could return index -1 and incorrectly satisfy the original order comparison.
Assert that the selected result is present before comparing its position with the final result.
Focused lint reports zero errors and warnings, and formatting passes.
The [rendered panel capture](./send-now-ui/completed-after-reload.png) records the retained timeline.
The rendered panel exposed three raw event names.
Use the existing event label map to show Run picked up, Sending follow-up, and Action interrupted for Send now.
The complete browser check passes again with explicit assertions for all three labels.
Web type checking passes after the label change.
This does not claim full design-scene acceptance or a clean browser console for Story 2.8.

## Environment and cleanup

An initial fixture restore overlapped migration and failed.
Reset only the disposable database schema, restore the archive, then apply all migrations in sequence before starting the API.
Private credentials and native Git fixture data stay outside the checkout.
Stop the owned browser, web and API processes and remove the Compose stack and private fixture after verification.

## Remaining acceptance

Keep Story 2.15 in progress for verified steering or fallback conformance across the other required Harnesses.
The overall goal remains all 43 stories, with 14 complete.
