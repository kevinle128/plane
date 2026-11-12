# Denied effect acceptance

## Result

Story 3.3 meets its three acceptance criteria.
The existing production permission and effect boundary required no change.
The new native HTTP mode closes the missing complete denial and changed-effect flow.

## Actual flow

The private fixture input is `{"model":"sonnet","deny_effect":true}`.
The actual polling Worker starts Claude in the existing OS sandbox and proposes an exact Worktree file write through the Code MCP tool.
A member denies that request through the actual Plane HTTP endpoint.
The file still contains its original repository content, no Docker effect container exists, and the denied request has no consumed grant.
The durable native tool result contains exactly the denied status and the original permission ID.
No completed effect event refers to that denied request.
Claude then proposes different content for the same file through a separate tool call.
Plane creates a new pending request with a different request ID and effect hash, without a grant.
The file stays unchanged until the member separately selects Allow once for that new request.
The Worker then performs the approved Docker write and a separately approved local commit with the configured Human identity.
The existing later Stop checks preserve the clone, branch, and approved content.
The default branch remains unchanged.

## Acceptance evidence

| Criterion | Direct evidence |
| --- | --- |
| Durable Deny decision, time, request ID, action, and scope | The paired API fixture checks the saved decision, actor, timestamp, and single matching permission decision event; the [production browser report](./2026-09-29-permission-and-pr-scenes-progress.md) proves actual Deny selection and retained display after reload. |
| Block the denied effect and report denial as an interaction | The actual native Worker receives a denied MCP result with the exact permission ID; the file remains unchanged, the grant is unconsumed, and no completed denied effect exists; the focused Docker check attempts writes to read-only Worktree, root, temporary, shared-memory, and linked paths and observes rejection. |
| Create a new request for a materially different effect | The native Agent proposes different exact content; Plane returns a new pending request and distinct hash without a grant, and the file changes only after a separate member approval. |

The existing API contract also rejects consumption of a denied request and returns a separate pending request for a later changed effect.
The native broker denial check exposes only the approved Code tool set and makes no Docker write.

## Validation

- Paired Django HTTP fixture: one test passes in 54.49 seconds.
- Actual native polling Worker: one test passes in 53.909 seconds.
- Full permission contract suite: 89 tests pass in 33.95 seconds.
- Focused native broker denial and Docker boundary: two tests pass in 8.216 seconds.
- Ruff lint and format checks pass for all three changed test files.
- Read-only quality review found no concrete source defect or missing criterion; its requested paired integration result is now green.

The first focused native check found a stale expected tool set that omitted the existing `plane_ask_question` tool.
The test now includes that existing tool and still requires exact equality for the complete allowed set.
The focused rerun passes.
No production tool permission was expanded by this correction.

Source evidence is in [the paired HTTP fixture](../../../apps/api/plane/tests/contract/app/test_agent_worker_http.py), [the actual native Worker check](../../../apps/agent-worker/tests/test_live_api.py), [the permission contracts](../../../apps/api/plane/tests/contract/app/test_agent_run_permission.py), and [the native boundary checks](../../../apps/agent-worker/tests/test_docker_sandbox.py).
Terminal logs are `/tmp/plane-deny-effect-api.log`, `/tmp/plane-deny-effect-native.log`, `/tmp/plane-deny-effect-contract.log`, and `/tmp/plane-deny-effect-boundary-green.log`.
The initial tool-set failure is retained in `/tmp/plane-deny-effect-boundary.log`.
The other Harnesses, full network flow, and live GitHub publication retain their separate story requirements.
