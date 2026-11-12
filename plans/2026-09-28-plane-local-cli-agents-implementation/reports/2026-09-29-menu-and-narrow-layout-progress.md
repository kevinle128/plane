# Menu and narrow layout progress

## Scope and reproduction

This is partial acceptance work for Story 2.8.
The isolated AGENT-1 page uses the actual Plane API, archived database fixture, and email/password sign-in.
The previous page has eight nested native buttons.
The widget displays, work-item action display, and activity filter display account for six repaired controls.
The breadcrumb project control and emoji reaction control remain nested.

Enter on the work-item action trigger changes expanded ARIA but renders no menu items.
The shared CustomMenu has separate local and Headless UI state.
Keyboard selection in the relation menu closes the popup without invoking the child button callback.
The library registers an outer div rather than the native button.
After registering the submenu button, Enter still closes the parent before the submenu can open.
The declared component fixture reproduces this second failure.

At 375 px, a desktop browser keeps the old sidebar in normal document flow because the old placement depends on the user agent.
The title field has only 47 px of width at x=283 beside the open sidebar.
The [original open layout](./menu-controls-ui/original-open-375.png) records the clipping.

## Repair

Widget, action, and filter displays reuse the existing style helpers on noninteractive spans.
Their owning native triggers retain events and disabled behavior.
The attachment control uses the native button as its dropzone root and invokes the dropzone click handler before stopping propagation.
Activity filter choices are native buttons.

Headless UI owns menu state, and the conditional popup mirrors that state in a layout effect.
Closing uses the library render-prop close callback.
Menu item and submenu registration use the existing native buttons through Fragment.
The menu key handler reads the actual active descendant and activates a submenu trigger before the parent handles Enter, Space, or ArrowRight.
The submenu trigger prevents default click closure and exposes expanded ARIA.

The sidebar uses absolute placement below the existing md breakpoint and relative placement above it.
Closed sidebar and inactive peek content use native inert.
Sidebar controls have accessible names, expanded state, and a controlled element ID.
Closing returns focus after the conditional header control mounts.
The pending animation frame is cancelled on cleanup.
The open overlay retains the title width at 297 px and x=33.
The document width remains 375 px.
See the [open overlay](./menu-controls-ui/overlay-open-375.png) and [closed page](./menu-controls-ui/overlay-closed-375.png).

## Verification

Run `node apps/web/tests/agent-menu-controls.e2e.mjs <signed-in-isolated-session>` against the existing isolated web server.
The native production flow passes action menu Enter, Space, ArrowDown, accessible items, Escape, and focus return.
Keyboard relation selection opens the real relation modal.
The link control opens its real modal.
Activity filter options and focus return pass.
The five named widget/filter actions have no native button child or ancestor.
The attachment root is a native control.
Actual upload and drag/drop delivery are not proved by this check.

The narrow flow passes overlay geometry, retained content width, document width, native inert, and focus return.
The public submenu API uses a declared Strict Mode component fixture because CE does not currently render the nested copy-menu branch.
It uses the built UI package and native browser events and replaces no product API.
Enter, Space, and ArrowRight each open the submenu.
ArrowDown and Enter invoke its callback exactly once and close the menu.
The fixture imports the actual framework HMR initialization module found in the live server HTML.
The [React Router source](https://github.com/remix-run/react-router/blob/main/packages/react-router-dev/vite/plugin.ts) describes this initialization contract.
Temporary fixture files are removed even if restoring the browser page fails.

The existing page-controls browser check passes again after the shared menu repair.
State keyboard entry and ARIA, search Escape, closing Escape, Tab, priority persistence and restoration, calendar keyboard entry, and default-open single/range filters pass.
UI build, UI types, and web types pass.
Scoped lint and formatting pass across the eight touched files.
The final serial submenu test helper also passes lint and formatting.
Nine Run UI and pull-request checks pass.
The separate opt-in live polling test is skipped and is not counted as a pass.
The read-only review finds no concrete regression after the focus and fixture-cleanup repairs.

## Remaining acceptance

No additional story is marked done.
Nine of 43 stories remain complete.
Two nested buttons remain in the breadcrumb and emoji reaction controls.
All 11 dropdown flows, default-open focus after replacing another popup, full panel accessibility, long transcripts, and design-scene fidelity still require acceptance evidence.
The previously retained undefined browser error has no confirmed source.
This report makes no clean-console or full Story 2.8 completion claim.

## Cleanup

The owned controls-ui browser and web listener are stopped.
The owned one-off API container and plane-controls-ui Compose stack and network are removed.
No owned listener remains on ports 3000 or 8009.
The temporary override and diagnostic images are removed after the selected images are copied into this report directory.
The archived fixture dump remains available for subsequent acceptance work.

## Subsequent breadcrumb and reaction work

The [breadcrumb and reaction report](./2026-09-29-breadcrumb-and-reaction-progress.md) records the later two-control repair, zero nested buttons on the real web work item, and actual reaction persistence and removal.
Its remaining-acceptance section governs current control status.
