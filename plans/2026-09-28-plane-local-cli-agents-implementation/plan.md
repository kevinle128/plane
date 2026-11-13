---
title: "Plane Local CLI Agents implementation"
description: "Deliver and verify all 43 stories across the three approved epics."
status: in-progress
priority: P1
effort: ""
tags: []
created: 2026-09-28
---

# Plane Local CLI Agents implementation

## Outcome and authority

Deliver all 43 stories in the [epic breakdown](../2026-09-28-plane-local-cli-agents-epics/epics.md) and track them in [sprint status](../../_bmad-output/implementation-artifacts/sprint-status.yaml).
The [PRD](../2026-09-27-local-cli-agents-prd/prd.md), [Architecture Spine](../2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md), and [design handoff](../../claude-design/design_handoff_local_cli_agents/README.md) govern v1 when the older SPEC or prototype differs.

## Constraints

- Deliver Plane CE and one local Worker on the Mac Mini with all four Harnesses.
- Keep Plane as the Run state and permission authority.
- Give each Run a fresh clone and each Code job a bounded Worktree.
- Require a matching grant before each protected effect.
- Keep the Agent away from the Plane checkout and default-branch merge.
- Match the approved UI with semantic tokens, keyboard access, and responsive behavior.
- Build a long-term, maintainable, and scalable solution: use explicit Plane API and Worker contracts, durable indexed Run state, idempotent effects, bounded resource use, and versioned Harness adapters.
- Make scaling claims with load, concurrency, recovery, and migration evidence; do not rely on a single-worker happy path.

## Non-goals

- Plane Enterprise Agents, an in-app LLM, ACP, public Worker callbacks, or automated merges.

## Phases

| Phase | Scope | Depends on | Status |
| --- | --- | --- | --- |
| [1. GitHub and repository](./phase-01-github-and-repository.md) | Epic 1, stories 1.1–1.8 | None | In progress |
| [2. Run control plane and UI](./phase-02-run-control-plane-and-ui.md) | Epic 2 shared Run behavior and UI | Phase 1 repository contract | In progress |
| [3. Four-harness Worker](./phase-03-four-harness-worker.md) | Epic 2 execution and driver conformance | Phase 2 Run contract | In progress |
| [4. Code jobs and draft PR](./phase-04-code-jobs-and-draft-pr.md) | Epic 3, stories 3.1–3.9 | Phases 1–3 | In progress |

## Completion criteria

- [ ] Every story meets every acceptance criterion in the epic breakdown with direct test or runtime evidence.
- [ ] The 65 changed prototype items have production coverage and visual checks across the 12 design scenes.
- [ ] API, Worker, web, migration, isolation, and four-Harness conformance checks pass.
- [ ] Run event pagination, concurrent claims, queue order, Docker slot limits, and restart recovery pass realistic load and concurrency checks.
- [ ] Relevant lint, type, build, and integration gates pass without hidden failures.
- [ ] Sprint status matches verified story and epic state.
- [ ] Setup and operating documentation describes the delivered behavior.

## Current acceptance audit

The [43-story audit](./reports/2026-09-28-story-acceptance-audit.md) lists current evidence and remaining acceptance work for every story.
The restored, manifest-verified sprint generator now records Stories 1.6, 1.7, 1.8, 2.2, 2.3, 2.4, 2.5, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13, 2.14, 2.16, 2.17, 2.18, 2.19, 2.20, 3.2, 3.3, 3.7, and 3.8 as `done`, with all three epics and the other 20 stories still `in-progress`.
The [panel acceptance report](./reports/2026-09-29-panel-resize-and-polling.md) proves pointer and keyboard resize, persistence, member isolation, and visible controls for both Story 2.9 criteria.
No other story is marked `review` or `done` before all its acceptance criteria have direct evidence.
The [plan reporting report](./reports/2026-09-29-plan-reporting-progress.md) adds a bounded shared MCP producer, native reported estimates, plan turn fencing, browser disclosure checks, and the completed fresh-page polling repair.
The [native HTTP plan acceptance report](./reports/2026-09-29-plan-http-acceptance.md) completes Story 2.10 with actual polling Worker delivery and latest member API reads across Q&A and Code turns.
The [Run repository acceptance report](./reports/2026-09-29-run-repository-acceptance.md) completes Story 2.11 with keyboard selection across 101 candidates, actual selected remote clone, native Claude CWD and README proof, and grant revocation before preparation without a clone or Harness.
The [Queue UI report](./reports/2026-09-29-queue-ui-progress.md) adds real API submission, disclosure persistence, keyboard actions, composer mode changes, and 375 px layout checks for Story 2.14.
The [Queue HTTP acceptance report](./reports/2026-09-29-queue-http-acceptance.md) completes Story 2.14 with actual native ordered delivery and Worker restart after and before result persistence.
The [Send now native report](./reports/2026-09-29-send-now-native-progress.md) records the reproduced selected-message cancellation defect, shared control repair, actual process shutdown, acknowledgment ordering, and native selected-then-FIFO completion.
The [Send now timeout report](./reports/2026-09-29-send-now-timeout-progress.md) verifies an actionable fenced error without a terminal result or competing turn when a declared stop fault leaves a process record unresolved.
The [Send now browser report](./reports/2026-09-29-send-now-browser-progress.md) verifies keyboard selection, pending/error/dispatching states after reload, no early acknowledgment, selected-then-FIFO conclusions and unchanged historical events.
Story 2.15 remains in progress for the other required Harness conformance.
The [Queue removal report](./reports/2026-09-29-queue-removal-acceptance.md) completes Story 2.16 with native cancellation before dispatch, conflicts after dispatch and acceptance, and retained audit after browser refresh.
The [follow-up context report](./reports/2026-09-29-follow-up-decisions-progress.md) adds bounded same-Run decision history and identifies the remaining native and browser acceptance for Story 2.13.
The [native follow-up report](./reports/2026-09-29-follow-up-http-progress.md) proves changed issue and comment context, ordered same-Run messages and decisions, clone retention, and private-history exclusion across native CLI process exits.
The [browser follow-up acceptance](./reports/2026-09-29-follow-up-browser-acceptance.md) completes Story 2.13 with a production panel reply delivered by the native Worker and ordered conclusions after reopening and full browser reload.
The [older-comments progress report](./reports/2026-09-29-older-comments-progress.md) adds bounded requester-authorized Worker endpoints, shared Q&A and Code MCP tools, and a native Claude retrieval check.
The [older-comments HTTP acceptance report](./reports/2026-09-29-older-comments-http-acceptance.md) completes Story 2.12 with actual polling Worker retrieval, stable pages, remaining Unicode text, and forbidden issue, workspace, and private panel checks.
The [instruction acceptance report](./reports/2026-09-29-agent-instructions-acceptance.md) completes Story 2.4 with real settings persistence, historical snapshot checks, and policy/task separation.
The shared settings edit-during-Save data loss case was reproduced with a delayed actual API response and repaired with a native disabled fieldset.
Success and validation-error browser checks confirm that editing resumes and a rejected draft remains intact.
The [name and handle acceptance report](./reports/2026-09-29-agent-name-and-handle-acceptance.md) completes Stories 2.2 and 2.3 with settings validation, repaired Integrations name display, mention picker updates, and stable historical Run and comment identity.
The [Mentionable acceptance report](./reports/2026-09-29-agent-mentionable-acceptance.md) completes Story 2.5 with real settings toggles and picker reasons, atomic rejection of new mentions, and retained active Run access and exact audit history.
The [stale failure acceptance report](./reports/2026-09-29-stale-failure-acceptance.md) completes Story 2.20 with actual browser confirmation, named and isolated modal controls, retained native Git clone and history, native HTTP late event and result rejection, and comment permission checks.
The [stale retry acceptance report](./reports/2026-09-29-stale-retry-acceptance.md) completes Story 2.19 with exact five-minute lease timing, actual browser Retry pickup and unavailable Worker reload, native process reconciliation, actual polling Worker and Claude accepted-turn recovery, and protected effect recovery without replay.
The [Stop acceptance report](./reports/2026-09-29-stop-acceptance.md) completes Story 2.17 with actual browser confirmation/cancellation and reload, retained native Git clone, recorded Stop identity/time and discarded/interrupted counts, comment permission rejection, and polling Worker/Claude interruption with protected action boundaries.
The [stopped clone resume report](./reports/2026-09-29-stopped-clone-resume-progress.md) records an actual polling Worker reproduction and repair of replacement clone creation after Stop.
The [stopped repository recovery report](./reports/2026-09-29-stopped-recovery-progress.md) verifies durable recoverable errors, fenced member Retry, original clone restoration, and original-task continuity with later queued messages.
The [stopped resume acceptance report](./reports/2026-09-29-stopped-resume-acceptance.md) completes Story 2.18 with production browser stopped reply, recoverable error, keyboard Retry, pending reload, and retained history after clone restoration and panel reopen.
Nested sidebar drag buttons are repaired using the existing single-control pattern.
The [page control progress report](./reports/2026-09-29-page-controls-progress.md) records the repaired property display and project menu nested buttons.
The [dropdown keyboard progress report](./reports/2026-09-29-dropdown-keyboard-progress.md) proves selected state, priority, calendar, and default-open date-filter flows with real options and ARIA checks.
The [menu and narrow layout report](./reports/2026-09-29-menu-and-narrow-layout-progress.md) proves native menu callbacks, submenu keyboard selection, and repaired 375 px sidebar geometry and focus.
The [breadcrumb and reaction report](./reports/2026-09-29-breadcrumb-and-reaction-progress.md) proves zero nested native buttons on the real work item, separate breadcrumb navigation and selection, and real reaction creation and removal across reload.
The [stopped banner report](./reports/2026-09-29-stopped-banner-progress.md) adds the latest acknowledged member/time summary, exact browser timestamp checks and long-history API coverage.
The [timeline group and cursor report](./reports/2026-09-29-timeline-groups-and-cursors.md) proves additive history, a 65-event live burst without loss or duplicates, native keyboard groups, completion duration and retained details after reload.
The [historical plan and long timeline report](./reports/2026-09-29-historical-plan-and-long-timeline.md) proves 1,002 ordered events, immutable plan states and estimates, keyboard step-list access, and full long Unicode detail.
The [native tool result report](./reports/2026-09-29-native-tool-results-progress.md) records the reproduced lost-result defect, complete native result chunks and call identities, additive API and recovery support, and actual polling Worker delivery and member reads after Harness exit.
The [tool result browser report](./reports/2026-09-29-tool-result-browser-acceptance.md) verifies exact multi-part content across cursors and reload, keyboard detail and scrolling, honest partial history, correct action counts, and repaired error icon and label in Light and Dark.
The [timeline detail report](./reports/2026-09-29-timeline-details-progress.md) repairs long input action counts and verifies complete parameters, safe Markdown, requester identity, reduced motion, completion and reload.
The [timeline failure report](./reports/2026-09-29-timeline-error-progress.md) adds actual subprocess exit metadata and a recorded recovery hint, with fenced API and browser evidence.
The [panel and peek keyboard report](./reports/2026-09-29-panel-peek-keyboard-progress.md) repairs lost peek ownership on panel and modal clicks, independent Escape dismissal and focus return, and the nested mobile layout control.
The [title and comment menu report](./reports/2026-09-29-title-and-comment-menu.md) proves title resizing at 320–1280 px and repairs the observed nested comment trigger with real keyboard, ARIA, focus, and reload checks.
The [fetch cancellation report](./reports/2026-09-29-issue-fetch-cancellation-progress.md) resolves the earlier undefined browser rejection and verifies current loader and response ownership across seven stores.
The [question history report](./reports/2026-09-29-question-history-progress.md) repairs expanded warning-card presentation and verifies safe Markdown, Unicode, narrow layout, and retained question history after reload.
The [question API report](./reports/2026-09-29-question-api-progress.md) adds indexed durable questions, exact answer binding, deferred acknowledgement, lease recovery, and permission and queue fencing, with 144 passing API checks.
Native question delivery and the question-bound composer remain required for complete elicitation acceptance.
The [question Worker report](./reports/2026-09-29-question-worker-progress.md) adds the shared MCP tool, exact native Claude delivery matching, deferred acceptance, and pending and answered recovery context.
The [question composer report](./reports/2026-09-29-question-composer-progress.md) verifies bound choices and free text, retained drafts, queued, dispatching, and interrupted reload, deferred acceptance, history, and narrow layout with the production browser and API.
The [native question HTTP report](./reports/2026-09-29-question-http-progress.md) verifies actual polling Worker and Claude answers, persistence before acknowledgment, recovery before and after native delivery, retained question and clone identity, and Stop while waiting.
The [native Code question report](./reports/2026-09-29-question-code-progress.md) records the reproduced handler initialization defect and repair, exact Unicode receipt retention before acknowledgment, and separate protected write and commit approval through Docker and Git.
The [Code question control report](./reports/2026-09-29-question-code-control-progress.md) verifies native waiting Stop and restart, repairs FIFO slot admission for a pending question, and preserves the original task in recovery after answer acceptance.
The [answer acceptance recovery report](./reports/2026-09-29-question-acceptance-recovery-progress.md) verifies native Q&A recovery after committed acceptance and Code recovery before and after committed acceptance.
Other Harness question mappings and the remaining whole-story criteria still require acceptance evidence.
The [Run status report](./reports/2026-09-29-run-status-progress.md) verifies all eight handoff states in Light and Dark, accessible status announcements, keyboard focus return, and repairs missing Code sandbox metadata and the waiting icon.
The [permission and PR scene report](./reports/2026-09-29-permission-and-pr-scenes-progress.md) verifies real member decisions and retained history, repairs keyboard access to full permission content, and proves confirmed PR presentation and semantic theme changes.
The [durable timeline acceptance audit](./reports/2026-09-29-durable-timeline-acceptance.md) completes Story 2.8 against all nine criteria with named keyboard scroll regions, actual accessibility-tree checks, a fresh cursor burst and completion/reload gate, and read-only quality review.
The [Run grant acceptance report](./reports/2026-09-29-run-grant-acceptance.md) completes Story 3.2 with two actual matching Docker writes, separate request-linked audit, broader-path rejection, and cross-Run and network scope contracts.
The [denied effect acceptance report](./reports/2026-09-29-denied-effect-acceptance.md) completes Story 3.3 with actual native denial receipt, unchanged file content, separate changed-effect permission, durable audit, and native OS/Docker boundary checks.
The [branch format acceptance report](./reports/2026-09-29-branch-format-acceptance.md) completes Story 1.8 with both persisted browser choices, distinct same-issue Run branch reservations, policy-change retention, and actual Git Worktrees for both formats.
The [Code Stop acceptance report](./reports/2026-09-29-code-stop-acceptance.md) completes Story 3.7 with active native Harness and Docker interruption, actual queue cancellation, retained Worktree/branch/history/PR, and verified slot transfer to a waiting Code container at capacity one.
The [Code resume acceptance report](./reports/2026-09-29-code-resume-progress.md) completes Story 3.8 with a new native Harness in the original Worktree, fresh slot acquisition, actual durable context delivery, and a separately approved Docker write after Stop.
Missing Worktree, changed remote, and revoked grant checks now pass without a Harness or new slot; actual browser errors, keyboard Retry, reload, and 375 px checks pass after two recovery UI repairs.
The actual stopped panel reply now reaches the native Worker and completes through polling; a reproduced terminal-to-active polling defect is repaired and a fresh complete browser-to-native run passes with retained completion after reload.
Full dropdown-flow coverage and default-open focus still require acceptance work.
Bounded command execution now passes native Claude and normal paired HTTP checks through the existing permission and Docker contracts.
Paired command restart recovery now passes before and after result persistence without replay.
The [path boundary report](./reports/2026-09-28-path-access-progress.md) now has native descriptor evidence and records why a direct host bind cannot rely on inode equality on Docker Desktop.
Exact scoped file reads now have matching Plane/Worker contracts and retained preparation and output before acknowledgement.
Historical read reporting and native restart settlement now pass without reopening the external file.
Code MCP routing now passes bounded read, Deny, Stop, uncertain receipt, and native Claude checks.
The normal read and both paired HTTP restart modes now pass with the external file deleted and historical acknowledgement before capacity release.
Native Claude hard-link escape testing exposed an unapproved read through the Worktree.
The shared OS boundary now blocks direct Run-file data reads, and bounded Worker tools provide repository read, list, and search with current authority and pinned descriptors.
Actual native probes pass for repository access and blocked external, symbolic-link, and hard-link reads.
The [path boundary report](./reports/2026-09-28-path-access-progress.md#native-hard-link-read-escape-and-repository-reader) tracks the complete rerun and HTTP recovery checks.
The member accepted Docker content production with trusted Worker publication through pinned Host descriptors; AD-8 records this explicit exception.
Exact additional-file write proposals and historical result reporting now pass the permission and lease contract checks.
The internal Host publication primitive now passes native atomic replacement and process-death checks with pinned target and parent descriptors.
Exact additional-file writes now use Docker content production, durable registry preparation and results, receipt-gated recovery without target replay, and the Code MCP route.
Native Claude Allow/Deny, process-death journal boundaries, and Docker recovery checks pass.
Paired HTTP normal writes and both result-loss restart modes now pass without target replay, including a deleted target and a later human target edit.
The shared task frame now lets the current member request propose Code and added-path work while keeping every effect behind its separate Plane grant.
Exact new-file writes now have a create-only effect, atomic publication without replacement, native Claude Allow/Deny, Docker recovery, and process-death evidence.
Paired HTTP creation and both result-loss restart modes now pass without target replay and with an absent target before approval.
The existing-file API effect and journal contract remain valid; creation requires its own explicit flag and displayed command.
Complete path product flows, network destination enforcement, the complete read conformance audit, and four-Harness permission conformance remain required.

The [network report](./reports/2026-09-29-network-boundary-progress.md#native-process-death-during-namespace-creation) now verifies native creation-process death at four Docker namespace boundaries, receipt-gated cleanup, replay rejection, and preservation of later source edits.
The [latest network evidence](../reports/test-260929-1847-network-namespace-recovery.md) now proves full polling Worker death after bridge creation and HTTP Code MCP rejection of revoked repository authority.
The other three polling namespace checkpoints, full polling revocation, DNS, visual flows, and other Harnesses remain required.
Claude reported a session limit before the controller-checkpoint retry could reach Code; no passing result is claimed for that retry.

<!-- slug: plane-local-cli-agents-implementation -->

The [GitHub PR policy acceptance report](./reports/2026-09-29-github-pr-policy-acceptance.md) completes Stories 1.6 and 1.7 with browser defaults, keyboard persistence, member read-only controls, API rejection, and actual delivery consumer policy checks.
The repaired exact GitHub route and disabled checked switch pass the final browser gate.
Live GitHub publication remains in its owning stories.
