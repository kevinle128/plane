# Follow-up browser acceptance

## Scope and environment

Complete the panel checks identified in the [native follow-up report](./2026-09-29-follow-up-http-progress.md).
Add `browser_follow_up` to the existing context fixture mode.
Use Chromium with the production web app on localhost port 3000, the actual Django fixture server on localhost port 8009, and the actual polling Worker and authenticated Claude.
Use the stored fixture member session in an owned browser.
The isolated instance and member onboarding records are fixtures; no login UI acceptance is claimed.
The initial Run, repository, local clone, updated issue/comments, and historical decision remain the explicit fixtures described in the native report.
No GitHub connection or other Harness execution is claimed.

## Browser-to-native flow

Claude completes Q&A turn 1 and its Harness process exits.
The fixture updates the work item and the native test pauses for a real browser reply.
Open `test-workspace/browse/WRK-1` and open the exact Run by its stable panel identity.
The completed panel shows `Reply to Claude…` and `Send reply`.
Fill the task from the private fixture file and select Send reply.
The panel stores it on the same Run and reports the pending pickup state.

The actual polling Worker claims the message and starts a new Claude process in the same clone.
Turn 2 reports the updated title, latest comment, earlier decision, and its own `FOLLOWUP_1` marker.
The existing native test then sends a second follow-up after that process exits.
Turn 3 contains the latest context, prior accepted message, prior conclusions, and `FOLLOWUP_2` marker.
The API inspects the actual contexts delivered to both native processes, including ordered comments and exclusion of the other same-issue Run's private history.
Both replies retain the original Run ID, Q&A kind, clone path, and unchanged source bytes.

## Reopen and refresh

The same open panel reaches completion through production polling.
Close it with Escape and reopen the exact same Run.
The timeline has three direct conclusion entries in order: original repository answer, first follow-up answer, then second follow-up answer.
Reload the complete page and reopen that Run again.
The same three conclusions remain in the same order.
There is exactly one opener for this Run card.
The other fixture Run has its own card and its private panel history does not appear in this panel.

The [browser check record](./follow-up-ui/browser-check.json) stores the actual DOM conclusion marker flags, one-card count, absence of the private sentinel, and equal page/viewport width at 375 px.
The check asserts those values before releasing the API fixture's browser gate.
The [reopened 375 px image](./follow-up-ui/reopened-375.png) was inspected.
The panel has no horizontal overflow and retains its Reply composer.

## Checks

The native side passes in 79.30 seconds, including its wait for the browser reply.
The API side passes in 160.03 seconds, including its final browser verification hold.
Focused Ruff lint and formatting pass for both changed fixture files.
The earlier decision-context checks retain their byte-limit, omissions, lease-fence, and privacy evidence.
No production UI code change is required for this acceptance flow.

## Story 2.13 completion audit

| Acceptance criterion | Direct evidence |
| --- | --- |
| Panel reply stays on the same Run and starts its next turn in the same clone | Actual browser Reply submission, polling Worker claim, native turn 2, and stored Run/clone identity checks |
| Changed issue/comments and prior same-Run messages/decisions reach the prompt without another Run's private history | Updated fixture records, actual delivered context responses, turn-2 and turn-3 native answers, and private sentinel exclusion |
| Harness exit preserves the conversation through durable reconstruction | Exit checks before both follow-ups and new actual Claude processes using the same Plane Run and clone |
| Reopened panel retains ordered turns and conclusions on one Run card | Actual close/reopen and full page reload, three ordered conclusion entries, and one matching Run-card opener |

All four criteria have direct evidence.
Other Harness conversation and recovery stories retain their own requirements.

## Review

**Summary:** A real panel reply reaches the native Worker and durable context survives both CLI exits and browser reload.
**Critical issues:** None found in the delivered follow-up flow.
**Major issues:** The remaining 38 stories and complete four-Harness goal require their own acceptance evidence.
**Minor issues:** Initial authorization and historical decision observations are fixtures.
**Positive feedback:** The browser uses the existing production composer, API, queue, Worker, and context path without a UI bypass.
**Questions:** AD-7 and DNS decisions remain pending and are not assumed.
**Verdict:** Mark Story 2.13 done and keep the complete goal active.

## Cleanup

The owned native and API processes exit successfully.
Close the browser and stop the owned web process.
Remove the isolated Compose containers and network, private fixture directory, and temporary override.
No owned listener remains on ports 3000, 8009, 8769, or 8811.
No member session or Worker token is stored in the report or checkout.
