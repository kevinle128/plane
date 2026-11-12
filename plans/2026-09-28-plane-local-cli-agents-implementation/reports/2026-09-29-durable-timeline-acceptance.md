# Durable Run timeline acceptance

## Scope

This audit checks all nine acceptance criteria of Story 2.8 in the [epic breakdown](../../2026-09-28-plane-local-cli-agents-epics/epics.md).
The implementation uses the existing web, API, safe Markdown renderer, semantic theme tokens, and durable event cursors.
The evidence combines actual native Worker delivery with production browser presentation and API checks.
Declared browser fixtures prove presentation and do not claim native execution or GitHub delivery.

## Criterion evidence

| Criterion | Evidence | Result |
| --- | --- | --- |
| 1. Header, scrolling activity, fixed composer, ordered entry kinds, status and elapsed time | [Timeline groups](./2026-09-29-timeline-groups-and-cursors.md), [detail and Markdown](./2026-09-29-timeline-details-progress.md), [question composer](./2026-09-29-question-composer-progress.md), [errors](./2026-09-29-timeline-error-progress.md), [permission and PR](./2026-09-29-permission-and-pr-scenes-progress.md), and the fresh keyboard scroll and fixed geometry checks below | Pass |
| 2. Agent, work item, kind, status, start, active path, sandbox, elapsed and activity count | [Eight-state header check](./2026-09-29-run-status-progress.md) and inspected Code/Q&A panel captures | Pass |
| 3. Eight distinct states with label, icon and semantic color | [Run status check](./2026-09-29-run-status-progress.md) and current shared card/panel state mapping | Pass |
| 4. Full thought and action detail, active step count and completed duration | [Timeline groups](./2026-09-29-timeline-groups-and-cursors.md), [full Unicode input](./2026-09-29-timeline-details-progress.md), [full result parts](./2026-09-29-tool-result-browser-acceptance.md), and fresh exact completed thought/action checks | Pass |
| 5. Cursor reconciliation without missing or duplicate events | [1,002-event history](./2026-09-29-historical-plan-and-long-timeline.md), [native delivery](./2026-09-29-native-tool-results-progress.md), and fresh 65-event burst with exact sequence checks | Pass |
| 6. Same Run and durable history after close/reopen | [Result reload](./2026-09-29-tool-result-browser-acceptance.md), [native follow-up browser flow](./2026-09-29-follow-up-browser-acceptance.md), and fresh same-ID reload | Pass |
| 7. Keyboard and screen-reader disclosure, labels, status and focus | [Panel and peek focus](./2026-09-29-panel-peek-keyboard-progress.md), [status tree](./2026-09-29-run-status-progress.md), [permission focus](./2026-09-29-permission-and-pr-scenes-progress.md), and fresh named region and native disclosure accessibility-tree checks | Pass |
| 8. Plane/Propel semantic theme, spacing, icons and motion | [Actual profile theme selection](./2026-09-29-tool-result-browser-acceptance.md), [reduced motion](./2026-09-29-timeline-details-progress.md), [PR semantic surface changes](./2026-09-29-permission-and-pr-scenes-progress.md), and current component classes | Pass |
| 9. Streaming progress in panel; only card and conclusion in Activity | [Native tool delivery](./2026-09-29-native-tool-results-progress.md), [native follow-up in browser](./2026-09-29-follow-up-browser-acceptance.md), [streaming tail](./2026-09-29-timeline-details-progress.md), and fresh exclusion of audit detail from Activity | Pass |

## Fresh accessibility defects and repair

The expanded [timeline browser check](../../../apps/web/tests/agent-run-timeline.e2e.mjs) first reproduced the missing keyboard target on the main activity scroller.
The red log is `/tmp/plane-timeline-audit-red.log`.
The panel now has a named `Run activity` region, native keyboard focus, and a semantic focus outline.
PageDown scrolls this region while header and composer bounds stay unchanged.

A second actual accessibility-tree check omitted `Thought details` even though its `pre` had an `aria-label`.
A generic `pre` did not expose that name in the tree.
The bounded, focusable named scroll blocks now have a region role in the shared timeline and permission card.
This preserves content, disclosure controls, API authority, and the protected effect contracts.

The final browser check passes for 120 retained events, a 65-event live burst, exact ordered sequences, retained member disclosure state, measured completed duration, exact thought/action content, named regions in the accessibility tree, Activity exclusion, and same-Run reload.
The final log is `/tmp/plane-timeline-audit-green.log` and capture is `/tmp/plane-timeline-audit.png`.
Thirteen Run helper tests pass.
The final permission/PR browser gate also passes after review, including the named full-effect region in the accessibility tree, exact content, keyboard scroll, saved decisions and reload.
Its log is `/tmp/plane-permission-pr-final.log`.
Web type checking, targeted OxLint, and formatting pass after the region changes.
The type log is `/tmp/plane-timeline-audit-types.log`; existing tool configuration warnings remain visible.
Read-only review found no concrete defect or missing evidence for the nine criteria.
The sprint generator records Story 2.8 as done, for 16 of 43 stories done and 27 still in progress.
All three epics remain in progress.
The generator reports no orphan, illegal, or new entries.
Its two heading warnings refer to the document title and Epic List heading; all three epics and 43 stories are parsed.
All check processes exited; the owned browser, web, API and isolated dependencies remain available for the next story.

## Remaining whole-goal work

The broader design audit, other Harness conformance, live GitHub delivery, sustained load, and remaining story criteria stay in the full goal and their owning stories.
This Story 2.8 decision does not complete any epic or the full goal.
