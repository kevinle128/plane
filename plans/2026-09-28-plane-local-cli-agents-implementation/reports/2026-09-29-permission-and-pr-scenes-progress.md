# Permission and PR scene progress

## Permission accessibility defect

The [production browser check](../../../apps/web/tests/agent-permission-and-pr.e2e.mjs) creates separate declared audit fixtures in the isolated database.
It does not run protected effects or make GitHub requests.
The first browser run could not focus the full proposed effect because that scroll region lacked an accessible name and a keyboard focus target.
The red log is `/tmp/plane-permission-pr-red.log`.

The shared [permission card](../../../apps/web/core/components/issues/issue-detail/issue-activity/agent-run-permission.tsx) now makes the proposed command, permission scope, and full effect keyboard accessible.
Each region has a descriptive accessible name.
The existing card serves both current and historical permission requests.
No decision or effect authority changed.

## Browser evidence

The real web and API pass all three decisions: Allow for this Run, Allow once, and Deny.
Each decision produces exactly one saved decision event with an actor and timestamp.
No grant is consumed by this presentation check.
Focus moves to the saved card, and reload retains the decision stamp with no decision buttons.
The exact 10,001-character Unicode content remains available through the native disclosure and scrolls with PageDown.
The requested permission appears once in the timeline.

The confirmed PR fixture renders its title, branch, diff counts, Draft state, and human merge note in the panel.
Its link is keyboard accessible and uses a GitHub URL, a new-tab announcement, and `noopener noreferrer`.
The Activity card retains the Markdown conclusion and the compact repository/PR link.
This follows the current prototype's compact Activity link and detailed timeline PR card.
Light and Dark retain these fields and produce different semantic panel surface colors.
The desktop Light and Dark captures are `/tmp/plane-permission-pr-375.png.light.png` and `/tmp/plane-permission-pr-375.png.dark.png`.
The 375 px capture is `/tmp/plane-permission-pr-375.png`.
The inspected captures have no horizontal document overflow.
No page errors were recorded.
The final browser log is `/tmp/plane-permission-pr-green.log`.

## Gates and remaining scope

The existing PR render check passes.
Web type checking, targeted OxLint, and formatting pass.
The type log is `/tmp/plane-permission-pr-types.log` and retains existing tool configuration warnings.
All check processes exited; the existing browser, web, API, and isolated dependencies remain available.

This check proves member decisions and presentation, not protected execution or actual GitHub delivery.
The separate native Worker reports own protected effect evidence.
Complete the nine-criterion Story 2.8 audit and remaining panel accessibility and scene checks before changing sprint status.
The full goal remains active with 15 of 43 stories done.
