# Run panel resize and state polling

## Scope and environment

Verify Story 2.9 against both acceptance criteria in the approved epics.
Also verify the visible capacity transition required by Story 3.6.
Use the production Plane sign-in, work-item page, Run panel, and member API with an isolated restored test database.
The owned Compose project is `plane-resize-ui`, with API port 8000 and web port 3000.
The database has current migrations through 0142.
Two fixture members use the same browser session and local storage.
No Harness connection or Docker Code launch occurs in this UI check.
Capacity state changes are controlled database fixtures, not Worker observations.
The approved handoff governs Plane typography, tokens, spacing, and the 7-pixel resize boundary.

## Resize acceptance evidence

The first member opens the panel at the default 540 pixels.
ArrowLeft changes the width to 560 pixels and stores it under that member's ID.
A real mouse drag changes the width to 680 pixels.
Reloading the work-item page and reopening the panel restores 680 pixels.
Dragging beyond either limit clamps the width to 960 or 380 pixels.
The accessible separator reports the chosen width and the 380–960 range.
At a 375-pixel viewport, the panel and document are both 375 pixels wide without horizontal overflow.
Escape closes the panel and restores focus to the Open run button.
The first member then saves 440 pixels with the keyboard.
After signing out and signing in as the second member in the same browser, the panel opens at 540 pixels.
The second member saves 560 pixels and retains it after reload.
The first member's stored value remains 440 pixels under its separate member key.
At 960 pixels, the close control and composer remain within the viewport.
Closing and reopening the panel also restores 960 pixels.

These observations meet both Story 2.9 acceptance criteria.
The [narrow dark panel](./panel-resize-ui/dark-375.png), [keyboard focus](./panel-resize-ui/dark-keyboard-focus.png), and [960-pixel dark panel](./panel-resize-ui/dark-960.png) record the rendered views.

## State polling defect and repair

Changing the fixture Run state through the real database did not update the open panel.
The API returned the new state while the panel continued to show the previous state.
The elapsed clock updates React state each second.
The inline refresh-interval function changed identity on each render and reset SWR's three-second polling timer.
Timeline and queue polling continued, but Run detail polling did not run regularly.
The first repair used a stable module-level refresh-interval function.
The later [plan check](./2026-09-29-plan-reporting-progress.md) found that this still stopped polling on an empty cache after a fresh page load.
The final function is a stable callback that also uses the initial Run when the cache has no data.
Its existing active-state and conclusion-mirror policy remains the same.
The other dynamic polling callers were inspected; they do not contain this panel's elapsed clock.

The new opt-in browser regression uses the open production panel and an isolated test database.
It confirms that the elapsed clock changes, then changes the fixture between waiting capacity and in progress.
It requires both changes to reach the same mounted panel without reload.
It restores the original fixture status after the check.
The original implementation fails after 12 seconds with the same panel still mounted and its status unchanged.
The first repaired implementation passed the warm-cache check in 2.79 seconds, including the live-clock check.
The expanded regression now reloads the page before it opens the exact Run panel and tests both state transitions with an empty initial cache.
The final fresh-page regression passes in 9.25 seconds.

Select Dark through Plane Preferences before the capacity check.
The [waiting panel](./panel-resize-ui/dark-waiting-375.png) and [running panel after the transition](./panel-resize-ui/dark-running-after-wait-375.png) show both states at 375 pixels.
Waiting keeps the composer and Stop available and disables Send now.
The panel updates its badge and controls when the API reports in progress.
This proves the UI transition; sustained Worker-to-Docker capacity delivery remains required for Story 3.6.

## Runnable regression and gates

Open the fixture Run panel in a named `agent-browser` session before this opt-in command.
Use only an isolated test database; the check rejects container names outside the `plane-*-test-db-1` pattern.
Pass the browser session, test database container, and open Run ID as arguments.

```sh
node apps/web/tests/agent-run-panel-polling.test.mjs plane-resize-ui plane-resize-ui-test-db-1 221ce611-32e9-4a29-a5c0-f5fa6f1af09f
```

Without these arguments, the browser check reports an explicit skip.
All nine existing Run helper and production PR rendering checks pass.
Web type generation and TypeScript pass.
Focused OxLint passes with zero warnings and errors.
Focused Oxfmt passes.
The existing Vite path-plugin, package module-type, and browser-externalized Node module warnings remain recorded in the development logs.

## Review

**Summary:** Story 2.9 has direct browser evidence for both acceptance criteria, and open-panel polling now follows API state while the clock ticks.
**Critical issues:** None found in the changed polling policy.
**Major issues:** Full Worker capacity delivery and the remaining design scenes need their own acceptance evidence.
**Minor issues:** The browser regression needs an authenticated fixture panel and the installed browser CLI.
**Positive feedback:** The repair retains the existing polling policy and changes only callback identity.
**Questions:** The pending Harness runtime and DNS decisions are separate from this UI work.
**Verdict:** Story 2.9 can be marked done; Story 3.6 remains in progress.

## Cleanup

The owned API and web processes exited after SIGINT.
The named browser session was closed.
The isolated Compose containers, volumes, and network were removed.
No listener remains on ports 3000 or 8000, and no container remains under the owned Compose project.
The temporary Compose override was removed.
The screenshots and test report remain as acceptance evidence.
