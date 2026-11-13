# Native question HTTP acceptance progress

## Scope

The [native check](../../../apps/agent-worker/tests/test_live_api.py) now supports question mode through the existing [Django HTTP fixture](../../../apps/api/plane/tests/contract/app/test_agent_worker_http.py).
The check starts the actual polling Worker process and authenticated Claude with the production MCP tool and Host boundary.
It uses actual HTTP delivery, member endpoints, durable question records, and lease recovery.
The initial Run, repository binding, and Git clone are declared fixtures.
This check does not prove live GitHub setup or other Harness behavior.

## Verified behavior

Claude publishes a question with two choices and receives the exact choice answer.
It then publishes a question without choices and receives the exact Unicode free-text answer.
Member submission retries retain the same message ID.
The Worker persists the native result before the corresponding durable `question_answered` event.
Claude reads the real clone and includes both answers and source content in its conclusion.
A later same-Run follow-up asks a third question and waits.
Member Stop terminates the native process, cancels that pending question, retains the two answered questions, and creates no conclusion for the interrupted turn.
The check creates no protected permission request or effect.

The waiting recovery mode kills the polling Worker before the first question has an answer.
It expires the saved lease, calls member Retry pickup, and starts another Worker.
The replacement reconciles the old Harness process and keeps the same question ID, operation ID, and clone inode.
The exact answer is then delivered and acknowledged under the replacement lease.

The delivered recovery mode holds the first acceptance request before the API accepts it.
At that point the native result is already stored, the answer is dispatching, and no answered event exists.
Worker death and fenced recovery retain the same question and answer.
The new native process retrieves the same answer and completes both questions without creating a duplicate question.
Both recovery modes also complete the later Stop check.

## Gates and review

| Mode | Native check | API check |
| --- | --- | --- |
| Normal questions and Stop | 28.158 s, pass | 37.34 s, pass |
| Restart while waiting | 30.048 s, pass | 29.97 s, pass |
| Restart after native delivery | 29.873 s, pass | 29.83 s, pass |

Logs are `/tmp/plane-question-http-native.log`, `/tmp/plane-question-http-api.log`, `/tmp/plane-question-waiting-native.log`, `/tmp/plane-question-waiting-api.log`, `/tmp/plane-question-delivered-native.log`, and `/tmp/plane-question-delivered-api.log`.
Ruff lint and formatting pass for both changed test files.
Read-only review found no concrete defect in the delivered modes or cleanup.
The first waiting fixture attempt incorrectly expected a member-visible lease generation; the corrected check uses the saved process record and durable claim events.
The first delivered fixture attempt incorrectly treated absence from the visible Queue as acceptance.
The corrected check waits for a durable answered event for the exact question ID, and the API separately requires accepted answer states and exact event counts.

## Cleanup and remaining work

Every native check exits and reconciles its owned process records.
No private MCP listener remains on ports 8769 or 8811.
Owned private fixture directories, tokens, sessions, and failure diagnostics were removed.
The browser API was restored on port 8009 as `plane-timeline-ui-api-tests-run-5e105a24a70b`, with harness session 98579 and log `/tmp/plane-question-browser-api.log`.
The existing web server on port 3000 and isolated test browser remain in use.

Complete native question delivery in Code and the other three Harnesses.
Verify recovery after Plane acceptance before native turn completion.
Complete the remaining timeline and whole-story criteria before changing Story 2.8 status.
The full goal remains active with 15 of 43 stories done.
