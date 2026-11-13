# Dropdown keyboard progress

## Scope and reproduction

This is partial UI acceptance work for Story 2.8.
The real isolated AGENT-1 page initially reports an expanded Todo trigger after Enter but renders zero state options.
The caller and Headless UI had separate open states.
The separate reviewer also found that mirroring the library's initial closed state removes the date filters' existing defaultOpen behavior.
Both single-date and range-date production filters use this contract.

## Repair

Headless UI now owns the popup state.
The shared ComboDropDown mirrors that state before the caller mounts its conditional content and search input.
The registered native trigger remains reachable through Tab.
A hidden field label names the trigger, input, and options through the library's label contract.
Escape restores native trigger focus after popup teardown.
A nonempty search query clears on the first Escape and closes on the second Escape.
Selection closes through the registered trigger, and callbacks run on state transitions.
All 11 property dropdown callers use this contract.
The root remains mounted while popup content stays conditional.
This removes the old lazy-root optimization; large-list performance still needs acceptance evidence.

Date defaultOpen activates the registered native trigger once after mount.
The timer is cancelled on cleanup, and a disabled native trigger cannot open the popup.
The date callers begin with a closed mirror rather than a competing default-open state.

The real Filter toggle also failed after a Strict Mode cleanup removed the filter that render-time memoization had registered.
Filter registration and deletion now share one effect lifetime.
Current expression options and callbacks update separately without replacing the filter on each callback change.

The date operator options existed in the DOM but their wrapper was inert and absent from the accessibility snapshot.
CustomSearchSelect now uses the library's nonmodal options mode.
Its single-selection close callback runs through onChange for pointer and keyboard selection.

## Verification

Run `node apps/web/tests/agent-run-page-controls.e2e.mjs <signed-in-isolated-session>` on the documented isolated AGENT-1 fixture.
The fixture must contain the normal Triage state as well as Todo.
The archived fixture lacked Triage; a real isolated database state was added before the filter checks.
No production response was replaced.

The final browser run passes native single-button checks for the state and project menus.
Enter, Space, and ArrowDown open the real state options with both trigger and search-input ARIA expanded.
Escape, query clearing, second Escape, and Tab pass.
Priority keyboard selection persists Low after reload and restores None after another reload.
Calendar Enter opens the real grid, Tab enters its previous-month control, and Escape returns native trigger focus.
An empty single-date filter automatically opens its calendar.
Switching the operator to between automatically opens the incomplete range calendar.
The operator options are accessible and selectable.
Both calendars close from their internal controls, and the test removes its filters before returning to the work item.

UI build, UI types, web types, and formatting pass.
Scoped OxLint reports zero warnings and errors across 32 files.
Nine Run UI and pull-request checks pass; the separate live polling check is skipped by its own opt-in gate and is not counted as a pass.
The read-only review found no concrete regression after the defaultOpen and lifetime repairs.
The final browser rerun completed after the review.

The shared library contract follows the [Headless UI Combobox documentation](https://headlessui.com/react/combobox).
The callback notification and filter registration use the current [React useEffectEvent contract](https://react.dev/reference/react/useEffectEvent).

## Remaining acceptance

No story is marked done by this report.
Nine stories remain complete out of 43.
The full acceptance of all 11 dropdown flows is not proved by these selected browser checks.
Default-open focus after replacing another popup still needs a dedicated check; the automatic-open checks establish visible content and expanded ARIA only.
Eight nested native buttons and the clipped 375 px work-item page remain from the earlier report.
The browser error command also retains an undefined error whose source is not identified in this check.
No clean-console claim is made.
Full panel accessibility, design-scene fidelity, and long transcript acceptance remain open.

## Cleanup

The owned browser, web listener, one-off API container, and isolated Compose services are stopped and removed.
No owned listener remains on ports 3000 or 8009, and the isolated network is removed.
The temporary override and diagnostic files are removed.
The archived fixture dump is retained for the remaining acceptance work.

## Subsequent menu and narrow layout work

The [menu and narrow layout report](./2026-09-29-menu-and-narrow-layout-progress.md) records the later native action and submenu repair and passing 375 px overlay and focus checks.
Two nested controls and the remaining full Story 2.8 acceptance remain open.
