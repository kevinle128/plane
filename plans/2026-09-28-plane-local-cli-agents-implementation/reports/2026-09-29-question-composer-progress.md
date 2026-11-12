# Question composer progress

## Behavior

The production Run panel binds quick choices and free text to the current question ID.
The submission key also binds the answer body and question ID.
Selecting a choice preserves an unsent free-text draft.
Queued, dispatching, and interrupted answers disable further answers until Plane permits them.
The panel shows a pending question even when its event is outside the loaded history page.
Historical questions retain their content without active choices.
Question answers do not grant protected permissions.

Review identified an incorrect Retry pickup instruction while the current Run lease was still active.
The card now says that answer delivery was interrupted and waits for Run recovery.
The Queue also reports pending answer delivery instead of suggesting delivery after the current step.

## Evidence

The [browser check](../../../apps/web/tests/agent-question-answer.e2e.mjs) uses a declared isolated Run fixture and the actual production browser and Django API.
It verifies keyboard choice selection, retained draft, question-bound Unicode free text, and reload in queued, dispatching, and interrupted states.
The check verifies that reservation does not mark an answer accepted and that acceptance creates the answered event.
It also verifies retained history, disabled controls, no unavailable Retry pickup button, 375 px layout, and no browser errors.
The check passes with its log at `/tmp/plane-question-answer-browser.log` and capture at `/tmp/plane-question-answer-375.png`.
The final interrupted test question remains pending in its declared fixture.
This check does not claim native Harness restart recovery.

Web type checks pass after removal of an unsupported MarkdownRenderer property.
Targeted OxLint and formatting checks pass.
The owned web server on port 3000, isolated API on port 8009, and test browser remain available for further acceptance work.
The current API container is `plane-timeline-ui-api-tests-run-b7e6a3677a8a` and has migration 0144 applied to its browser database.

## Remaining work

Verify the complete polling Worker, native Harness, and Django HTTP question flow.
Verify restart before and after native answer delivery and Stop while the question waits.
Complete the other three Harness question mappings and acceptance checks.
Story 2.8 remains in progress, 15 of 43 stories remain done, and the full goal remains active.
