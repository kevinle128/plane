# Send now native progress

## Scope

Verify the Claude fallback path for Story 2.15 with the actual polling Worker, native CLI, OS boundary, PostgreSQL and member/Worker HTTP endpoints.
The local repository and registered service/member credentials are fixtures.
No other Harness, browser flow, timeout recovery or complete Story 2.15 acceptance is claimed.

## Reproduced defect

The native check submits two messages while the first Harness is running and selects the second message with Send now.
Plane correctly advances to turn 2 after the old process settles.
The Worker dispatches the selected message, but its Send now command remains pending until native output is acknowledged.
The shared control helper handles that command again, stops the new Harness, and attempts another interruption receipt with the new lease.
The actual endpoint returns 409 and the Run remains active with a dispatching message.
The check times out at its native acknowledgment boundary after 151.861 seconds.

Skip only a Send now command whose selected message matches the message currently being delivered.
Keep that command pending until Plane accepts the native acknowledgment.
Stop and Send now for other queued messages still pass through the existing cancellation path.
Use the existing shared helper for Q&A, Code capacity waiting, and active Harness execution.

## Direct evidence

The native check passes in 30.430 seconds and the paired API check passes in 30.38 seconds.
A fixture holds the first actual Harness progress HTTP request so a member can submit two queued messages and select the second.
Same-key Send now replay returns the same command; a different duplicate request returns 409.
Both messages stay queued, and the selected message reports Send now pending before the Worker resumes.

The temporary Worker bootstrap observes the real stop function without replacing its behavior.
It records that the original native process group is alive immediately before the stop call and absent after it returns.
The acceptance boundary then confirms that the old group is absent before delivery is acknowledged.
The selected message is dispatching with no accepted timestamp or accepted event while its actual acknowledgment request is held.
Release acknowledgment and let the actual native CLI complete the selected message in turn 2.
The remaining queued message completes in turn 3.
Both answers contain their distinct markers.

The API verifies no result for interrupted turn 1, exact accepted turn numbers, one dispatch and one acceptance for each message, and interruption before dispatch before acceptance.
The final queue is empty, the Run ID and clone path stay the same, and repository contents remain unchanged.
Fixture holds are released during failure cleanup before stopping the owned Worker.

Initial setup attempts omitted the Worker import path and used an image tag rather than the required immutable image ID.
Correct both settings before taking the native result as evidence.
A test assertion initially requested a turn number absent from the member response; use the message turn and conclusion number supplied by the actual contract.
These setup and assertion corrections do not weaken product behavior.

## Regression checks

Four Worker control checks pass in 1.024 seconds.
Three Code turn checks pass in 0.595 seconds.
The complete lease contract file passes 22 checks in 7.21 seconds.
Focused Ruff lint and formatting pass for the Worker helper and both paired test files.
Updated documentation links resolve.

## Review and remaining work

Read-only review verifies that the guard skips only the current message, and that Plane atomically acknowledges its Send now command on acceptance.
The direct stop observation resolves the initial review concern about natural process exit during the held HTTP request.
Keep Story 2.15 in progress for actionable cancellation timeout without a competing CWD, production queue/timeline pending controls, and the required other Harness conformance.

## Cleanup

The owned Worker and API test processes exit.
Remove the Compose stack, private fixture directory, token/session files and temporary override.
Leave no owned listener on ports 8009 or 8769.
