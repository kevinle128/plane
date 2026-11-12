# Capacity waiting UI and durable Stop

## Scope and environment

Verify the production Run Activity card and panel against the actual Plane API.
The accepted AD-11 waiting contract governs the older capacity-refusal prototype scene.
This check used the restored isolated browser database, current migrations through 0142, Django on localhost port 8000, and the web development server on port 3000.
The new waiting Run was a controlled database fixture with retained repository and Worktree metadata.
No native Harness or Docker Code job ran in this browser check.
No Harness connection was changed or reported as verified.

## Observed behavior

The real Plane sign-in flow authenticated the fixture member.
Activity showed `Waiting for a Docker slot` and opened the same Run panel.
At 375 pixels, the document and panel were both 375 pixels wide without horizontal page overflow.
At a 960-pixel viewport, the panel was 540 pixels wide and the document stayed within the viewport.
The retained Worktree path wrapped within the panel.
The waiting state kept the composer and Stop available.
Submitting a follow-up stored the message through the real API, cleared the composer, recorded its actor in the timeline, and showed one waiting queue message.
Send now remained disabled during capacity waiting.
Cancel in the Stop confirmation left the Run unchanged.
Confirming Stop stored the pending command, cancelled the queued message, and disabled further actions in the current panel.
The panel did not claim that the Worker had completed Stop.

## Reproduced defect and repair

Reloading the page and reopening the panel enabled the composer and Stop again while the stored Stop command remained pending.
The UI had kept this state only in local React state.
The [before screenshot](./capacity-ui/pending-stop-before-fix.png) records the reopened panel.
The focused database regression also failed because the member response did not include the pending state.
It failed with `KeyError: stop_pending` in 2.23 seconds.

The shared member Run queryset now annotates `stop_pending` with a correlated `Exists` check for a stored pending Stop command.
Run list and detail return this value from the same query.
It adds no per-Run database query and needs no schema migration.
The panel combines the confirmed API state with its immediate local request state.
It uses that result to disable messages, permission decisions, queue actions, and duplicate Stop and to retain the settlement notice.
The notice clears when the Run settles instead of retaining an old local Stop notice.

The repaired browser reload retained the notice and disabled composer and Stop.
The queue was empty after the stored cancellation.
The [after-refresh screenshot](./capacity-ui/pending-stop-after-refresh.png) and [375-pixel screenshot](./capacity-ui/pending-stop-375.png) record the repair.
The earlier [375-pixel waiting view](./capacity-ui/waiting-375.png) and [960-pixel waiting view](./capacity-ui/waiting-960.png) record the active waiting controls.

## Verification

The capacity, Worker lease, and Run creation gates passed all 44 checks in 16.08 seconds.
The changed capacity case checks pending state in detail and list before Worker acknowledgement and cleared state after acknowledgement.
Existing bounded Run-list query-count checks passed.
All nine web helper and production PR rendering checks passed.
Web type generation and TypeScript passed.
Focused web lint and formatting passed without warnings or errors.
Touched Python Ruff lint and formatting passed.
The development server still reported its existing Vite path-plugin and package module-type advisories.
It also recorded browser-externalized Node module warnings and large sidebar diagnostic records.
Those records need source inspection before further full-page verification; this report does not claim a clean development log.
Initial cold dependency optimization produced outdated-dependency responses; reloading after optimization loaded the application.
The computer-use native pipe was unavailable, and the installed browser CLI lacked its newer skill-content command.
Its installed help and an existing Chromium executable supplied the browser controls without installing or changing browser packages.

## Review and remaining work

**Summary:** Preserve the real pending Stop state when a member reopens a waiting Run.
**Critical issues:** The observed refresh failure is fixed in the shared Run read contract and production panel.
**Major issues:** Dark-theme coverage, visible waiting-to-running transition, sustained API-to-Worker Docker load, deployed Mini resource sizing, and all four Harnesses remain required.
**Minor issues:** This browser fixture proves member controls and persistence, not native Worker settlement.
**Positive feedback:** The API uses one correlated check in the existing tenant-scoped query, and database gates also prove Worker acknowledgement.
**Questions:** The AD-7 runtime exception is still pending and was not enabled by this work.
**Verdict:** Comment; Stories 3.6 and 3.7 and the complete goal remain in progress.

## Cleanup

The owned API process exited after SIGINT, and the owned web process exited after SIGTERM.
The isolated browser session was closed.
The test services, temporary volumes, and network were removed after the API container exited.
No listener remained on ports 3000 or 8000, and no container from `plane-capacity-ui` remained.
The private temporary Compose override was removed.
Report links and diff checks passed.
