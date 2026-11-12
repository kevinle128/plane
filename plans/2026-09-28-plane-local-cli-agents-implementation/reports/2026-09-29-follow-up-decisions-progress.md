# Follow-up decision context progress

## Requirement and reproduction

Story 2.13 and PRD FR-22 require prior messages and decisions from the same Run in each follow-up.
The endpoint returned current issue details, prior turns, messages, and comments, but omitted permission decisions.
The new contract claims a follow-up through the actual Worker API and reads its context.
Before the repair, the valid HTTP 200 response fails on missing `prior_decisions`.
The check uses stored event fixtures rather than native permission approvals.

The first fixture attempt collided with the real claim event sequence.
Correct that fixture before reproducing the missing field.
The first repaired check also expected HTTP 409 for invalid generation 0, which correctly returns HTTP 400.
Use a valid mismatched generation to test the lease fence.

## Shared endpoint repair

Read immutable `permission_decided` events from earlier turns of the leased Run through the existing Run, kind, and sequence index.
Select at most the latest 50 candidates and return included summaries in chronological order.
Retain permission identity, turn, action, scope, effect hash, decision, actor, and time.
Exclude raw effect content.
Bound the decision list to 64 KB of UTF-8 JSON, including separators.
Skip summaries that do not fit and report the excluded count in `omitted.decisions`.
Historical decisions grant no new effect permission.
The Worker already serializes the complete matching context; its prompt check now verifies this decision history and the existing no-permission task boundary.

## Checks

- All 17 lease and lifecycle API checks pass in 5.12 seconds.
- The final focused check passes in 1.32 seconds with another Run's private sentinel in a field that would otherwise be included.
- It verifies ordered latest-50 history, omitted count, exclusion of current-turn decisions, and same-issue Run isolation.
- A 66 KB Unicode scope verifies the byte bound and omission accounting.
- The current lease succeeds and a valid mismatched generation returns HTTP 409.
- All ten Worker driver and control checks pass in 1.05 seconds.
- Focused Ruff lint and formatting pass for the endpoint and both test files.

## Remaining work

Keep Story 2.13 in progress.
Complete an idle panel follow-up with changed issue content and comments through native prompt reconstruction.
Verify the new decision history reaches the native Harness, the clone remains the same after its prior process exits, and both conclusions remain ordered on one card after reopening.

## Review

**Summary:** Follow-up context now includes bounded historical decisions from its own Run.
**Critical issues:** None found in the changed read.
**Major issues:** Full native and browser Story 2.13 evidence remains required.
**Minor issues:** The API test seeds decision events instead of creating them through approval endpoints.
**Positive feedback:** Reuse ordered audit records and their index without a migration or new service.
**Questions:** AD-7 and DNS decisions remain pending and are not assumed.
**Verdict:** Keep Story 2.13 in progress.

## Cleanup

The API test processes exit.
Remove the owned `plane-context` Compose project, network, and temporary override.
No browser, native Worker, or listener is started.
