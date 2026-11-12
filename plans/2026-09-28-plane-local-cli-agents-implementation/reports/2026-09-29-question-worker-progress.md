# Question Worker integration progress

## Delivered behavior

The private Q&A and Code MCP apps now expose the same bounded `plane_ask_question` tool.
The [question controller](../../../apps/agent-worker/plane_agent_worker/run_questions.py) fixes the Run, turn, and lease through its existing workspace session.
It uses the current operation lock, checks pending controls, and waits with the turn's cancellation event.
The API client uses the durable question publication and answer endpoints.
The tool returns the exact question, operation, message, and answer receipt without sending acceptance.
Identical-operation retries can retrieve the same pending answer, while a different question waits for settlement.
Code effect grants remain separate from question answers.

The [Claude adapter](../../../apps/agent-worker/plane_agent_worker/claude_driver.py) keeps a bounded map of unresolved question calls.
It recognizes delivery only from a non-error native tool result associated with the same question call and operation.
The [Worker](../../../apps/agent-worker/plane_agent_worker/worker.py) persists every result event before it confirms the exact returned receipt and requests acceptance.
Changed receipts and pending Stop cannot acknowledge an answer.
An already accepted recovery receipt does not generate a second acceptance.
Q&A handoff waits until a returned question answer has been acknowledged.

## Recovery repair

The recovery prompt includes the pending question summary from the current claim and directs the Harness to reuse its exact operation, text, and choices.
A new API regression reproduced a missing answered-question event in recovery context after acceptance and another lease expiry.
The recovery event filter now includes `question_answered` within its existing event and character limits.
The [API check](../../../apps/api/plane/tests/contract/app/test_agent_run_question.py) verifies the repaired context through real lease expiry, member Retry pickup, reconciled claim, and HTTP endpoint reads.
All 35 question and Worker lease checks pass with migrations enabled.
The log is `/tmp/plane-question-answered-context-green.log`.

## Evidence and limits

The [question tests](../../../apps/agent-worker/tests/test_run_questions.py) cover deferred acceptance, exact receipts, same-operation retry, cancellation without a retained thread, invalid encoding, Stop before confirmation, and accepted recovery receipts.
The [MCP checks](../../../apps/agent-worker/tests/test_code_tools.py) exercise the actual private HTTP server and strict schemas for both Q&A and Code.
They reject authority fields, invalid operations, empty text, repeated or invalid choices, and excessive bounds before question publication.
The [control check](../../../apps/agent-worker/tests/test_worker_control.py) runs a real child process with a declared stdout fixture through the production turn controller.
It verifies persistence before acceptance and injects a result-event delivery failure that leaves acceptance pending and prevents a terminal result.
This stream fixture is not native Harness evidence.

Authenticated native Claude separately calls the actual question tool through the private MCP server and Host read-only boundary.
It receives the declared Unicode answer and emits the corresponding native tool result.
The test confirms that result before sending the first acceptance request.
That native check passes in 7.281 seconds.
Its Plane responses are a declared test fixture, so it does not prove the complete polling Worker and Django HTTP flow.
The log is `/tmp/plane-question-native-tool.log`.

The broader Worker regression runs 60 checks and passes, with five opt-in native checks skipped.
The relevant native question check was run separately with `PLANE_AGENT_TEST_CLAUDE_MODEL=sonnet`.
Ruff and formatting checks pass for the affected files.
Read-only review found no concrete defect in receipt binding, current lease routing, deferred acceptance, Stop checks, or the bounded adapter state.
All owned native and MCP test processes exit, and the private broker listeners are closed.

## Remaining acceptance work

Bind the production composer and choices to the current question identity.
Verify the actual polling Worker and Django HTTP flow, then browser answers and reload.
Verify restart before and after native answer delivery and Stop while a question waits.
Complete the required question mapping and acceptance for the other three Harnesses.
Story 2.8 remains in progress, sprint status is unchanged, and the full goal remains active.
The existing owned web server, isolated API stack, and browser are retained for the next checks.
