# Run grant acceptance

## Result

Story 3.2 meets its three acceptance criteria.
The existing production grant contract required no change for this acceptance check.
All other stories keep their own acceptance requirements.

## Actual native flow

The native HTTP mode uses `{"model":"sonnet","run_grant":true}` as its private input.
The actual polling Worker runs Claude, Docker, and Git against the actual Django HTTP fixture.
A member grants the first exact file write with Allow for this Run.
Claude then proposes a second write to the same path with different content and a different effect hash.
Plane retains a separate request that points to the original Run grant, and the Worker completes both Docker writes.
The resulting file contains the second exact content.
The separate commit still requires its own permission and records the configured Human identity.
A later request to create `broadened.txt` remains pending without an inherited grant.
Stop leaves that file absent and preserves the previously granted file content.
The default branch and original clone stay unchanged.

## Acceptance evidence

| Criterion | Direct evidence |
| --- | --- |
| Record member, time, request ID, action, normalized scope, and effect hash | The paired API fixture checks the original persisted decision and its single permission decision event; the production browser decision and reload checks are recorded in the [permission scene report](./2026-09-29-permission-and-pr-scenes-progress.md). |
| Permit later matching effects with request-linked audit | The native Worker completes two actual writes with distinct hashes; the API checks both consumed requests, matching scope, original actor, and the second request grant ID. |
| Require new permission for broader path, network, action, or Run identity | Native broadened-path request stays pending before Stop; API contracts reject broader and recursive path scopes, changed action, changed network destination or resolved IPs, and a separate Run with the same repository binding. |

The API contracts also check removed membership, removed grants, and current lease authority after recovery.
The cross-Run check creates a separate active Code Run through the existing database fixtures and submits the same action and exact path through the real permission endpoint.
It receives a pending request without a grant.

## Validation

- The permission contract suite passes: 89 tests in 35.18 seconds.
- The final paired Django HTTP fixture passes: one test in 46.72 seconds.
- The final actual native Worker check passes: one test in 46.918 seconds.
- Ruff lint and format checks pass for all three changed test files.
- Read-only quality review found no source defect or missing criterion; the requested final paired API rerun and permission suite both pass.

The first contract attempt omitted the separate Run repository binding in its test fixture.
That attempt correctly failed at the existing Code authority check; the corrected fixture passes.
The first paired API attempt expected two consumed permissions after the mode added a second matching write.
The native flow passed, and correcting the expected count to three made the final paired check pass.
Neither failure required a production behavior change.

Source checks are in [the permission contracts](../../../apps/api/plane/tests/contract/app/test_agent_run_permission.py), [the paired HTTP fixture](../../../apps/api/plane/tests/contract/app/test_agent_worker_http.py), and [the native Worker check](../../../apps/agent-worker/tests/test_live_api.py).
Local terminal logs are `/tmp/plane-run-grant-contract-green.log`, `/tmp/plane-run-grant-final-api.log`, and `/tmp/plane-run-grant-final-native.log`.
This evidence does not establish live GitHub delivery or execution conformance for the other three Harnesses.
