# Stale failure acceptance

## Scope and test state

This report covers the three accepted criteria of Story 2.20.
The browser uses the production web app, actual Plane API, and an isolated restored AGENT-1 database.
Sign-in uses the email and password UI.
The test starts with an explicitly prepared current lease and a registered private Worker token.
A local source repository is committed and cloned with native Git into a private temporary Run directory outside the Plane checkout.
The repository grant records are declared test fixtures.
This test does not claim GitHub delivery, live Harness connection, or full CLI execution.

## Browser and native HTTP evidence

Run the durable check after preparing the signed-in isolated fixture:

```sh
node apps/web/tests/agent-stale-failure.e2e.mjs <session> <isolated-db-container> <isolated-api-container> <fixture-root>
```

The fixture root must be a temporary plane-stale-fixture directory with a private 0600 worker-token file and a Git clone in runs/221ce611-32e9-4a29-a5c0-f5fa6f1af09f.
The test validates isolated container names before database access.
The native production PlaneClient registers that real clone and submits a progress event under the current lease.
The isolated fixture then expires the lease and progress time by six minutes.
The actual stale detection task changes the Run to Stale.

The browser opens the actual Run card and sees the stale recovery controls.
Native keyboard Enter opens Mark failed confirmation.
Escape cancels without any persisted change.
An empty reason shows the accessible validation error and leaves all persisted state unchanged.
A confirmed Unicode reason persists Failed, the signed-in member identity, and a valid timestamp.
The prior event rows and clone path remain equal to their original values.

The native authenticated PlaneClient then sends an event and a successful result under the old lease.
Both actual HTTP requests return 409.
The complete Run row, all Run events, all turns, and all issue comments remain exactly equal to the saved failed state.
The real Git HEAD, clean worktree status, and README contents also remain equal.
After full browser reload, the Run panel still shows Failed and the exact member reason.
The [reload screenshot](./stale-failure-ui/failed-after-reload.png) records that retained timeline and conclusion.
The complete durable browser and native HTTP check passes.

## Reproduced accessibility repairs

The first browser inspection found that the shared confirmation dialog had no accessible name.
The shared AlertModalCore now registers its existing heading with Headless UI Dialog.Title.
Its positive button tab index is removed so native document order controls keyboard navigation.
The inspection also found that the independently portaled Run panel remained exposed while confirmation was open.
The Run panel now uses native inert while recovery or Stop confirmation is open.
The browser check proves the recovery dialog has a registered accessible label, the background panel is inert during confirmation, and Escape restores the panel.
The confirmation portal remains interactive outside the inert panel.

## API and quality evidence

The [API progress report](./2026-09-29-stale-failure-progress.md) records the focused and full lease checks.
Both outsiders and active project guests without comment permission receive 403.
The API checks require a reason, record the exact actor and finish timestamp, retain earlier events and clone path, and preserve a single conclusion on replay.
Late event and result rejection leave complete persisted rows unchanged.
All 18 lease checks pass in 5.27 seconds.
The UI package build and UI and web type checks pass.
Scoped lint and formatting checks pass for the browser check and both changed UI files.
The Python test file passes Ruff lint and formatting.

## Acceptance mapping

| Criterion | Direct evidence |
| --- | --- |
| Confirm failure with member, time, reason, retained timeline and clone | Actual keyboard browser confirmation, persisted event fields, API exact timestamp check, prior event equality, retained native Git HEAD and files, and reload |
| Reject old Worker update without changing conclusion | Native authenticated PlaneClient event and result both return 409; complete persisted state remains equal |
| Reject member without comment permission | Production endpoint checks for outsider and active restricted project guest both return 403 |

Full Harness execution, stale pickup recovery, and GitHub publication remain in their own unfinished stories.
The read-only review confirms all three criteria and finds no concrete lifecycle defect in the dialog repairs.
The focused API check passes again after review.
The sprint generator records Story 2.20 as done.
Eleven of 43 stories are done, and the complete goal remains active.

## Cleanup

The owned stale-ui browser and web process are stopped.
The owned API container, isolated Compose services, and network are removed.
No owned listener remains on ports 3000 or 8009.
The private Worker token, temporary Git fixture, preparation script, and Compose override are removed.
The archived database fixture is retained for later checks.
