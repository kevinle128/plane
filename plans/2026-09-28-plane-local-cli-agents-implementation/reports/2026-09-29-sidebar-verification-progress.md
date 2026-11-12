# Sidebar verification during Agent Run UI testing

## Reproduction and cause

The preceding capacity UI check recorded large development log entries from the project sidebar.
This turn reproduced them through the actual Plane sign-in and work-item page with the restored isolated browser database and current migrations.
The owned API used port 8000, and the owned web server used port 3000.
Four warnings produced a development log of 17,152,980 bytes before the repair.
Each warning included a DOM element with its React graph.

The [project list](../../../apps/web/core/components/workspace/sidebar/projects-list.tsx) registered auto-scroll on its own content `div`.
Both rendered registrations had visible overflow in both axes.
Each already had a containing `ScrollArea` viewport with vertical scroll overflow.
The [upstream registration implementation](https://github.com/atlassian/pragmatic-drag-and-drop/blob/main/packages/auto-scroll/src/over-element/make-api.ts) explains this warning and checks the registered element's CSS overflow.
The source and native DOM observations agree on the cause.

## Repair

The project list now uses the existing `scroll-area-viewport` marker to find its containing viewport.
Its scroll listener and auto-scroll registration share one effect and one combined cleanup.
The listener reads the actual viewport position and also applies the initial position.
No new dependency, wrapper, scroll container, or global listener was added.

Native DOM inspection also found a button inside the project's drag-handle button.
The [project item](../../../apps/web/core/components/workspace/sidebar/projects-list-item.tsx) now uses the existing shared `DragHandle` directly with the same transparent styling and forwarded button ref.
The [shared component](../../../packages/ui/src/drag-handle.tsx) accepts an optional standard accessible name.
The consumer supplies the existing translated drag-to-rearrange label.
Native inspection confirms one named button without a nested button at this handle.
The touched project list's promise-return and placeholder-key lint warnings were also repaired.

## Runtime and test evidence

Twenty additional project memberships were created only in the isolated fixture database to make the sidebar overflow.
After reload, both registered elements were the existing viewport and had scroll overflow.
No non-scrollable registration warning or duplicate registration warning appeared after the repair.
A new page load generated 8,429 log bytes at the first check instead of another large React graph dump.
The remaining browser-externalized Node module warnings are still visible; this is not a claim that all development warnings are fixed.

Native mouse-wheel input moved the visible viewport from zero to 139 pixels and displayed the project's scroll border.
The hidden viewport stayed at zero and had no border.
The [scrolled sidebar screenshot](./sidebar-ui/scrolled-projects.png) records this state.
Automated drag attempts did not emit a native `dragstart` event in this browser session.
They do not prove drag auto-scroll or reordering, and those checks remain required.

The shared UI package build passed before the rendering test and browser accessible-name check.
Web type generation and TypeScript passed after the updated package build.
The [new native rendering check](../../../apps/web/tests/sidebar-drag-handle.test.mjs) verifies the shared button's accessible name, text escaping, transparent style override, and disabled placeholder.
All ten web checks passed in 1.159 seconds.
Focused lint and formatting passed without warnings or errors for the touched production files.
The new test's lint and formatting passed without warnings or errors.
Shared UI TypeScript and the production web build also passed.

## Review and remaining work

**Summary:** Correct the project sidebar's actual scroll target and remove a nested drag-handle button found during Agent Run UI checks.
**Critical issues:** The reproduced invalid registration and large diagnostic output are fixed at their source.
**Major issues:** Native drag auto-scroll and reordering, remaining browser module warnings, complete Agent Run scenes, and all four Harnesses remain unverified.
**Minor issues:** The new accessible-name property is optional and preserves existing consumers.
**Positive feedback:** The repair reuses the owning viewport, the existing cleanup helper, and the shared handle component.
**Questions:** The pending AD-7 runtime decision remains unchanged.
**Verdict:** Comment; the complete implementation goal remains in progress.

## Cleanup

The owned API exited after SIGINT, and the owned web server exited after SIGTERM.
The isolated browser session was closed.
The test containers, temporary database, volumes, and network were removed.
No owned listener remained on ports 3000 or 8000.
The private temporary Compose override and log cursor were removed.
Local report link and diff checks passed.
