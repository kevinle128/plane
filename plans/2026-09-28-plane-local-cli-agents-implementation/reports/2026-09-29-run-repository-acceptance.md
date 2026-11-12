# Run repository selection acceptance

## Boundaries and reproduction

Use the production web app and API, isolated PostgreSQL, actual polling Worker, native Git and authenticated Claude.
The [durable API fixture](../../../apps/api/plane/tests/fixtures/agent-run-repository-ui.py) controls only the external GitHub installation response and a bounded claim-response hold.
Its seed and server require the isolated `test-db` host.
Private generated Worker credentials and native clone data stay outside the checkout.
This proves the Run selection contract; it does not prove GitHub OAuth, organization installation or actual GitHub grant removal.
Those requirements remain in Epic 1.

The actual Git remote is `https://github.com/octocat/Hello-World.git`, with branch `master` and observed HEAD `7fd1a60b01f91b314f59955a4e4d4e80d8edf11d`.
The Worker creates this clone through its unchanged Git path; there is no clone transport replacement or Harness replacement.

The native revocation check exposed a defect before the repair.
The fixture held the actual claim response after grant validation, revoked the current Plane catalog generation, and then released the response to the Worker.
The Worker created the clone before its registration request discovered the revoked grant.
The native assertion failed because the clone directory existed.

## Repair

Reuse the clone endpoint with an optional exact Boolean `prepare_only` field.
A preparation check verifies the current lease, grant and path without registering the clone or changing the event sequence.
Reject a pending Stop before Git preparation.
If authority is revoked, keep the Run awaiting a repository, fence the old lease and preserve anchored context.
The Worker performs this check before preparing either its Q&A clone or Code repository.
It still checks authority again when registering the resulting clone before Harness launch.

A Stop that arrives during the preparation request is acknowledged without cloning or launching a Harness.
The preparation control check handles only Stop.
Review found that handling Send now before dispatch would repeat steering for a carried selection on its replacement lease.
Repair that regression and extend the actual sandboxed follow-up controller check to retain selected Send now until message acceptance and reject repeated steering.
The read-only re-review finds no remaining concern.

## Browser and native evidence

The [selection check](../../../apps/web/tests/agent-run-repository.e2e.mjs) uses 101 catalog entries.
An empty active catalog shows the repository wait, no usable candidates, a GitHub management link and a disabled confirmation.
The actual polling Worker creates no clone or lease in this state.
The first page has 100 candidates; keyboard Load more appends the last candidate without duplicates.
Keyboard selection uses the public repository with its displayed branch and visibility.
A declared revoked GitHub response rejects confirmation with an actionable error and exact unchanged Run state.
Repository wait survives a full reload.
Case-insensitive search finds the authorized candidate.

Successful confirmation records one choice event and the exact repository in both Run identity and anchored context.
The real Worker claims the Run, clones the selected remote and launches Claude.
Inspection of the recorded native PID with `lsof -a -p PID -d cwd -Fn` confirms its actual CWD equals the fresh Run clone outside Plane.
The clone origin matches the selected URL and its worktree stays clean.
Claude invokes `mcp__plane__plane_read_file` and returns the exact native README content, `Hello World!`.
The conclusion and active CWD remain visible after full reload.
The [completed capture](./repository-ui/completed-after-reload.png) records this state.

The [revocation check](../../../apps/web/tests/agent-repository-revocation.e2e.mjs) then prepares a new disposable test turn, holds its actual claim response and removes the active Plane catalog grant before preparation.
After the repair, the actual Worker returns to repository wait with no clone directory, no clone-ready event, no Harness record and unchanged anchored context.
The [375 px capture](./repository-ui/revoked-after-reload.png) shows the no-candidate explanation and management link after reload, with no horizontal overflow.
The test explicitly resets only its own disposable Run between scenarios; it does not claim that a production Run deletes prior history.

Both complete checks pass again from a fresh restored database using the durable fixture after review.

## Acceptance mapping

| Criterion | Evidence |
| --- | --- |
| An unbound mention asks for an authorized repository before clone or Harness launch | Actual mention creation contract; production empty-catalog panel with live polling Worker, unchanged lease generation and no clone |
| Selecting a candidate records its Run identity and creates a fresh remote clone before launch | Keyboard pagination/search/selection; one selection event; actual Git remote clone; native process and exact README conclusion |
| No candidate or revoked selection keeps repository wait with a resolution path and no write | Actual empty and rejected-confirmation browser states; native revocation after claim validation with absent clone/Harness and retained context |
| Harness CWD and context refer to the exact selected repository outside Plane | Native PID CWD inspection, exact origin, anchored context equality and README content from that clone |

## Checks and operation

The complete API lease/control and Run creation suites pass: 40 tests in 11.33 seconds.
They cover actual mention creation, selected repository access, current grant checks, preparation without registration, invalid flags, stale lease, pending Stop, and idempotent choice.
Worker control passes six checks, including Stop during preparation and carried Send now delivery.
Code turn checks pass three cases.
Focused Ruff, JavaScript lint and formatting pass.
No web production type contract changed in this repair.

Restore the archived disposable AGENT-1 database, apply migrations, and mount a private `plane-repository-fixture-*` directory as `/fixture` on the isolated API service.
Run `python plane/tests/fixtures/agent-run-repository-ui.py seed /fixture` once, then `python plane/tests/fixtures/agent-run-repository-ui.py serve /fixture` with local port 8009 published.
Set the standard Worker API, workspace, private token, Run root and deployment-root variables to this fixture and run the normal Worker.
Sign in to the isolated web app as its test member.
Run the selection browser check with session, database container and private host fixture path; then run the revocation check with database container and fixture path.
The revocation check releases the held response in its cleanup path.
The owned browser, Worker, web and API processes are stopped.
The isolated Compose stack and private credentials/clone data are removed after verification.

Story 2.11 meets its four criteria.
The overall 43-story goal remains active; live GitHub setup and the other Harness drivers remain required work in their owning stories.
