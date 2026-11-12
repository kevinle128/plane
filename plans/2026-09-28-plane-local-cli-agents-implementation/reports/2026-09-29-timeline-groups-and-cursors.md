# Run timeline groups and cursors

Story 2.8 remains in progress.
This report covers grouped work, additive history, live cursor delivery, keyboard disclosure, and completion retention.
It does not prove all design scenes or all Story 2.8 criteria.

## Reproduction and repair

The signed-in production web page used the isolated production Django API and a declared 120-event history fixture.
The initial panel showed 50 events with sequences 71–120 and no work group.
Selecting Load earlier activity replaced those events with sequences 21–70.
This removed the latest work from the visible timeline.

The panel now keeps loaded history and live events in sequence order and removes overlapping entries by event ID.
Older history uses the existing reverse cursor and adds each requested page.
Live delivery uses the existing forward cursor and drains each response before it requests the next page.
The initial request and each later request remain limited to 50 events.
The live cursor keeps polling while the member reads older work.
No API pagination contract changed.

Consecutive thought and tool events form a native details group.
Active work shows the number of tool steps.
Completed work shows measured elapsed time and keeps every loaded detail.
The first incomplete group labels its count and duration as loaded work.
This avoids presenting a partial page as the complete work history.
Native summary controls support Enter and Space.
New events retain a member's collapsed group.
Individual thought and tool details remain collapsed until the member opens them.
Event glyphs now use the design's 24 px column and distinguish thought, action, question, permission, error, conclusion, and PR events.

History can contain more than 50 permission request IDs.
The panel therefore uses separate permission requests with at most 50 IDs each, as required by the existing API.
Grouping makes one pass through the ordered events.
The merged history and groups are memoized so the elapsed-time clock does not sort the history again each second.
This is bounded-page and burst evidence, not proof of sustained production load or all long-transcript requirements.

## Direct checks

The durable [browser check](../../../apps/web/tests/agent-run-timeline.e2e.mjs) resets only the isolated AGENT-1 Run's declared history.
It does not replace API responses or claim native Harness execution.

- The latest 50 events show Working with 25 loaded steps.
- Enter and Space open and close the group.
- Two older requests retain all 120 events in exact sequence order.
- A 65-event burst arrives while history is open and produces all 185 unique events.
- The member's collapsed group stays collapsed during that burst.
- Completion adds event 186 and shows Worked for 3m 4s with 92 steps.
- Completion collapses the group; the keyboard can open it again and inspect tool input.
- A full reload opens the same Run and retains its conclusion.
- At 375 px, the document and panel are both 375 px wide with no horizontal overflow.

The browser check passed after review and after the last production change.
Both [completed work](./timeline-ui/completed-work.png) and [narrow reloaded work](./timeline-ui/narrow-reloaded-work.png) captures were inspected.
The current browser error query returned no errors; this does not settle the earlier unexplained error across all scenes.
The web process output at shutdown included a nested-button React warning from a Headless UI menu trigger that contains an IconButton.
The owner is not yet confirmed; reproduce and trace that menu before changing it.
This report does not claim a clean web console.

`node --test apps/web/tests/agent-run-ui.test.mjs` passed all nine tests.
`pnpm --filter=web check:types` passed.
Focused OxLint passed with zero warnings and errors.
Focused formatting checks passed.
The read-only reviewer found no concrete defect in this slice and confirmed that full Story 2.8 remains incomplete.

The first repeat type check rejected `toSorted` because the supported TypeScript library target does not include it.
The code now sorts a newly created array with the supported native method.
The final type check passed without changing the browser target.

## Remaining acceptance

Verify all applicable design scenes, full panel accessibility, long transcripts, all event-kind layouts, full dropdown flows, default-open focus, and narrow work-item title clipping.
Resolve the observed Headless UI menu and IconButton nesting warning.
Keep the 43-story goal active and retain the verified count of 15 completed stories.

## Process ownership

This check owned Compose project `plane-timeline-ui`, its API on port 8009, the web process on port 3000, and browser session `plane-timeline-ui`.
The owned processes and test containers are stopped after verification.
No unrelated container or process is stopped.
