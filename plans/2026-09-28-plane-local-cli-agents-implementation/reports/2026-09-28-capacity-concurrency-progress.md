# Shared Code pool concurrency

## Scope

The preceding goal turn proved HTTP creation and recovery and repaired inconsistent permission reads.
This turn verifies the shared Code pool across workspace boundaries while the AD-7 runtime decision remains pending.
No Harness runtime write exception is enabled.

## API evidence

The new [capacity check](../../../apps/api/plane/tests/contract/app/test_agent_code_capacity.py) prepares six Code Runs across two workspaces with six separate Worker identities and registered tokens.
It uses the shared pool with two slots and interleaved durable enqueue times.
Three queue waves issue 36 duplicate acquisition requests through six concurrent API clients.
Every concurrent request checks the active global count and maintains its live lease through the production heartbeat endpoint.
After retry in durable order, each wave assigns only the oldest two Runs, one from each workspace.
The workspace slot list exposes only its own reservation while reporting the shared capacity.
Six reservations use six distinct container names.
Repeated releases produce one release event per reservation.

The first wave expires one active lease and runs the production stale task.
Both reservations remain occupied, and later Runs still wait until a registered Worker reports reconciliation and releases the slots.
The check passed in 33.88 seconds.
The full capacity and Worker lease gate passed all 22 checks in 61.97 seconds.
The fixture now uses one shared Run construction helper so the second workspace has the same repository and membership contracts as the first.

This is direct PostgreSQL and API allocation evidence.
The release receiver accepts trusted Worker observations as the production API does.
It does not create six Docker containers or establish memory, process, or deployed Mini limits.
Actual concurrent Docker load, the waiting UI, and four-Harness execution remain required.

## Test stack startup repair

The first test command stopped before pytest because RabbitMQ could not read its Erlang cookie.
The stopped broker recorded `eacces` for `/var/lib/rabbitmq/.erlang.cookie`.
The installed image entrypoint changes ownership once, then starts the broker as user 100.
The old health command bypassed that entrypoint and ran diagnostics as root.

A disposable native image probe reproduced the ownership race without printing cookie contents.
The old command created a mode-400 cookie owned by user 0, which user 100 could not read.
The command through the image entrypoint created a mode-400 cookie owned by user 100, which the broker user could read.
The [test Compose file](../../../docker-compose-test.yml) now uses the image entrypoint for diagnostics.
The recreated broker became healthy and both test gates passed.
Cookie permissions remain private, as required by the [RabbitMQ CLI authentication contract](https://www.rabbitmq.com/docs/cli#authentication).
The [test guide](../../../apps/api/tests/RUNNING_TESTS.md) explains the health command and safe handling of occupied ports.

Compose validation, touched Python format and syntax and undefined-name checks, and diff checks passed.
All owned runner and probe handles exited, and the capacity test stack was removed with its temporary volumes.
Only the three unrelated pre-existing containers remain.

## Review

**Summary:** Verify global FIFO allocation across two workspaces and repair the observed broker health-check ownership race.
**Critical issues:** No open issue in the tested queue waves, slot count, expiry retention, or health-check ownership.
**Major issues:** Actual concurrent Docker and deployed limits, waiting UI acceptance, and four-Harness execution remain unverified.
**Minor issues:** Source inspection shows that the waiting-head query does not include repository-grant validity; a revoked queued head needs a direct regression check next.
**Positive feedback:** The checks reuse the actual lease, heartbeat, stale, reservation, and release endpoints.
**Questions:** The AD-7 runtime exception needs the member decision before the other three Harnesses can receive writable runtime state.
**Verdict:** Comment; Story 3.6 and the all-story goal remain in progress.

## Revoked repository queue head

The preceding goal turn added cross-workspace queue evidence and identified a missing grant check in candidate selection.
This turn reproduced the failure through the actual Worker capacity API on PostgreSQL.
The oldest Run was prepared in one workspace, and a granted follower was prepared in another.
After removal of the head's connection, installation, or binding, or a change to its bound base reference, the head was correctly denied with 409.
The follower still received `waiting: true` despite an empty pool.
All four regression cases failed in 74.96 seconds.

The [capacity endpoint](../../../apps/api/plane/app/views/agent_worker_capacity.py) now applies a database grant filter before it selects the oldest candidate.
The [shared repository utility](../../../apps/api/plane/utils/agent_run.py) checks a live workspace connection and either the exact active project binding snapshot with its installation or the matching active catalog generation and repository identity.
It uses correlated existence checks and JSON identity comparisons in the same candidate query.
It does not loop through Runs with a separate grant query per candidate.
The occupied-slot count, reconciliation rule, Worktree, and enqueue times remain unchanged.
The original per-request authority check still rejects the revoked head.

The first four repaired cases passed in 3.43 seconds.
Eight final API cases, including catalog entry removal, catalog generation change, and catalog connection or installation removal, passed in 3.75 seconds.
The grant-filter check compares valid binding, changed binding snapshot, valid catalog selection, and rotated catalog generation with the existing authority predicate.
It requires one SQL query for the candidate batch in each state.
The complete capacity and Worker lease gate passed all 31 checks in 11.99 seconds.
Touched Python format, syntax and undefined-name checks passed.

### Queue grant review

**Summary:** Stop an invalid repository grant from blocking capacity in another workspace.
**Critical issues:** The observed cross-workspace queue blockage is fixed and passes all eight revocation cases.
**Major issues:** Actual concurrent Docker load, deployed resource bounds, waiting UI acceptance, and four-Harness execution remain required.
**Minor issues:** The grant query and the per-request predicate have explicit parity checks for the supported binding and catalog paths.
**Positive feedback:** Eligibility stays in one database query, and no occupied reservation is freed without Worker reconciliation.
**Questions:** The pending AD-7 runtime decision is separate from this queue repair.
**Verdict:** Comment; the queue repair passes, while Story 3.6 and the all-story goal remain in progress.

## Concurrent Docker resource enforcement

The [native Docker check](../../../apps/agent-worker/tests/test_docker_sandbox.py) now runs two bounded approved commands through the production Docker command primitive with separate Run identities, Worktrees, and effect registries.
Both containers must be running before a shared gate permits their commands to execute.
Each uses the installed pinned image, 128 MiB of memory, equal memory and swap limits, and a process limit of 16.
The command starts a child that allocates memory until the kernel kills it.
It checks the child exit signal and the increased `memory.events` OOM-kill counter.
It then starts child processes until fork returns `EAGAIN` and checks the `pids.events` limit counter.
All surviving children are killed and reaped in the command's `finally` block.
The production command supervisor confirms the result and stops each verified container.
The test checks that both command records are cleared and both source files remain unchanged.
The test fixture removes its own containers and temporary repositories.

The first test run found a newline-escape error in the new embedded test program before pressure began.
The corrected raw string passed the focused check in 1.584 seconds.
The combined concurrent-pressure, read-only boundary and recovery, output and timeout and descendant, and Stop checks passed all four cases in 9.402 seconds.
Ruff formatting and lint checks passed for the changed test file.
No production behavior or security exception changed.

This is actual simultaneous Docker resource-enforcement evidence.
It does not prove the complete API-to-Worker queue under sustained Docker load, deployed Mini resource sizing, waiting UI, or all four Harnesses.
Those acceptance requirements remain open, and the AD-7 runtime decision remains pending.
Diff checks and local document link checks passed.
Both owned test handles are terminal, and Docker lists no remaining container from these test fixtures.
The unrelated pre-existing containers remain unchanged.

### Resource check review

**Summary:** Add direct concurrent memory and process enforcement evidence through the existing Docker command primitive.
**Critical issues:** No open issue in the tested resource limits or result settlement.
**Major issues:** Sustained end-to-end queue, deployed resource bounds, waiting UI, and four-Harness evidence remain required.
**Minor issues:** The check uses a small two-container load and makes no throughput claim.
**Positive feedback:** Kernel counters prove enforcement, and the tests require actual concurrent running containers before commands start.
**Questions:** The AD-7 decision remains separate from this resource check.
**Verdict:** Comment; both affected stories and the full goal remain in progress.
