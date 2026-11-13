# Timeline failure detail progress

## Scope and reproduced failures

The handoff requires an expanded error card with its exit code and a monospaced hint.
The actual Worker previously recorded the terminal failure without a separate error event.
A real subprocess inside the Q&A OS sandbox returned a declared error result and exited with code 17.
The focused test failed because no error event was recorded.
The production web with an isolated API also failed to show the persisted exit code in a declared error event.

## Repair

After process exit and Code cleanup, the Worker posts a lease-fenced error event before its terminal result.
It records the actual process return code, the bounded final failure reason, and the turn number.
The event source key uses the lease generation for idempotent delivery.
The hint directs the member to review the error and check the Agent connection before starting a new Run with a new mention.
It does not infer expired authentication, expose stderr, or offer a Retry action for an ordinary terminal failure.

The shared panel error card shows a valid integer exit code and an optional recorded hint.
The hint remains plain text in a named, focusable scroll region.
Older errors without these fields still display their original reason.
The danger card and icon use existing semantic tokens.

## Direct evidence

The [Worker control check](../../../apps/agent-worker/tests/test_worker_control.py) verifies actual sandbox subprocess failure, exact code 17, original reason, turn identity, interrupted pending-message settlement, and error-before-result ordering.
The subprocess output is a declared Harness-format fixture; it is not a claim of native CLI authentication failure.
Nine Worker control and Code turn tests pass.
The [API lease check](../../../apps/api/plane/tests/contract/app/test_agent_worker_lease.py) now includes the error metadata.
All three selected event-kind cases pass with exact stored payload equality, idempotent replay, conflicting replay, wrong owner, wrong generation, expired lease, and revoked Worker rejection.

The [browser check](../../../apps/web/tests/agent-timeline-details.e2e.mjs) uses the production web and API with declared history.
It reproduces the absent exit code and then verifies the repaired exact exit code, full hint, keyboard focus, persisted Failed state after reload, and 375 px layout.
The [narrow error capture](./timeline-details-ui/narrow-error.png) was inspected and has no document overflow.
Web type checks, targeted OxLint, formatting, and Worker Ruff pass.
Existing Vite configuration warnings remain visible.
Read-only review found no concrete defect in the failure path or its compatibility with older events.
The final Worker and browser checks passed after review.
The owned browser, web server, API server, and isolated dependency containers were stopped.
Ports 3000 and 8009 have no remaining listener.

## Remaining acceptance

Story 2.8 remains in progress for all remaining scenes and accessibility criteria.
Repository elicitation uses the actual authorized selection flow verified in [Story 2.11](./2026-09-29-run-repository-acceptance.md).
The final fresh-clone architecture governs that flow; the prototype's suggested reused mirror paths are not production authority.
Native authentication failure across all four Harnesses remains part of their conformance stories.
