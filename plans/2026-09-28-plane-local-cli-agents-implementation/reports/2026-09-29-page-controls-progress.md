# Work-item page control progress

## Scope and reproduction

This is partial UI acceptance work for Story 2.8.
Use the isolated archived AGENT-1 fixture with the actual API and web app.
Sign in through the email and password UI.
Before the repair, a fresh page has 15 nested native buttons.
Three project menu triggers wrap an IconButton, and four property dropdowns contain another native button in their display content.

## Repair

The shared property dropdown display now uses a span with the existing Button style helper.
All nine DropdownButton callers already provide the native trigger and its event handlers.
The project menu uses a span with the existing IconButton style helper inside the native CustomMenu trigger.
The menu callback moves to the existing menuButtonOnClick contract, and its outside-click ref still points at its display element.
No dependency or shared component contract is added.

## Verification

A fresh page has one native Todo state button and three project menu triggers with no button child or button ancestor.
Eight other nested native buttons remain on this fixture.
Clicking Todo opens the actual list with the saved Todo option.
The runnable browser check is `node apps/web/tests/agent-run-page-controls.e2e.mjs <signed-in-isolated-session>`.
Web type checking passes.
Focused OxLint passes with zero warnings and errors.
All nine existing Run UI and pull-request checks pass in 253 ms.
The UI package build and type checks pass after the exploratory edits are removed.

## Remaining defects

Enter changes the Headless UI expanded state without opening the property list.
The property dropdown has separate local and Headless UI open state.
An exploratory trigger handler opens the list, but it leaves aria-expanded false.
That incomplete change is removed, including its temporary public contract changes.
The keyboard and ARIA repair remains required.
The eight remaining nested buttons include header project selection, menus, relation actions, link, attachment, and popovers.
The 375 px screenshot has no document overflow, but the page content is visibly clipped beside the open navigation.
This is not a passing responsive-layout result and still requires repair.
The [375 px image](./page-controls-ui/single-controls-375.png) and [960 px image](./page-controls-ui/single-controls-960.png) record the actual page.

## Completion state

No story is marked done by this report.
The full goal remains active at nine completed stories out of 43.

## Review

The separate read-only review found no concrete regression in the scoped changes.
It confirmed the outer native triggers, existing style helpers, project menu ref, and callback contract.
Keyboard completion and full Story 2.8 acceptance remain open.

## Cleanup

The owned browser and web process are stopped.
The owned one-off API container and isolated Compose stack are removed.
No listener remains on test ports 3000 and 8009.
The temporary override is removed.

## Subsequent keyboard work

The [dropdown keyboard progress report](./2026-09-29-dropdown-keyboard-progress.md) records the later shared-state repair and selected passing keyboard, ARIA, calendar, and date-filter checks.
Its remaining-acceptance section governs the current keyboard status.

## Subsequent menu and narrow layout work

The [menu and narrow layout report](./2026-09-29-menu-and-narrow-layout-progress.md) records the later native action and submenu repair and passing 375 px overlay and focus checks.
Two nested controls and the remaining full Story 2.8 acceptance remain open.
