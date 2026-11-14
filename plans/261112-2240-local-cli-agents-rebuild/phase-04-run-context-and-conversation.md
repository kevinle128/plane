---
phase: 4
title: "Run context and conversation"
status: todo
priority: P1
effort: "6.5d"
dependencies: [3]
---

# Phase 4: Run context and conversation

## Goal

The panel resizes and remembers width, shows the Agent's plan, asks for a repository when none is usable, lets the Agent read older authorized comments, and accepts follow-up replies in the same Run and clone. One PR, one commit per story 2.9-2.13.

<!-- 2026-11-14 --> Decisions Q31-Q35 ([plan.md](./plan.md#docker-sandboxes-decisions-2026-11-14)): Runs run in the Q&A sandbox of their (workspace, repository) key ([architecture-contracts.md §12](./architecture-contracts.md#12-docker-sandboxes-for-runs)). This phase adds the sandbox choice after a repository answer and the rebuild after a lost sandbox. Effort 6.5d (was 6d).

## Context links

- Stories: [epics.md:843-955](../2026-09-28-plane-local-cli-agents-epics/epics.md). Contracts: [architecture-contracts.md](./architecture-contracts.md) §3 (`AgentRunMessage`, `AgentRunQuestion`), §5 (`mcp_server.py`). Spine AD-2, AD-5, AD-6, AD-7, AD-9.
- Design: Screen 2 (resizable panel, plan block, elicitation row, input row); scenes 2 and 3.
- Prior lessons: [panel resize](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-panel-resize-and-polling.md), [plan HTTP](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-plan-http-acceptance.md), [Run repository](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-run-repository-acceptance.md), [older comments HTTP](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-older-comments-http-acceptance.md), [follow-up browser](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-follow-up-browser-acceptance.md), [question API](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-question-api-progress.md).

## Key decisions

- Panel width and Plan/Queue disclosure: `useLocalStorage` keyed `agent_run_panel:<user_id>` (per member, per browser). This meets 2.9 AC 2 without a server table. Clamp 380-960, default 540, keyboard step 16 px with Arrow keys on a `role="separator"` handle. Reuse the drag logic pattern from `apps/web/components/sidebar/resizable-sidebar.tsx:14-161`.
- Plan: drivers map native plan events (Claude `TodoWrite` tool input) to a `plan` event with steps and optional estimate. The panel shows the latest plan event. No plan event means no section.
- Repository elicitation: Run creation with no usable binding sets `awaiting` with an `AgentRunQuestion(kind=repository)`. Options come from the workspace catalog of attached accounts of both providers (GitHub and GitLab), grouped by provider with the provider icon. An answer records the neutral repository snapshot (`provider`, host, external ID, `clone_url`, `base_ref`) on the Run (<!-- 2026-11-14 --> no policy snapshot, Q36), then the Run returns to `created` for pickup. The Worker never clones before a confirmed choice; the clone uses the clone spec of the chosen provider (architecture-contracts §11). <!-- 2026-11-14 --> The chosen repository also selects the Q&A sandbox key, so the Run is cloned into that key's clones folder and runs in that sandbox (§12).
- Harness questions (elicitation rows, "Waiting for you" state): the Plane MCP tool `plane_ask_question` creates `AgentRunQuestion(kind=harness)` and sets `awaiting`. The answer is a panel reply bound to the question ID and is delivered as the next turn input. This supports FR9/FR11 elicitation and is reused by Omp UI-response in Phase 6. <!-- 2026-11-14 --> Kept by Q24 (the user rejected research item S5). The Plane MCP server reaches Claude through the generated config and the HTTP endpoint of Phase 3 (Q24, Q31). Claude's own `AskUserQuestion` tool is turned off for Runs (`--disallowedTools AskUserQuestion`), so a question always goes through `plane_ask_question`; `[UNVERIFIED]` how `AskUserQuestion` behaves in `-p` stream-JSON mode, the Phase 4 fake and native tests confirm that a Claude question becomes a question card.
- Older comments: MCP tool `plane_issue_comments(before_id, limit)` calls a Worker API route that checks the Run lease and returns only comments of the Run's issue visible to the requester, with ID, author and time.
- Follow-up: a reply on an idle Run stores `AgentRunMessage(state=queued)` and creates the next turn. The Worker resumes the native session when valid, else rebuilds from the snapshot, same-Run messages, decisions and an issue delta (changes since the last turn). Same clone path; never a new clone. <!-- 2026-11-14 --> The native session lives inside the sandbox (Q35). When the sandbox was removed or recreated since the last turn (limit, missing, import change), `--resume` fails and the Worker uses the rebuild path; the clone on the host stays, so the clone path and inode are the same.

## Files

Create (backend): `apps/api/plane/agent/services/{messages,questions,context_delta}.py`; migration `<next>_agent_run_messages_questions` (generated); tests `test_agent_run_followup.py`, `test_agent_run_question.py`, `test_agent_older_comments.py`, `test_agent_run_repository_choice.py`.

Modify (backend): `apps/api/plane/agent/services/run_creation.py` (awaiting repository), `apps/api/plane/agent/services/context_snapshot.py` (omission count, delta), `apps/api/plane/app/views/agent/runs.py`, `apps/api/plane/agent/worker_api/views.py`.

Create (Worker): extend `plane_agent_worker/mcp_server.py` (`plane_ask_question`, `plane_issue_comments`), `drivers/claude.py` (plan mapping, resume); tests `tests/test_mcp_tools.py`, `tests/test_followup_turn.py`, `tests/test_plan_mapping.py`.

Create (web): `packages/blocks/src/agent-run/{panel-width.ts,plan-progress.ts,plan-section.tsx,question-row.tsx}` with tests; `apps/web/components/agent-run/{resize-handle,plan-block,question-card,composer}.tsx`.

Modify (web): `apps/web/components/agent-run/panel-root.tsx`, `apps/web/components/agent-run/timeline.tsx`, `apps/web/store/agent/run.store.ts`, `apps/web/services/agent/run.service.ts`, `packages/i18n/src/locales/*/agent.json`.

## API endpoints

| Path                                                          | Auth                 | Story                   |
| ------------------------------------------------------------- | -------------------- | ----------------------- |
| `POST .../agent-runs/<id>/messages/` (idempotency key)        | comment permission   | 2.13                    |
| `POST .../agent-runs/<id>/questions/<qid>/answer/`            | comment permission   | 2.11, harness questions |
| `GET .../agent-runs/<id>/repository-options/`                 | comment permission   | 2.11                    |
| `GET api/agent-worker/v1/runs/<id>/comments/?before=&limit=`  | Worker token + lease | 2.12                    |
| `POST api/agent-worker/v1/runs/<id>/questions/`               | Worker token + lease | harness questions       |
| `POST api/agent-worker/v1/runs/<id>/messages/<mid>/accepted/` | Worker token + lease | 2.13                    |

## Tests Before

1. Phase 3 timeline and claim tests pass unchanged.
2. Run creation for a bound project stays `created` (no question).

## Refactor

Protected by Tests Before 1-2: `run_creation.py` gains the awaiting-repository branch only for Runs without a usable binding; `context_snapshot.py` gains the omission count and delta builder with the v1 payload fields unchanged.

## Story steps and Tests After

| Story | Steps                                                                    | Tests After                                                                                                                                                                                                                                                                                                                                                                       |
| ----- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2.9   | Resize handle, clamp, persist per user                                   | Blocks vitest: clamp, keyboard step, default, key per user ID; browser: drag and keyboard, reload, second user keeps own width                                                                                                                                                                                                                                                    |
| 2.10  | Plan event mapping, plan section, disclosure                             | Worker: fake Claude `TodoWrite` maps to plan with and without estimate; blocks vitest: progress count, done/doing/todo, estimate only when present, absent plan renders nothing                                                                                                                                                                                                   |
| 2.11  | Awaiting repository question, options, answer, revoked grant handling    | API: no binding sets awaiting and no claim is possible; answer records repository with provider; options include GitHub and GitLab rows and exclude candidate or detached accounts; choosing a GitLab repository records provider `gitlab`; revoked grant keeps awaiting with hint; Worker: clone uses chosen remote, credential mode and CWD; <!-- 2026-11-14 --> the Run runs in the sandbox of the chosen key and a GitLab choice does not reuse a GitHub key's sandbox; browser: scene 3 keyboard choice |
| 2.12  | Omission count, MCP comment tool, authorized page route                  | API: exact omission count; page ordered with stable IDs; other issue, other workspace and private panel messages absent; expired lease 409                                                                                                                                                                                                                                        |
| 2.13  | Reply stores message, next turn, delta context, native resume or rebuild | API: reply after completed turn creates turn 2 in same Run; delta includes changed title and new comments, excludes other Runs; Worker: same clone path and inode; process exit between turns rebuilds context; <!-- 2026-11-14 --> a sandbox recreated between turns (fake `sbx` reports exit 125 at the health check) rebuilds context in the new sandbox with the same clone path; native: a follow-up in the same sandbox resumes the session; browser: two turns in order after reopen                                                                                                                          |

## Verification

```bash
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app -k "agent_run or agent_older_comments"
docker compose -f docker-compose-test.yml run --rm api-tests python manage.py makemigrations --check --dry-run
cd apps/api && uv run ruff check .
cd apps/agent-worker && uv run pytest -m "not native and not docker"
pnpm --filter=@plane/blocks test && pnpm turbo run check:types --filter=web --filter=@plane/blocks
pnpm check:lint && pnpm --filter=@plane/i18n check:sync
```

## Success criteria

- [ ] All Given/When/Then cases of 2.9-2.13 pass.
- [ ] Mockup rows I018, I023, I024, I032, I033, I034 pass browser review.
- [ ] A native Claude turn on the Mini calls `plane_issue_comments` and receives only authorized comments.

## Risks

| Risk                                                 | L x I           | Mitigation                                                                                 |
| ---------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------ |
| Claude has no estimate in plan events                | High x Low      | Estimate is optional by design (UX-DR6)                                                    |
| Native session resume ID is invalid after CLI update or sandbox removal (Q35) | Medium x Medium | Fallback rebuild from durable context is always available and tested                       |
| MCP tool bypasses requester access                   | Low x High      | Route checks requester visibility, not Worker rights; contract test with a guest requester |

## Rollback

Revert the PR and migrate `db` back to the Phase 3 migration. Runs created during the phase keep events; messages and questions tables drop with the migration, so back up first.
