# Historical plans and long Run timeline

Story 2.8 remains in progress.
This report covers immutable plan details and a 1,002-event timeline.
It does not prove every design scene or native result-stream conformance.

## Reproduction

The signed-in production panel used the isolated production Django API with declared history.
The API stored full steps and an estimate for a plan event.
The timeline displayed only Plan.
The browser check failed because the timeline row did not contain the stored step title.
The current composer plan still had its own latest snapshot, so it could not supply the older plan's detail.

## Repair

The panel now reads each plan event's own immutable payload.
Its native disclosure shows the completion count and reported estimate.
The member can open it to read titles and Done, In progress, or To do states.
An empty snapshot says Plan cleared.
The composer continues to use the latest plan endpoint and its existing saved disclosure preference.
Both surfaces use the same step renderer and semantic tokens.
The step list has a named keyboard focus target for scrolling.
The timeline uses the same plan glyph as the composer.

The plan payload guard checks the fields used by the renderer and rejects invalid step states or oversized lists.
Title and estimate bounds count Unicode code points, as the API does.
This avoids rejecting valid emoji text because JavaScript string length counts UTF-16 units.
No Worker, API, or migration contract changed.

## Evidence

The [durable browser check](../../../apps/web/tests/agent-plan-history.e2e.mjs) uses the real web app, signed-in member, API pagination, and latest-plan endpoint.
The history is a declared fixture, not native Harness output.

- One latest page and 20 older pages retain all 1,002 event IDs in exact sequence order.
- An older plan at sequence 51 keeps its titles, In progress and To do states, and 2m estimate.
- A newer plan at sequence 1,001 keeps its Done states and 3m estimate.
- The composer contains the newer plan and does not contain the older title.
- The empty plan at sequence 50 displays Plan cleared.
- Space and Enter toggle the historical plan, and Tab enters its named step list.
- The full 6,000-character Unicode thought and its trailing marker remain available.
- At 375 px the document has no horizontal overflow.
- A full reload opens the same Run with the retained latest plan event.

The check passed after the repair and review.
The [historical plan capture](./plan-history-ui/historical-plan.png) was inspected.
This fixture proves bounded long-history retrieval and rendering; it does not establish a maximum supported transcript or sustained production load.

All 10 focused UI helper tests passed.
The tests include malformed plan payloads and the API's emoji character bounds.
The web type check passed.
Focused OxLint passed with zero warnings and errors.
Focused formatting passed.
The read-only reviewer found no concrete defect in this slice.

## Remaining acceptance

Verify remaining design scenes, full panel and screen-reader navigation, full dropdown flows, default-open focus, the earlier unexplained browser error, and native tool-result stream retention.
The Claude driver currently ignores user stream records; inspect actual tool-result output before changing that mapping.
Keep Story 2.8 in progress and the verified story count at 15 of 43.

## Process ownership

This check owns Compose project `plane-timeline-ui`, API port 8009, web port 3000, and browser session `plane-plan-history`.
Owned processes and test containers are stopped after verification.
No unrelated process is stopped.
