# Responsive title and comment menu repair

Story 2.8 remains in progress.
This report resolves narrow work-item title clipping and the concrete comment menu nesting warning found during timeline checks.

## Direct reproduction

The signed-in work-item page used the production web app and the isolated production API.
The archived AGENT-1 fixture title was Check Run controls with real Plane API.
At desktop width, the title textarea had a client height and scroll height of 30 px.
After changing the viewport to 375 px without editing the title, its width was 297 px, client height stayed 30 px, and scroll height increased to 60 px.
Its second line was clipped.
The [before capture](./title-ui/narrow-title-before.png) shows this defect.

The shared textarea hook only measured height after a value change.
It now observes the textarea width with the native ResizeObserver.
It measures height again only when client width changes, and it disconnects the observer during cleanup.
Height changes do not cause another resize cycle.
The full-page and peek title callers use this same TextArea and hook.
The repair does not add a global window listener or a new dependency.

The actual React console identified CommentQuickActions as the source of a button within another button.
CustomMenu owns its native trigger, but that caller supplied a complete IconButton as the trigger's child.
The same incorrect pattern existed in Cycle, Module, View, and work-item layout menus.
All five callers now supply the glyph and apply the existing icon button styling to CustomMenu's own button.
The triggers have accessible action names.
The shared menu's event and ARIA contract stays intact.

## Verification

The durable [browser check](../../../apps/web/tests/agent-title-and-comment-menu.e2e.mjs) uses a signed-in isolated AGENT-1 work-item page.
It changes viewport width to 1280, 375, 320, 960, and 375 px with the same saved title.
At each width, all textarea lines fit and the document has no horizontal overflow.
The check then creates a real member comment through the web UI and production API.
Enter, Space, and ArrowDown open the real Edit menu item and update the trigger's expanded state.
Escape closes the menu and returns focus to the single native trigger.
A full reload retains the saved comment.
The checked console contains neither the nested-button warning nor a ResizeObserver loop warning.
This does not claim that every unrelated browser warning is resolved.

The browser check passed after review and correction.
The [after capture](./title-ui/narrow-title-after.png) shows the complete wrapped title.
Both captures were inspected.
The direct browser check covers the comment menu; the other four callers have source, type, and lint verification, not complete browser journey evidence.

The UI package build passed.
UI and web type checks passed.
Focused OxLint passed with zero warnings and errors.
Focused formatting passed after formatting the corrected Cycle callback.

The focused lint check also exposed four existing promise return warnings in the touched callers.
The copy callbacks now return their final toast call.
Review caught an early toast return introduced in the Cycle restore callback before navigation.
The corrected callback displays the toast first and then returns the router call.
The reviewer confirmed that navigation is reachable and found no further concrete regression.
No full Cycle restore browser journey is claimed by this report.

## Remaining work and cleanup

Full Story 2.8 still needs its remaining design scenes, long transcript, full panel accessibility, all dropdown flows, and default-open focus evidence.
The earlier unidentified browser error must be assessed separately from the now-identified comment menu warning.
The verified story count stays at 15 of 43.

This check owns Compose project `plane-title-ui`, API port 8009, web port 3000, and browser session `plane-title-ui`.
All owned processes and test containers are stopped after verification.
Unrelated processes are kept.
