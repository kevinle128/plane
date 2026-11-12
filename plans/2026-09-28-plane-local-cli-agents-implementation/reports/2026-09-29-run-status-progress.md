# Run status and header progress

## Reproduction and repair

The production Code panel displayed its Worktree path but did not name its sandbox mode.
The [browser check](../../../apps/web/tests/agent-run-status.e2e.mjs) reproduced this missing header field through the real web and API.
The red log is `/tmp/plane-run-status-red.log`.

The header now states `worktree · OS sandbox · Docker effects` for Code.
This matches the current Host Harness boundary and protected Docker effect execution described in the [boundary guide](../../../docs/local-cli-agent-docker.md#container-contract).
The status badge has a native `status` role, separate from the elapsed timer, so status changes can be announced without a timer announcement each second.
Waiting for pickup now uses an hourglass, as required by the handoff, while Stale retains its clock.

## Verification

The browser check creates declared presentation fixtures in the isolated `plane` database.
It does not claim native execution of those fixtures.
It checks all eight handoff states in Light and Dark with their labels and hidden decorative icons.
It verifies Agent, work-item identifier, Run kind, start time, active path, sandbox mode, elapsed display, and activity count in the header.
The accessibility tree exposes the current status.
Keyboard Enter opens each panel; Escape closes it and restores focus to the exact card trigger.
The card contains the status and excludes panel sandbox metadata.
The 375 px capture `/tmp/plane-run-status-375.png` was inspected and has no document overflow.
The green log is `/tmp/plane-run-status-green.log`.
No page errors were recorded.

Web type checking, targeted OxLint, and formatting pass.
The type log is `/tmp/plane-run-status-types.log`; existing tool configuration warnings remain visible.

## Environment and remaining work

The API restart initially exposed a stale instance response in the isolated test cache.
The owned test cache was cleared and the browser signed in again with the declared fixture account.
The original database, Run histories, web process, and browser were retained.
The active API container is `plane-timeline-ui-api-tests-run-7abe3e6b4443`, with harness 60522 on port 8009.
No new background process was required.

Complete the remaining permission and PR timeline scenes, result presentation, and full panel accessibility audit before completing Story 2.8.
The full 43-story goal stays active and sprint status remains unchanged.
