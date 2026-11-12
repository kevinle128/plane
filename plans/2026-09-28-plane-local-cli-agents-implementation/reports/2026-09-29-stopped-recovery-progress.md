# Stopped Run repository recovery progress

## Scope

Extend the [missing-clone repair](./2026-09-29-stopped-clone-resume-progress.md) with durable recoverable preparation failures and member Retry.
Keep Story 2.18 in progress until the production browser acceptance checks pass.
The paired checks use actual member and Worker HTTP endpoints, isolated PostgreSQL, the polling Worker, native Claude, repository MCP tools, and the Host boundary.
The local Git clone and repository binding are fixtures.
The stopped-clone mode changes only Git transport to a local bare remote.
No live GitHub access or other Harness execution is claimed.

## Reproduced failures

After native Stop and a missing-clone failure, restore the original clone and submit Retry pickup.
The actual member API returns 409 because the Run is Failed.
The native check fails in 17.704 seconds before this contract change.
An initial fixture attempt used an incorrect retry URL; correct that URL before taking this failure as evidence.

Review finds that a recoverable Retry enters Created, while blocked process reconciliation reports accept only Stale.
The actual endpoint check reproduces 409 and passes after accepting Created with its matching pending Retry generation.

A registered initial clone can fail verification after a stale pickup with no panel message.
Restoring the clone and requesting Retry then fails because turn 2 requires a queued message.
The paired native check reproduces this ordinary terminal failure in 8.426 seconds.

After the first repair, a later panel task can replace the original task being retried.
The paired native check queues `FUTURE_TASK` and incorrectly completes it in turn 2.
Its assertion fails with `2 != 3` in 10.965 seconds.
Fix task-source continuity before accepting the recovery contract.

## Delivered contract

Add `recoverable` to each durable turn with default false.
Generate migration 0143 with Django and apply its database constraint: only failed turns can be recoverable.
The Worker result endpoint accepts only a Boolean flag and requires a registered clone for a recoverable result.
Idempotent result receipts compare that flag as part of their stored content.
Ordinary failures remain terminal and cannot use Retry pickup.

The Worker marks retained repository preparation failures recoverable and gives an explicit repair instruction.
No replacement clone or Harness process starts when clone verification fails.
Member Retry retains history, clone paths, and pending task data and advances to a new turn on the same Run.
It requires comment permission and a reconciled process registry before a new lease.
A blocked reconciliation report stays durable and idempotent while Retry is pending.
Old-generation heartbeat and new result writes remain fenced.
An exact existing result receipt can be read again without another state change.

Claim receipts record the task source.
Initial claims use the original mention task.
Retry carries that source from the prior claim receipt rather than deriving it from queued or cancelled message rows.
Repeat claims and Q&A-to-Code handoff keep the same source.
The prior receipt uses the existing unique Run/source-key index and the fenced prior lease generation, so lookup does not scan transcript history.
The Worker leaves future messages queued while the original task is active.
A new ordinary turn after that task completes dispatches the next queued message.
Original-task prompt construction requires the explicit Plane marker and matching current Run and turn context.
It creates no artificial member message and grants no effect permission.

The panel shows the retained repository error and Retry pickup for a recoverable failed conclusion.
It keeps the ordinary failed banner and stale controls for their existing states.
Production browser verification of these changes remains required.

## Native acceptance evidence

The final stopped-clone check passes natively in 30.441 seconds and on the API side in 30.40 seconds.
It completes initial Q&A, starts a native follow-up Harness, submits Stop, and waits for terminal Stopped with no retained Harness process record.
A member reply with the original clone absent produces a recoverable failed turn without another clone or Harness launch.
Restore the moved original clone and submit member Retry.
A new native process completes turn 4 on the same Run and clone.
Clone device/inode, Git HEAD, and file contents stay unchanged.
The answer includes the current issue title, later comment, earlier answer, historical denied decision, and `STOPPED_RESUME` marker.
Plane records turns 1 completed, 2 interrupted without a result, 3 recoverable failed, and 4 completed.
The pending queue is empty and private history from another Run is excluded.

The original-task and later-queue check passes natively in 20.731 seconds and on the API side in 20.76 seconds.
The initial registered Worker lease is a fixture with no running Harness and no panel message.
Expire it through the production stale task and use actual member Retry while the clone is absent.
After the recoverable failure, restore the original clone, request Retry, and queue a later member task before pickup.
The actual polling Worker and Claude complete the original request in turn 2 with repository content in its answer.
Only then is the later message accepted and completed as `FUTURE_TASK` in turn 3.
No task is silently replaced and no fake panel message represents the original request.

## Other verification

Apply all real migrations through 0143 in the isolated test database.
An initial reuse of the older test schema fails with the missing new column; rebuild it with `--create-db --migrations`.
Fix the test-only outsider username collision and rerun the affected checks.
The lease and Code capacity regression passes 37 tests in 12.83 seconds after review.
It covers typed result validation, registered-clone requirements, default terminal failure, exact receipts, denied member access, duplicate Retry, blocked reconciliation, current context, stale retry with a later message, and original-source Code handoff.
It also verifies the database constraint rejects a completed turn with recoverable true.

Fifteen focused Worker foundation, control, and Code turn checks pass in 2.462 seconds after review.
Web type checking passes.
Focused web lint and formatting pass.
Ruff lint and formatting pass for the affected non-generated Python files.
The generated migration remains unmodified.
Three final panel/original/stale retry checks pass after the indexed receipt lookup and kind filter in 1.91 seconds.

## Review and remaining work

Read-only review finds no concrete defect after the blocked-report and task-source fixes.
The scoped contract is verified; Story 2.18 is not complete.
Complete production browser reply after Stop, recoverable error and Retry keyboard controls, and ordered history after panel reopen and full reload.
Other Harness execution and full Code recovery remain in their own stories.

## Cleanup

The owned native and API processes exit successfully.
Remove the Compose containers and network, private fixture directory, and temporary override.
No owned listener remains on ports 8009 or 8769.
No Worker token or member session is stored in the report or checkout.
