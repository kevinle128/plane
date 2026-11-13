# Native follow-up HTTP progress

## Scope and fixtures

Extend the existing paired native HTTP check with `follow_up_context`.
Use the actual polling Worker, authenticated Claude, production MCP repository tools, Host OS boundary, HTTP member endpoints, and isolated PostgreSQL database.
The initial Run, repository binding, and local clone are fixtures.
After the first turn completes, the fixture updates the issue title and adds two public comments in order.
It also seeds one historical denied-decision audit snapshot and a separate Run on the same issue with private message and decision sentinels.
The decision snapshot tests historical context, not an actual permission approval or grant.
No protected effect, browser action, GitHub connection, or other Harness execution is claimed.

## Verified native flow

Claude reads the actual `source.txt` through the production Plane read-file tool and completes Q&A turn 1.
Wait until the Harness record clears after its process exits.
Apply the fixture issue updates and send an idle member follow-up through the real API.
The polling Worker claims turn 2 on the same Run and clone and reconstructs its context for a new native Claude process.
The answer contains the exact updated issue title, latest comment marker, prior decision `deny`, and its own `FOLLOWUP_1` marker.

After that Harness process exits, send another idle follow-up.
The new native process answers turn 3 with the current title, latest comment, prior decision, and `FOLLOWUP_2` marker.
Both member Run responses retain the original Run ID, clone path, and Q&A kind.
The source file stays unchanged.
Member event reads show completed turns in order 1, 2, 3.

The API fixture records the actual context responses delivered to the Worker for turns 2 and 3.
Both contain the updated issue title and ordered comment markers.
Both contain the earlier denied-decision snapshot.
Neither contains the other same-issue Run's private message or decision marker.
Turn 3 contains ordered prior turns 1 and 2 and the accepted message identity from turn 2.
No permission request is created.

## Checks

The native side passes in 41.72 seconds.
The API side passes in 31.32 seconds.
Focused Ruff lint and formatting pass for both changed fixture files.
The first lint check detected a loop variable captured by a predicate; bind that predicate's turn number before running the native check.
The [decision-context report](./2026-09-29-follow-up-decisions-progress.md) retains the API byte-limit, omitted-count, lease-fence, private-history, and Worker prompt checks.

## Remaining Story 2.13 work

Keep Story 2.13 in progress.
This is the verdict of the first native HTTP check; the later [browser acceptance](./2026-09-29-follow-up-browser-acceptance.md) completes Story 2.13.
Complete the production browser reply flow and verify ordered conclusions on one Run card after reopening the panel.
Other Harness conversation stories retain their own execution and recovery requirements.

## Review

**Summary:** Actual idle native follow-ups reconstruct current same-Run context and preserve clone identity across CLI process exits.
**Critical issues:** None found in the checked native flow.
**Major issues:** Browser reply and reopened conclusion checks remain required for Story 2.13.
**Minor issues:** Initial Run and historical denied-decision observations are fixtures.
**Positive feedback:** The API inspects context actually delivered to the Worker, including another Run's private-history exclusion.
**Questions:** AD-7 and DNS decisions remain pending and are not assumed.
**Verdict:** Retain Story 2.13 in progress and continue browser acceptance.

## Cleanup

The native and API processes exit successfully.
Remove the owned Compose containers and network, private fixture directory, and temporary override.
No owned listener remains on ports 8009, 8769, or 8811.
No token or member session is stored in the report or checkout.
