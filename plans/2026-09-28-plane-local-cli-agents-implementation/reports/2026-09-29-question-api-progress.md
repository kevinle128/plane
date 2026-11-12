# Durable question API progress

## Scope

This work adds the durable Plane question and answer contract for Story 2.8 and the shared Harness flows.
It does not complete native question delivery or the question-bound composer.
The full goal remains active, with 15 stories done and 28 stories in progress.

## Durable state and access

The [question model](../../../apps/api/plane/db/models/agent.py) binds an operation, turn, immutable question event, and optional answer message to a Run.
PostgreSQL enforces one pending question per Run and one question per operation within that Run.
Django generated [migration 0144](../../../apps/api/plane/db/migrations/0144_agent_run_questions.py).
The migration was applied in the isolated test database.
The migration check reports no model changes.
The live browser database and its API process have not yet been updated for this contract.

The [question endpoint](../../../apps/api/plane/app/views/agent_run_question.py) checks the current Worker token, lease, requester access, turn, bounded content, and pending control state.
An identical operation returns the saved receipt, and changed content under that operation is rejected.
Question publication updates the Run's progress time and status.
The member Run response and Worker claim return the same indexed pending-question summary.
The existing Run list gate still passes with four queries.
The endpoint checks current answering-member access before it releases answer content.

## Answer and control behavior

The member message endpoint binds an answer through `question_id` and keeps its original identity in the immutable queue event.
Canceling an answer permits a replacement with a new client key.
Retrying the canceled answer's original key returns its original canceled message.
Question delivery reserves the answer without marking it accepted.
Only the existing message acceptance endpoint marks the question answered and resumes the Run.
New permission requests and grant consumption are blocked while a question is pending.
Grant status remains readable under its existing authority and Code slot checks.
Pending Stop blocks answer delivery and acceptance.
Stop acknowledgement cancels the pending question and retains its history.

Lease expiry interrupts unconfirmed answer delivery.
Reconciled recovery preserves the question, answer, and turn under the new lease.
The old lease cannot acknowledge that delivery.
Read-only review found that a second explicit interruption after recovery reused the first interruption's event key.
An API regression reproduced the resulting rejection and rolled-back state change.
The shared interruption key now includes the lease generation, and repeated requests within one generation remain idempotent.

Two further API regressions reproduced conflicting queue transitions.
Ordinary FIFO dispatch could reserve another task while a question was pending.
Question publication could also start while Send now was pending.
Both operations now check the conflicting state under the Run lock.
FIFO leaves later tasks queued until the question is answered.

## Verification

The [question contract checks](../../../apps/api/plane/tests/contract/app/test_agent_run_question.py) cover bounds, Unicode, duplicate operations, concurrent publication, exact answer binding, deferred acceptance, cancellation, Stop, lease recovery, repeated interruption, member revocation, FIFO, and Send now.
The [permission checks](../../../apps/api/plane/tests/contract/app/test_agent_run_permission.py) include pending-question request and consumption fencing.
The initial broader permission run exposed five status regressions from a misplaced Boolean condition.
The status condition was restored, and the pending-question guard was placed on consumption.
The final combined question, Worker lease, Run creation, permission, and Worktree suite passed all 144 tests in 46.73 seconds with migrations enabled.
Its log is `/tmp/plane-question-final-regression.log`.
Ruff reports no findings, and all 12 affected Python files pass the formatting check.
Read-only review found no remaining concrete defect in the repaired interruption, permission, and queue guards.
The [operating contract](../../../docs/local-cli-agent-docker.md#durable-run-question-api) now describes the delivered API behavior and its integration limits.

## Remaining work

Add the shared bounded MCP question tool and its Plane client methods.
Map confirmed native Harness tool delivery to message acceptance without early acknowledgement.
Preserve pending and answered question context during native recovery.
Bind the production composer and option buttons to the current question identity.
Verify native Worker delivery, browser reload, Stop, restart, and all four Harnesses.
Story 2.8 remains in progress, and sprint status has not been changed.
The owned web server, isolated API stack, and test browser remain in use for the next acceptance checks.
