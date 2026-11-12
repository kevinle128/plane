# Answer acceptance recovery progress

## Scope and evidence

The paired [API fixture](../../../apps/api/plane/tests/contract/app/test_agent_worker_http.py) and [native Worker check](../../../apps/agent-worker/tests/test_live_api.py) now test Worker death on both sides of answer acceptance.
The fixture holds only acceptance requests for messages bound to a question.
The `delivered` mode holds before the API commits acceptance.
The `accepted` mode executes the API request and checks its successful response before it holds the response and the check kills the Worker.
These are declared transport faults in the isolated test stack.

Actual polling Worker and Claude Q&A recovery after acceptance passes in 25.253 seconds; the API check passes in 25.04 seconds.
Logs are `/tmp/plane-question-accepted-native.log` and `/tmp/plane-question-accepted-api.log`.
Code recovery after native delivery before acceptance passes in 58.210 seconds; the API check passes in 57.94 seconds.
Logs are `/tmp/plane-question-code-delivered-native.log` and `/tmp/plane-question-code-delivered-api.log`.
Code recovery after committed acceptance passes in 62.815 seconds; the API check passes in 63.07 seconds.
Logs are `/tmp/plane-question-code-accepted-native.log` and `/tmp/plane-question-code-accepted-api.log`.

The checks retain the exact Unicode answer, operation, question, and message receipt.
They verify the committed answered event, old process removal, replacement lease, and original clone and Worktree identity.
Code acquires a replacement reservation and completes actual Docker content production and Git commit through separate protected approvals.
The later protected Stop checks also pass.
No new production repair was required for these three cases.

## Gates and limits

Ruff lint and formatting pass for both test files.
Read-only review found no concrete defect in the fault boundary or recovery checks.
All native test processes exited, and the three owned private input directories were removed.
The browser API was restarted with harness session 60522 and log `/tmp/plane-question-browser-api.log`.
The existing web server and test browser remain available for the next UI acceptance checks.

This evidence covers Claude only.
Other Harness mappings and the complete Story 2.8 acceptance audit remain required.
Sprint status stays unchanged at 15 of 43 stories done, and the full goal remains active.
