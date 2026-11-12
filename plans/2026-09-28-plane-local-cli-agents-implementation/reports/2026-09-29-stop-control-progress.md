# Stop control acceptance progress

## Permission rejection without data loss

The extended control test uses an active test Run with one queued message and a pending Send now command.
The member creates the queued message and Send now command through the production endpoints.
The active lease is explicitly prepared test state.
An outsider and an active restricted project guest each attempt a message and confirmed Stop through the actual API.
Both requests return 403 for each user.
The complete Run row, every message, every command, and every event remain equal to the original state.
The rejected Stop does not clear the existing queue or cancel the member's pending command.

## Stop settlement

The extended authenticated Worker control test has one accepted message, one dispatched message, and one queued message before Stop.
The member requests confirmed Stop through the production API.
The Worker receives the fenced command and acknowledges it through the production endpoint.
The queued message becomes cancelled, and the dispatched message becomes interrupted.
The Run becomes Stopped with a finish timestamp and a new lease generation.
The acknowledged command time equals the Run finish time, and its acknowledged generation matches the old lease.
The stopped event records the requesting member, one discarded queued message, and one interrupted dispatched message.
The event timestamp is at or after the Run finish timestamp.
The stored clone path remains equal to its original test value.
This contract test does not prove retention of real Git files or interruption of a real Harness process.

The three focused authorization and Worker settlement checks pass in 2.03 seconds.
The complete lease/control file passes all 20 checks in 5.85 seconds.
Ruff lint and formatting pass for the changed test file.

```sh
docker compose -f docker-compose-test.yml run --rm api-tests pytest plane/tests/contract/app/test_agent_worker_lease.py -q
```

## Protected effect boundaries

Six existing Stop boundary checks pass in 2.94 seconds.
They cover external path reads and writes with Allow once or Allow for Run, command-bound network consumption, and permission decisions.
The tests prepare a pending Stop and verify that the protected permission operation is rejected.
Fifteen non-Stop parameter cases are explicitly deselected for this focused gate.
These checks verify the API permission boundary, not full Harness Stop delivery.

```sh
docker compose -f docker-compose-test.yml run --rm api-tests pytest \
  plane/tests/contract/app/test_agent_run_permission.py::test_external_path_grant_requires_live_run_and_member \
  plane/tests/contract/app/test_agent_run_permission.py::test_command_network_consumption_requires_both_current_permissions \
  plane/tests/contract/app/test_agent_run_permission.py::test_permission_rejects_invalid_stale_and_stopped_requests \
  -k stop -q
```

## Remaining acceptance

Story 2.17 remains in progress.
The production browser confirmation explanation, cancellation with no command, and Stopping/Stopped state after refresh still need direct evidence.
The full native Harness interruption evidence and effect boundaries must be reconciled with these tests before completion.
The complete goal remains active with twelve completed stories.

## Cleanup

The owned Stop contract Compose services and network are removed after all test handles finish.
The temporary override is removed.
No container from that isolated project remains running.
