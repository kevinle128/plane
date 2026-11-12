# Stale retry acceptance progress

## Lease timing and fencing

The new production API check uses a controlled test clock instead of waiting five real minutes.
It claims the Run through the authenticated Worker endpoint and verifies an exact five-minute lease.
At four minutes and 59 seconds, the actual stale detection task leaves the Run active.
A valid heartbeat moves the last progress timestamp and grants five more minutes.
One microsecond before that renewed deadline, stale detection still leaves the Run active.
At the exact deadline, the task changes the Run to Stale, increments its generation, and retains all earlier event rows.
The stale event records the exact last progress timestamp.
The old heartbeat is rejected with 409, and a second stale detection pass adds no duplicate event.

The retry contract also checks actual member request idempotence, visible pending state in the member API, and the reconciliation requirement before claim.
A claim without reconciliation receives 409.
A reconciled claim receives generation three, recovers the original durable progress context, and acknowledges the retry command.
The extended check then sends both an old event replay and an old successful result.
Both return the specific lease rejection error with 409.
The complete current Run row and every event row remain equal after the rejected old-generation writes.

All 19 lease tests pass in 5.52 seconds.
The two focused timing and retry checks pass in 1.87 seconds before the final old-event and result assertions were added.
The complete 19-test run includes those final assertions.
Ruff lint and formatting pass for the changed test file.

```sh
docker compose -f docker-compose-test.yml run --rm api-tests pytest plane/tests/contract/app/test_agent_worker_lease.py -q
```

## Native process evidence

Four native process registry checks pass in 0.064 seconds.
They start actual isolated process groups and confirm that reconciliation stops a registered group.
A changed process start identity is rejected without stopping that process.
Startup clears a known registered group and retains an uncertain record.
A second Worker cannot reconcile the live owner's process while the Run root lock is held.
Each check stops and waits for its owned process before returning.

```sh
PYTHONPATH=apps/agent-worker:apps/agent-worker/tests python3 -m unittest \
  test_process_registry.ProcessRegistryTests.test_second_worker_does_not_reconcile_the_live_workers_process \
  test_process_registry.ProcessRegistryTests.test_reconcile_stops_only_a_registered_process_group \
  test_process_registry.ProcessRegistryTests.test_reconcile_rejects_a_changed_process_identity \
  test_process_registry.ProcessRegistryTests.test_startup_reconciles_registered_groups_and_keeps_uncertain_records
```

## Remaining acceptance

Story 2.19 remains in progress.
The actual browser Retry pickup action, retained last progress display, and unavailable Worker state after reload still need direct evidence.
The process registry checks are focused native safety checks, not a full Harness restart claim.
Existing protected effect restart evidence must be mapped to this story's no-replay criterion before completion.
The full goal remains active with eleven completed stories.
The separate AD-7 runtime exception question remains pending; no exception is enabled.

## Cleanup

The owned lease-contract Compose services and network are removed after the tests.
The temporary Compose override is removed.
No container from that isolated project remains running.
