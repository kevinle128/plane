# Plan reporting HTTP acceptance

## Scope and environment

Complete the native-to-HTTP check identified in the [plan progress report](./2026-09-29-plan-reporting-progress.md).
Use the existing paired native Worker and Django HTTP fixture with `{"model":"sonnet","plan_report":true}`.
The API fixture binds only to localhost port 8009 and starts with an isolated test database.
The native check starts the actual polling Worker in a separate process with a registered Worker token and a stored member session.
It uses authenticated Claude, the production private MCP app, the Host OS boundary, and the installed immutable Docker Code image.
The initial Run, repository binding, and local Git clone are fixtures.
No live GitHub connection, browser mention, or other Harness integration is claimed by this check.

## Verified flow

In Q&A turn 1, Claude reports a full plan with done, doing, and todo states and no estimate.
It reads the real clone through the checked Plane file tool.
It then reports an updated plan with the explicit estimate `About one minute` and completes its source-content answer.
The member plan endpoint returns this latest snapshot with turn number 1.
The clone content remains unchanged.

The member sends the implementation follow-up through the actual HTTP message endpoint.
The Worker performs the same-Run Code handoff in turn 2.
The plan endpoint returns a snapshot with done, doing, and todo states and the explicit estimate `About two minutes` before the file-write decision.
The member approves the exact file write and then the separate commit through the existing permission endpoints.
The production Docker executor changes the retained Worktree, and real Git creates the approved Run-branch commit.
After the commit, Claude reports all three steps done without an estimate.
The member plan endpoint returns this final turn-2 snapshot without retaining the earlier estimate.
The default branch and original clone content remain unchanged.

Plane stores exactly four plan events with turn numbers 1, 1, 2, and 2.
Each has a distinct stable `plan-` source key.
These events come from production MCP calls and real HTTP delivery, not direct fixture insertion.
Plan reporting adds no permission request or grant consumption.
The existing write and commit grant assertions pass.
The later turn-3 Stop check also passes without a second file change.
The Worker settles its records and releases its reservations before the acknowledged Stop.

The native side passes in 59.92 seconds.
The API side passes in 49.52 seconds.
Focused Ruff lint and formatting pass for both changed fixture files.

## Story 2.10 completion audit

| Acceptance criterion | Direct evidence |
| --- | --- |
| Show reported done, doing, and todo steps, progress, and only a reported estimate | Actual Claude-to-MCP-to-HTTP snapshots and latest member reads above; production browser states, progress, and optional estimate in the [plan report](./2026-09-29-plan-reporting-progress.md) |
| Keep disclosure choice and expose latest plan on reopen | Production browser Enter/Space, close/reopen, refresh persistence, and newer snapshot checks in the [plan report](./2026-09-29-plan-reporting-progress.md) |
| Show no empty section when no plan is reported | Production browser no-plan check and [no-plan screenshot](./plan-ui/no-plan-375.png) |

All three Story 2.10 acceptance criteria have direct evidence.
The latest-plan API also retains its bounded query and history checks, member access checks, and prior-turn retry receipts.
The first-page polling regression includes a real page reload and passes with the initial-cache fallback.
The other Harness integrations remain tracked in their own stories and the complete goal.

## Review

**Summary:** The full polling Worker delivers native plan snapshots through the production HTTP event path, and the member API returns the correct latest state.
**Critical issues:** None found in the new fixture mode or delivered plan flow.
**Major issues:** The remaining 41 stories and four-Harness goal still need their own acceptance evidence.
**Minor issues:** This check starts from a seeded Run and does not exercise GitHub authorization or browser mention creation.
**Positive feedback:** The check reuses the existing Worker, MCP, HTTP, permission, Docker, Git, and Stop paths and verifies stored plan counts and turn identities.
**Questions:** AD-7 and DNS decisions remain pending and are not assumed by this work.
**Verdict:** Mark Story 2.10 done and keep the complete goal active.

## Cleanup

The native Worker and API fixture exited successfully.
The isolated Compose containers, volumes, and network were removed.
No owned listener remains on ports 8009, 8769, or 8811.
The private fixture directory and temporary Compose override were removed.
No fixture token or member session is stored in this report or the checkout.
