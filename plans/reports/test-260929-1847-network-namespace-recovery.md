---
status: in-progress
scope: "Story 3.4 network recovery and revoked authority"
---

# Network namespace recovery and revoked authority

## Summary

The full implementation goal remains active.
Story 3.4 remains in progress.
The [active plan](../2026-09-28-plane-local-cli-agents-implementation/plan.md) and accepted epic criteria retain the complete scope.

## Passed evidence

| Check | Native | API | Scope |
| --- | --- | --- | --- |
| Death after bridge creation | 43.447 seconds | 43.36 seconds | Actual polling Worker, Claude, Code MCP, Docker, member decisions, and historical reconciliation. |
| Revoked repository authority | 7.533 seconds | 7.40 seconds | Real Code MCP and Plane HTTP APIs; no Harness or polling Worker in this mode. |

The [polling Worker fixture](../../apps/agent-worker/tests/test_live_api.py) accepts four namespace checkpoints through `command_namespace_crash`.
The bridge check kills the original Worker while its real Docker creation response is held.
The journal remains prepared with network phase starting and an actual bridge without a bound creation receipt.
Both exact command and network grants have been consumed, but no command container or execution counter exists.
A new polling Worker reports one unknown historical result with both original grant identities before clearance and capacity release.
The counter stays absent, later human source edits survive, and Git HEAD and index bytes remain unchanged.
Plane retains the stale Run without another claim or effect replay.

The [Code MCP fixture](../../apps/agent-worker/tests/test_live_network_api.py) and [network API fixture](../../apps/api/plane/tests/contract/app/test_agent_worker_network_http.py) add `mcp_revoke`.
Both decisions use the real member HTTP endpoint.
The fixture archives the repository installation grant inside the existing network-decision transaction and Run lock, before the saved approval can be observed by another request.
The production permission status endpoint then rejects both original grants with HTTP 409.
Code MCP returns an error and cancels further tool work.
Both grants remain unused, no output or journal is created, and the repository source remains unchanged.
Direct Docker queries show no container or bridge for the Run before the actual slot release.
Plane records no normal or historical command result and releases capacity after the saved network decision.
This simulates an unavailable stored installation grant; it does not claim live GitHub installation removal.

## Failures and corrections

The controller-creation polling check was interrupted before a terminal result.
The resumed orchestration cell was absent, and direct process and Docker inspection found no remaining fixture process or network resources.
That interrupted check is not accepted as passed.

Its fresh retry failed before the network checkpoint during initial Q&A.
Native evidence recorded Claude's session limit and a reset time of 19:20 in Asia/Saigon.
The native check failed in 8.662 seconds; the API check failed in 7.22 seconds.
No model fallback or passing result was substituted.
Controller creation, controller start, and filter installation still require full polling Worker and API checks after the external limit clears.
Their separate native process-death checks remain valid in the [network progress record](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-network-boundary-progress.md#native-process-death-during-namespace-creation).

The first revoked-authority fixture used an outer transaction around WSGI request delivery.
Django closed the request connection before that outer transaction ended, producing an HTTP 500 and `OperationalError: the connection is closed`.
The API failed in 5.43 seconds and the native check failed in 5.887 seconds.
The fixture now injects only the revocation checkpoint inside the existing production decision transaction.
The actual decision, permission polling, stored grant, and Docker absence checks remain in use.
The corrected pair passed, and the final pair above also verifies unchanged source and direct resource absence.

## Review and gates

Scoped review confirms that the new branches apply only to explicit fixture modes.
Normal execution, permission decisions, and recovery use the existing production paths.
No production security rule or public API contract changed in this batch.
Ruff lint, Ruff format, and Python compilation passed for the four HTTP fixture files.
Private database backups preceded new database fixture changes.
No fixture controller or bridge remained after validation.
Six owned private fixture directories were removed after terminal results and process reconciliation.
Their temporary Worker tokens and member sessions were not copied into the checkout or reports.
Private database backups remain outside the checkout with mode 0600.
The owned browser API is restored in `plane-timeline-ui-api-tests-run-3982be1f70f7` on localhost port 8009 with harness session 34497.
Its instance endpoint returns HTTP 200; it remains available for ongoing goal UI checks.

## Remaining acceptance

- Full polling Worker and API death at the three remaining namespace checkpoints.
- Full polling Worker revocation and visual permission flows.
- Granted hostname resolution after the DNS product decision.
- Other required Harness conformance and complete Story 3.4 acceptance.

## Unresolved questions

The prior DNS authorization and other-Harness runtime-write decisions remain pending.
