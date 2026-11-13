# Agent Mentionable acceptance

## Scope and environment

This report completes Story 2.5 against its three accepted criteria.
The browser uses the production web app and actual API with the isolated archived AGENT-1 fixture.
Sign-in uses the email and password UI.
The browser Agent is disconnected; no CLI health or connection proof is claimed from this fixture.
The existing fixture Run remains in progress and has retained audit records.
The API tests use an explicit connected test Agent to check availability independently of Harness conformance.

## Browser evidence

Run `node apps/web/tests/agent-mentionable.e2e.mjs <signed-in-isolated-session> <isolated-db-container>`.
The test requires an isolated database container and validates its name before reading it.
The Mentionable switch uses native keyboard focus and Space.
Disabling mentions persists through the actual settings API and a full reload.
The work-item editor's actual @Claude picker shows a disabled native choice and New mentions are disabled.
Pressing Enter does not insert an Agent mention.
The existing stable Run panel still opens and shows In progress.

Re-enabling mentions persists through the same API and full reload.
The disconnected Agent's picker choice remains disabled and now says Not connected.
Its existing Run still opens.
The test compares a digest of every Run, event, turn, and comment row before and after these actions.
The digest remains unchanged.
The test restores the initial Mentionable value and clears the unsaved comment text.
No browser API response is replaced.

## API evidence

The parameterized disabled-Agent check starts with a real saved mention through the production comment endpoint.
It retains the resulting Run, events, turns, and saved comment, then sets the isolated fixture Run to in-progress for the settings test.
This is an explicit test state, not a claim of live Worker execution.
The test disables mentions through the administrator settings endpoint or disconnects through the production disconnect endpoint.
The picker reports the exact disabled reason and available=false.
A new saved mention returns 400 and creates neither a comment nor a Run.
The authorized existing Run detail still returns 200 and in-progress.
The complete Run row, events, turns, and original saved comment remain equal to the original values.
Re-enabling a connected test Agent makes its picker choice available again.

Both focused parameter cases pass in 1.75 seconds.
All 20 Run creation and Harness settings API checks pass in 5.49 seconds.
The expected Server Error output comes from the existing rollback and post-commit-failure checks, which pass their assertions.
The new browser check passes scoped lint, formatting, and syntax validation.
No production implementation change is needed for this story.

## Completion audit

| Criterion | Direct evidence |
| --- | --- |
| Saved switch and picker state after refresh | Native browser Space toggle, actual database persistence, reload, and both actual picker reasons |
| Disabled or disconnected Agent cannot start a new Run | Disabled native picker selection plus production API rejection with unchanged comment and Run counts for both states |
| Existing active Run and audit remain available | Both stable browser panel opens, full historical row digest equality, and authorized API detail and exact row equality |

The separate read-only review confirms all three criteria and finds no concern.
Story 2.1 and the remaining Harness driver stories own live CLI conformance.
The sprint generator records Story 2.5 as done without changing the other unfinished stories.
Ten of 43 stories are now done, and the complete goal remains active.

## Cleanup

The owned mention-ui browser and web listener are stopped.
The owned API container, isolated Compose services, and network are removed.
No owned listener remains on ports 3000 or 8009.
The temporary override is removed, and the archived fixture dump is retained.
