# Code Stop acceptance

## Result

Story 3.7 meets its three acceptance criteria.
The existing production Stop, effect recovery, and capacity contracts required no change in this check.
The new mode combines the missing queue, retained PR, and next-slot assertions with the actual active-command Stop flow.

## Actual native Stop

The private input is `{"model":"sonnet","code_stop_handoff":true}` without other modes.
The check runs the actual polling Worker, native Claude, Code MCP, Django HTTP API, and Docker.
The configured Code capacity is one slot.
An exact file write, process command, and pinned network destination receive separate member approvals.
The command starts in a real container, writes its execution counter once, and remains active.
Two member follow-ups enter the queue before Stop.
A later human file edit is made while the command is active.
The member confirms Stop through the actual API.
The Worker interrupts the native Harness and command, reconciles the unknown active-command result, then releases capacity and acknowledges Stop.
The two undelivered follow-ups are cancelled.
The exact member identity and acknowledgement time are recorded, and the Run becomes Stopped.
The command execution counter stays at one, the later human edit remains, and no command completion or commit is reported.
No native Harness process, command container, or retained command journal remains for the stopped Run.

## Retained state and next Code job

A declared existing PR event tests retention; it does not represent live GitHub publication.
The member Run endpoint returns the same PR object before and after Stop.
The clone path, Worktree path, Git branch, branch HEAD, and all pre-Stop timeline events remain equal.
The default branch HEAD remains unchanged.
The existing [browser Stop report](./2026-09-29-stop-acceptance.md) proves member confirmation and retained stopped state after reload.
The [PR scene report](./2026-09-29-permission-and-pr-scenes-progress.md) proves the stored PR presentation in the actual panel.

The waiting job is another actual Run with the same repository binding and its own Worker identity.
The trusted test controller uses the production PlaneClient to claim that Run, register its actual local Git clone, reserve its branch, and register its verified Worktree.
Its slot request returns waiting while the original command occupies the only slot.
After the old command container is absent and its slot is released, the waiting Run receives that same slot number.
The database timestamps confirm that its reservation starts after the previous release.
The check starts an actual read-only Code container for the waiting Run and confirms the original container is still absent and only one slot is active.
It stops and removes the new container, reports verified absence, and releases the slot.
This next-job check uses the production API, Git, Docker, and trusted controller; it does not start a second native Harness.

## Acceptance matrix

| Criterion | Direct evidence |
| --- | --- |
| Stop interrupts Harness and container, clears undelivered messages, and records actor/time/state | Actual polling Worker and native Claude active-command Stop, two actual member queued messages, cancelled records, exact member and acknowledgement timestamp, and absent process/container. |
| Clone, Worktree, branch, timeline, and existing PR remain; no default merge | Actual member API before/after equality, actual Git branch and HEAD equality, retained human content, exact event prefix equality, unchanged default HEAD, and existing production browser evidence. |
| Waiting Code job can take the released slot without exceeding the limit | Real waiting slot response at capacity one, confirmed old-container absence, same-number new reservation after release, one active slot, actual next Docker container, and verified teardown/release. |

## Validation

- Paired actual Django HTTP fixture passes in 80.90 seconds.
- Actual native polling Worker check passes in 80.254 seconds.
- Capacity and lease/control API suite: 43 checks pass in 15.03 seconds.
- Focused Worker Code control suite: three checks pass in 0.573 seconds.
- Ruff lint and format checks pass for both changed test files.
- Read-only quality review found no concrete source defect or fixture leak; its requested final paired check now passes.

The local logs are `/tmp/plane-code-stop-handoff-api.log`, `/tmp/plane-code-stop-handoff-native.log`, `/tmp/plane-code-stop-capacity-contract.log`, and `/tmp/plane-code-stop-control.log`.
Source checks are in [the paired HTTP fixture](../../../apps/api/plane/tests/contract/app/test_agent_worker_http.py), [the native Worker check](../../../apps/agent-worker/tests/test_live_api.py), [the capacity contracts](../../../apps/api/plane/tests/contract/app/test_agent_code_capacity.py), and [the Worker control checks](../../../apps/agent-worker/tests/test_code_turn.py).
Other Harness execution, live GitHub delivery, and sustained Mini capacity testing retain their own story requirements.
