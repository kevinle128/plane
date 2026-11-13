# Send now timeout progress

## Scope

Extend the [native Send now evidence](./2026-09-29-send-now-native-progress.md) with the unverified-process error contract in Story 2.15.
Use the actual polling Worker, Claude process, OS boundary, Plane HTTP endpoints and isolated PostgreSQL.
Declare a fault at the Worker stop boundary that reports failure to confirm process termination.
This does not claim that the OS has a physically unkillable process or that all Harnesses pass.

## Reproduction

The native fault check fails in 71.179 seconds with `failed != in_progress`.
The Worker attempts to stop the native process, fails to confirm termination, and retains its process record.
Its generic exception handler still posts an ordinary terminal Failed result.
That result has no recovery control and does not describe the unresolved process.

## Repair

Before the Worker posts a terminal fallback failure, inspect its existing Harness and Git process registries.
If either record remains, keep the current Run, lease, queued messages and command.
Treat unreadable or invalid records as unresolved.
Publish an idempotent, lease-fenced `error` event with code `process_reconciliation_required`.
Tell the operator to inspect and stop the remaining Run process, then use Retry pickup when the Run becomes Stale.
Do not clear a record or report a terminal result without process verification.
Failures with no retained process record keep the ordinary terminal failure path.

The existing lease task changes the Run to Stale and cancels expired-generation commands while retaining queued messages.
Retry requires process reconciliation before another claim.
A member can select Send now again for a retained queued message after successful pickup.
No new authority or runtime write exception is added.

## Native evidence

After repair, the native fault check passes in 9.341 seconds and the paired API check passes in 9.05 seconds.
The recorded original native process is alive when the injected stop boundary reports its failure.
Plane remains In progress on turn 1 with no conclusion.
Both messages stay queued, the Send now command stays pending, and the original process record remains.
The API verifies exactly one claim, no later dispatch or acceptance, no turn result, and a visible actionable error event.
No competing turn is started in the clone.
Cleanup uses the unmodified registry stop path; after the Worker exits, the real process registry reconciles and stops its recorded process.

The normal native Send now regression passes in 28.291 seconds and the paired API check passes in 27.92 seconds after this shared exception-handler change.
It still verifies actual cancellation, selected message acknowledgment and ordered selected-then-FIFO native completion.

## Other checks and review

Five Worker control checks pass in 1.235 seconds.
The new controlled-client check covers retained Harness records, retained Git records, invalid records and the ordinary no-record terminal failure path.
Its initial setup omitted the Run root; create that private directory and correct the loop binding lint errors before rerunning.
Three Code turn checks pass in 0.502 seconds.
Focused Ruff lint and formatting pass for the changed Worker and test files.
Read-only review finds no concrete defect in retained records, idempotent error events, lease fencing or cleanup.

## Remaining work

Keep Story 2.15 in progress for production browser queue/timeline pending and error controls and the other required Harness conformance.
The timeout contract is verified with a declared native stop fault, not with every CLI or deployed Mini process failure.

## Cleanup

All owned test processes exit.
Remove the Compose stack, private fixture directory and temporary override.
Leave no owned listener on ports 8009 or 8769 and no credentials in the checkout.
