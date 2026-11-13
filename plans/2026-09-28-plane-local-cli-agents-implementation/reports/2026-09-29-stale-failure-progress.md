# Stale failure acceptance progress

## Verified API behavior

The extended production endpoint test claims a Run with a registered Worker token, dispatches a queued message, expires its lease, and runs the actual stale detection task.
The task interrupts the dispatched message.
An outsider and an active project guest without comment access both receive 403 from Mark failed.
The authorized member must supply a reason.
Confirmed failure creates one conclusion comment and retains idempotent response behavior.
The recorded actor, reason, and timestamp match the member and the Run finish time.
The stored clone path and all earlier event rows remain unchanged.

The old Worker lease receives 409 for both a late event and a late successful result.
The test compares the complete Run row, all event rows, all turn rows, and all issue comment rows before and after these requests.
All rows remain exactly equal.

Run the check with the isolated Docker test stack:

```sh
docker compose -f docker-compose-test.yml run --rm api-tests pytest plane/tests/contract/app/test_agent_worker_lease.py -q
```

The focused stale failure test passes in 1.62 seconds.
All 18 Worker lease tests pass in 5.27 seconds.
Ruff formatting and lint checks cover the changed test file.

## Remaining acceptance

Story 2.20 remains in progress.
The retained clone path in this API test is an explicit fixture value; it does not prove retention of real Git files.
The browser confirmation, cancellation, validation, refresh, and failed conclusion still need direct runtime evidence.
The native authenticated Worker client must also demonstrate late HTTP event and result rejection against that browser flow.
No full Harness execution or GitHub clone claim is made from this contract test.
