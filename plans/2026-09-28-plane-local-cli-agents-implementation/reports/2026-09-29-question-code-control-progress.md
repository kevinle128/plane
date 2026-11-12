# Code question control and recovery progress

## Native Stop

The [native HTTP check](../../../apps/agent-worker/tests/test_live_api.py) supports `question_code_control: "stop"` with `question_code: true`.
The actual polling Worker and Claude ask a question in the assigned Code Worktree.
Member Stop terminates the native process, cancels the pending question without an answer, and releases the reserved Code slot.
The Worktree remains unchanged, no protected permission is requested, no effect container remains, and the interrupted turn has no conclusion.
The [API fixture](../../../apps/api/plane/tests/contract/app/test_agent_worker_http.py) verifies the cancelled question and released reservation.
The native check passes in 30.403 seconds and the API check passes in 30.31 seconds.
Logs are `/tmp/plane-question-code-stop-native.log` and `/tmp/plane-question-code-stop-api.log`.

## Capacity recovery defect and repair

The `question_code_control: "restart"` mode kills the polling Worker while Code waits for its answer.
The replacement reconciles the old process and reservation, retains the same question and Worktree, and claims the Run under a new lease.
The first actual native check reproduced a slot-acquisition rejection because the restored Run was Awaiting.
The API only admitted In progress and Waiting capacity to a new reservation.

The [capacity API](../../../apps/api/plane/app/views/agent_worker_capacity.py) now admits Awaiting only when a pending question exists.
The FIFO query includes that state through an indexed existence check.
Repository grants, pending Stop, lease fencing, occupied reservations, and the shared pool limit retain their checks.
A reserved question Run returns to Awaiting; a full pool retains the question and enters Waiting capacity.
Awaiting without a question remains denied.

The [capacity checks](../../../apps/api/plane/tests/contract/app/test_agent_code_capacity.py) reproduce the rejection and verify FIFO behavior through a full one-slot pool and later release.
The initial focused run has one failure and one pass; the repaired capacity and question suite has 26 passes.
The repaired native check preserves question and operation IDs, clone and Worktree identity, and unchanged source before approval.
It removes the old process and uses a new reservation, then delivers the exact answer before separate write and commit approvals.
Actual Docker file production, Git commit, and the later protected Stop checks pass.
The native check passes in 61.169 seconds and the API check passes in 61.65 seconds.
Logs are `/tmp/plane-question-code-restart-native.log` and `/tmp/plane-question-code-restart-api.log`.
The initial native failure and capacity rejection logs are `/tmp/plane-question-code-restart-red-native.log` and `/tmp/plane-question-capacity-red.log`.

## Recovery task identity

An actual API regression after answer acceptance reproduced a second defect: recovery selected the latest accepted question answer as its current task.
This affected both an initial request with no panel task and a genuine accepted follow-up task.
The [recovery context API](../../../apps/api/plane/app/views/agent_worker_lifecycle.py) now excludes bound question answers from task selection.
The original accepted task remains current, and question and answered events remain in bounded recovery history.
The [question checks](../../../apps/api/plane/tests/contract/app/test_agent_run_question.py) verify the original request and the complete member follow-up, dispatch, acceptance, question, answer, expiry, Retry, and reclaimed context path.
Both cases fail before the repair and pass after it.
The focused red logs are `/tmp/plane-question-recovery-task-red.log` and `/tmp/plane-question-followup-recovery-red.log`.

## Gates and cleanup

All 53 capacity, question, and Worker lease API checks pass in 19.01 seconds with migrations enabled.
The log is `/tmp/plane-question-capacity-recovery-regression.log`.
Ruff lint and formatting pass for the six affected Python files.
Read-only review found no concrete defect in capacity admission, FIFO, task selection, exact native receipt checks, or cleanup.
Owned private control fixtures and failure diagnostics were removed, and all native test processes exited.
No private broker listener remains on ports 8769 or 8811.
The browser API was restored on port 8009 as `plane-timeline-ui-api-tests-run-d2deaf37b2fa`, with harness session 96366 and log `/tmp/plane-question-browser-api.log`.
The existing web server and test browser remain available.

## Remaining acceptance

Verify native recovery after Plane accepts an answer but before the turn completes.
Complete native Code recovery after answer delivery before acceptance.
Complete the other three Harness mappings and the remaining timeline and whole-story criteria.
Story 2.8 remains in progress, sprint status is unchanged, and the full goal remains active with 15 of 43 stories done.
