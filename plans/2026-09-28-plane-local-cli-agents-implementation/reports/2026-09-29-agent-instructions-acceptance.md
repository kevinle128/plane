# Agent instruction acceptance

## Scope and environment

Story 2.4 is complete after the edit-during-save case was reproduced and repaired.
Check the production Agent settings page in Chromium with the actual web app and Django API on an isolated restored fixture database.
Sign in through the production email and password form with the isolated fixture member.
No connected Harness, model discovery, or GitHub authorization is claimed from this settings fixture.
The instruction setting remains available while the fixture Harness is disconnected.

## Browser and database evidence

Open the Claude configuration page and edit the labeled Instructions textarea.
Save a multiline instruction with a Unicode example by focusing Save changes and pressing Enter.
Change the guidance again and save it with the same keyboard action.
Reload the entire page and verify the exact new text in the textarea, with no error alert.
Verify the exact same instruction string in the actual Agent database row.
Compare the stored instructions, context, and all events of the two existing Agent Runs before and after the change.
The complete data hashes match, and neither Run history is changed.

At 375 px, page width equals viewport width.
The textarea remains readable and is about 280 px wide.
Keyboard focus reaches Save changes and scrolls it into view.
The [refreshed page](./instructions-ui/refreshed-375.png) and [focused Save control](./instructions-ui/save-control-375.png) were inspected.

## New Run and prompt evidence

The new API regression check creates a Run through the production Agent mention endpoint.
It saves new instructions through the administrator settings endpoint and reads them back.
A second production mention creates a new Run with the new instruction snapshot.
The earlier Run retains its instruction snapshot, context, and complete event rows.
An invalid instruction beyond 20000 characters is rejected without changing the saved value.
Instruction-like text in the member comment remains in trigger task data and is absent from the Run's saved Agent instructions.

The Worker prompt check covers both Q&A and Code policy construction.
Saved Agent instructions are present under the Workspace Agent instructions heading.
Issue title, issue description containing a false system marker, prior comment text, and the current request remain task data and are absent from system policy.
The Worker builds policy from the claimed Run's instruction snapshot, while the Harness receives issue and comment JSON through its task input.

## Checks

All 14 Run creation API checks pass in 4.60 seconds.
All six Claude driver and prompt checks pass in 0.001 seconds.
Focused Ruff checks pass for both changed test files.
The initial normal-flow checks passed before the pending-Save repair below.

## Delayed Save repair

Hold the real Django PATCH response after the setting is stored, using a bounded private WSGI fixture wrapper.
Enter a second instruction in the actual browser before releasing that response.
Before the repair, the second text is accepted by the textarea, then replaced with the earlier submitted text when the response arrives.
This reproduces the reported data loss through the production UI and API.

Replace the existing configuration wrapper with a native disabled fieldset driven by the existing `busy` state.
The same group covers Name, Handle, Instructions, and the connected Model selector.
No state counter, request abstraction, dependency, or per-field synchronization is added.
The `min-w-0` class preserves the existing narrow layout.

With a held response after the repair, Name, Handle, and Instructions all match the browser's `:disabled` state.
After release, all three are editable and the submitted multiline Unicode text is retained.
A later deliberate edit is accepted after Save completes.
A second held request uses an invalid handle and receives an actual API validation error.
The draft instruction text remains intact, an error is shown, and editing resumes.
Correcting the handle and saving succeeds, and a full reload retains the new instruction.
The [repaired 375 px page](./instructions-ui/guarded-save-375.png) was inspected and has no horizontal overflow.

Web type checking, focused OxLint, and focused Oxfmt checks pass.
All nine existing Run UI and pull-request checks pass.

## Story 2.4 completion audit

| Acceptance criterion | Direct evidence |
| --- | --- |
| Saved instructions remain after refresh and future Runs receive them as configuration | Actual keyboard Save, complete browser reload, database equality, and second production mention with the updated snapshot |
| Member instruction-like content is separated from saved system instructions | Run context assertions and Q&A/Code prompt checks with an injected description marker, plus the Worker policy/task input split |
| Existing events remain unchanged and new Runs receive new instructions | Actual database hashes for two historical Runs and an API old/new Run snapshot and event comparison |

## Review and cleanup

**Summary:** Normal Save, refresh, future Run snapshots, and historical event preservation have direct evidence.
**Critical issues:** None found in the API instruction snapshot or policy separation.
**Major issues:** The shared edit-during-Save data loss case was reproduced and repaired with a native fieldset.
**Minor issues:** Initial Run and repository setup are isolated fixtures.
**Positive feedback:** The normal setting and Run paths reuse the existing API and snapshot contracts.
**Questions:** None needed for this repair.
**Verdict:** Mark Story 2.4 done and keep the complete goal active.

The separate code re-review found no remaining concrete defect.
Success and error paths both restore editing, and validation errors preserve the draft.
The owned web and API processes are stopped and the owned browser is closed.
The isolated Compose stack, private response-delay wrapper, and temporary override are removed.
Keep the complete goal active.
