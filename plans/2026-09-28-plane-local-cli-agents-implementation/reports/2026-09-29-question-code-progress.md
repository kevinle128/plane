# Native Code question progress

## Reproduction and repair

The actual polling Worker and Claude Code flow reproduced a question acceptance failure in the Code Worktree.
Plane stored the question, the member's exact answer, and the native result, but the answer remained dispatching.
The later protected write correctly failed because the pending question had not been acknowledged.
The native check timed out waiting for that acknowledgment.

The [Worker](../../../apps/agent-worker/plane_agent_worker/worker.py) selected `CodeTurn.session` before `CodeTurn.start` created it.
Its question handler was therefore absent during native result processing.
The handler selection now occurs after Code startup and before Harness launch.
The same selection still serves Q&A.
No permission check was weakened.

The [ordering regression](../../../apps/agent-worker/tests/test_worker_control.py) now covers late Code session creation as well as Q&A.
It failed for Code before the repair and passes after it.
Both modes retain the existing result-persistence failure check that prohibits answer acceptance and a terminal result.

## Actual HTTP evidence

The [native HTTP check](../../../apps/agent-worker/tests/test_live_api.py) supports `question_code: true` with the existing [Django fixture](../../../apps/api/plane/tests/contract/app/test_agent_worker_http.py).
Claude starts in Q&A, requests Code, and asks its confirmation question in the assigned Worktree.
The member answers with complete Unicode free text.
The native receipt check assembles ordered result parts, decodes their content, and compares the exact answer, operation ID, question ID, and message ID before the corresponding acknowledgment event.
This replaces a weaker text-prefix assertion identified during review.

The Worktree remains unchanged before the answer and before write approval.
The answer grants no protected effect.
The existing exact file-write permission is separately approved, Docker produces the file change, and a separate commit permission allows actual Git commit creation.
The conclusion includes the exact answer and commit ID.
The same Run and turn retain both the implementation message and the bound question answer.
The original clone and default branch remain unchanged.
The later Stop test prevents another file change and releases the Code reservation.

The repaired native flow passes in 43.942 seconds.
The API fixture passes in 43.77 seconds and verifies the saved answered question, accepted answer, event count, and existing permission and Code assertions.
Logs are `/tmp/plane-question-code-native.log` and `/tmp/plane-question-code-api.log`.
The focused red and green ordering logs are `/tmp/plane-question-code-controller-red.log` and `/tmp/plane-question-code-controller-green.log`.

## Review and regression

All 21 question, Claude parser, and Worker control checks pass in 1.054 seconds.
The log is `/tmp/plane-question-code-worker-regression.log`.
An earlier concurrent regression run collided with the active native broker on port 8811.
The final regression ran after the native flow exited and both private ports were confirmed free.
Ruff lint and formatting pass for all four affected Python files.
Read-only review found no concrete regression in handler initialization, persistence ordering, exact receipt checks, or cleanup.

## Cleanup and remaining work

Owned private Code fixtures and failure diagnostics were removed.
The native Worker and test processes exited, and private broker listeners are closed.
The browser API was restored on port 8009 as `plane-timeline-ui-api-tests-run-a979ae0ad55a`, with harness session 59664 and log `/tmp/plane-question-browser-api.log`.
The existing web server and test browser remain available for further acceptance work.

Verify recovery after Plane acceptance before native turn completion.
Complete native Code question restart and Stop while its question waits.
Complete the other three Harness mappings and the remaining whole-story criteria.
Story 2.8 remains in progress and the full goal remains active with 15 of 43 stories done.
