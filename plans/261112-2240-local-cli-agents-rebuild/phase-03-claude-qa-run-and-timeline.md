---
phase: 3
title: "Claude Q&A Run and durable timeline"
status: todo
priority: P1
effort: "8d"
dependencies: [1, 2]
---

# Phase 3: Claude Q&A Run and durable timeline

## Goal

A member mentions Claude in a work-item comment. Plane commits the comment and a Run together. The Worker clones the bound repository into a fresh Run-ID CWD, runs Claude read-only, streams events, and posts one conclusion. The member opens a durable timeline panel. One PR, commits for 2.7 and 2.8, plus the Run-level checks deferred from 2.2-2.5.

## Context links

- Stories: [epics.md:743-841](../2026-09-28-plane-local-cli-agents-epics/epics.md). Contracts: [architecture-contracts.md](./architecture-contracts.md) §3 (`AgentRun`, snapshot, turn, event), §4, §5, §6. Spine AD-1, AD-2, AD-3, AD-6, AD-7, AD-10.
- Design: Screen 1 (Run card, status table, mention composer) and Screen 2 (panel header, timeline rows); scenes 1, 2, 4, 7.
- Prior lessons: [durable timeline acceptance](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-durable-timeline-acceptance.md), [timeline groups and cursors](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-timeline-groups-and-cursors.md), [native tool results](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-native-tool-results-progress.md), [Run status](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-run-status-progress.md), [panel and peek keyboard](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-panel-peek-keyboard-progress.md).

## Data flow

1. Browser saves a comment with `<mention-component entity_name="agent_mention" entity_identifier="<agent id>">`.
2. `IssueCommentViewSet.create` (`comment.py:94`) saves the comment and its Runs inside one `transaction.atomic` block: parse agent mentions, check each Agent is connected and Mentionable, create one `AgentRun` per distinct Agent with snapshots (model, instructions, repository binding, branch format), build `AgentRunContextSnapshot` v1. The existing comment permission check (`comment.py:103-118`) runs first. Both existing `.delay` calls stay after the block, as today.
3. If an Agent is not connected or not Mentionable, the whole request fails with 400 and names the Agent (no comment, no Run). Edits through `partial_update` (`comment.py:148`) never create Runs (FR8 says each new comment).
4. Worker polls `runs/claim/` (filtered by connected harness), receives lease generation and expiry, and the snapshot.
5. Worker verifies remote and path, clones to `<run_root>/<run_id>/clone`, reports `clone_path`, starts Claude under `qa-readonly.sb` with CWD = clone, and the Plane MCP server (empty tool list in this phase except `plane_issue_context`).
6. Worker maps Claude events to Run events with `source_key` and posts batches with `lease_generation`. Plane assigns `seq`, rejects old generations (409) and duplicate `source_key` (returns the existing event).
7. Terminal result: Plane writes one conclusion `IssueComment` by the Agent bot user, links it to the Run, and sets `completed` or `failed`.
8. Browser polls `runs/<id>/events/?after=<seq>` every 2 s while active and reconciles by event ID. Activity shows the Run card and its conclusion; the standalone conclusion comment is not rendered twice.

## Key decisions

- Mention kind `agent_mention`: add to `TSearchEntities` (`packages/types/src/search.ts:15`), backend `SearchEndpoint` (`plane/app/views/search/base.py:334-402`), `useAdditionalEditorMention` (`apps/web/hooks/use-additional-editor-mention.tsx:51`), and the mention node renderer `apps/web/components/editor/embeds/mentions/root.tsx`. Add `disabled` and `disabledReason` to `TMentionSuggestion` (`packages/editor/src/types/mention.ts:10-17`) and honor them in `mentions-list-dropdown.tsx`.
- `process_mention` (`plane/bgtasks/email_notification_task.py:130-138`) filters `entity_name="user_mention"` so an agent ID is never looked up as a user.
- Stale is derived: `status in (in_progress, awaiting, approval)` and `lease_expires_at < now` reads as `stale` with `last_progress_at`. Lease length 5 min, renewed by heartbeat.
- Run card: one per Run, positioned by `created_at` inside `activity-comment-root.tsx`. Panel: one portal-mounted drawer opened from the full page and from peek. Escape closes the panel first, then peek (prior lesson).
- Q&A boundary: profile denies writes everywhere except the CLI's own temp dir policy decided for Claude in Phase 2, denies reads of other Runs and of the Worker token. Add a hard-link probe; if it reads foreign content, stop and take decision Q7.
- Context envelope (FR20-FR23): workspace, project, issue identifier and link, title, description, state, repository, requester, trigger comment, earlier visible comments in order with ID, author and time; member content is fenced as task data below Agent instructions; a byte budget with an exact omission count (retrieval tool arrives in Phase 4).
- Tool results split into chunks with call ID and part index; the store joins them (prior lesson).

## Files

Create (backend): `apps/api/plane/agent/services/{run_creation,context_snapshot,lease,run_events,conclusion}.py`; `apps/api/plane/app/views/agent/runs.py`; Worker API views for claim, renew, events, result (extend `plane/agent/worker_api/views.py`); migration `<next>_agent_run` (generated); tests `apps/api/plane/tests/contract/app/test_agent_run_creation.py`, `test_agent_run_context.py`, `test_agent_worker_lease.py`, `test_agent_run_events.py`, `test_agent_conclusion.py`, `apps/api/plane/tests/unit/test_agent_mention_parsing.py`, `test_email_mention_filter.py`.

Modify (backend): `apps/api/plane/app/views/issue/comment.py:94-145`, `apps/api/plane/bgtasks/email_notification_task.py:130-138`, `apps/api/plane/app/views/search/base.py:329-402`, `apps/api/plane/app/urls/agent.py`, `apps/api/plane/db/models/agent.py`.

Create (Worker): `plane_agent_worker/{workspace,prompt,mcp_server,events}.py`; extend `drivers/claude.py` and `loop.py`; tests `tests/test_workspace_clone.py`, `tests/test_prompt.py`, `tests/test_claude_turn.py`, `tests/test_event_mapping.py`, `tests/test_qa_boundary.py` (native).

Create (web): `packages/blocks/src/agent-run/{status-meta.ts,timeline-reconcile.ts,timeline-group.ts,run-status-badge.tsx,timeline-rows.tsx}` with tests; `apps/web/services/agent/run.service.ts`; `apps/web/store/agent/run.store.ts`; `apps/web/hooks/store/use-agent-run.ts`; `apps/web/components/agent-run/{run-card,panel-root,panel-header,timeline,composer-shell}.tsx`; `apps/web/components/issues/issue-detail/issue-activity/agent-run-card-row.tsx`.

Modify (web): `packages/types/src/search.ts:15`, `packages/editor/src/types/mention.ts`, `packages/editor/src/extensions/mentions/mentions-list-dropdown.tsx`, `apps/web/hooks/use-additional-editor-mention.tsx`, `apps/web/components/editor/embeds/mentions/root.tsx`, `apps/web/components/issues/issue-detail/issue-activity/activity-comment-root.tsx`, `apps/web/components/issues/issue-detail/issue-activity/root.tsx`, `apps/web/store/root.store.ts`.

## API endpoints

| Path | Auth | Story |
| --- | --- | --- |
| `GET api/workspaces/<slug>/projects/<pid>/issues/<iid>/agent-runs/` | issue reader | 2.7, 2.8 |
| `GET .../agent-runs/<run_id>/`, `GET .../agent-runs/<run_id>/events/?after=&limit=` | issue reader | 2.8 |
| `GET api/workspaces/<slug>/entity-search/?query_type=agent_mention` | member | 2.7 |
| `POST api/agent-worker/v1/runs/claim/`, `.../runs/<id>/renew/`, `.../runs/<id>/clone/`, `.../runs/<id>/events/`, `.../runs/<id>/result/`, `GET .../runs/<id>/context/` | Worker token + lease | 2.7 |

## Tests Before

1. Comment create without agent mentions: same response body and the same two `.delay` calls (patch `issue_activity.delay` and `model_activity.delay` with `mocker`).
2. `process_mention` keeps rendering user mentions in email HTML.
3. Entity search `user_mention` unchanged (`test_entity_search_project_members_app.py`).
4. `packages/editor` vitest passes before the type change.

## Refactor

Protected by Tests Before 1-4: put the comment save and Run creation of `IssueCommentViewSet.create` (`comment.py:94-145`) in one `transaction.atomic` block and keep both `.delay` calls after it; add the `entity_name` filter in `process_mention` (`email_notification_task.py:130-138`); add an `agent_mention` branch in `SearchEndpoint` without changing `user_mention`; add optional `disabled`/`disabledReason` to `TMentionSuggestion`; insert Run cards into the merged list in `activity-comment-root.tsx` without changing comment or activity order.

## Story steps and Tests After

| Story | Steps | Tests After |
| --- | --- | --- |
| 2.7 | Mention search and picker reasons; atomic Run creation; snapshot; claim and lease; fresh clone; read-only Claude turn; event append with idempotency; conclusion comment; concurrent Runs; failure on auth or boundary denial | API: comment+Run commit together (forced failure after comment rolls back both); issue activity/history endpoint returns the bot-authored conclusion comment although the bot is not a project member; two agents in one comment create two Runs; disconnected/non-Mentionable 400; guest without comment right 400; snapshot contains exact IDs and excludes other issues and other Runs' panel messages; repeated event `source_key` creates one event; old generation 409; duplicate result creates one conclusion; Worker: clone path from Run ID outside checkout, remote mismatch refuses launch, fake Claude turn maps events, auth failure produces failed result and no write; native: write in and outside clone denied, hard-link and other-Run read denied, two concurrent Runs have different CWDs |
| 2.7 (deferred settings checks) | Run snapshots of name, handle, instructions, model, Mentionable | API: rename/handle change keeps Run agent ID and events; new instructions affect only new Runs; disabling Mentionable keeps active Run readable |
| 2.8 | Run card, panel header, timeline rows and groups, status presentation, polling and reconcile, close/reopen, theme tokens | Blocks vitest: reconcile by event ID with overlap, gaps and out-of-order pages; group step count and duration; status meta for eight states has icon, label and token; rows render collapsed thought/tool and expanded result; API: cursor pages are stable across 1,000 events; browser: scenes 1, 2, 4, 7 in Light/Dark, keyboard disclosure, focus return on close, peek and full page |

## Verification

```bash
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app -k "agent_run or agent_worker or agent_conclusion or entity_search" plane/tests/unit -k "mention"
cd apps/api && uv run python manage.py makemigrations --check --dry-run && uv run ruff check .
cd apps/agent-worker && uv run pytest -m "not native and not docker" && uv run pytest -m native   # native on Mini only
pnpm --filter=@plane/editor test && pnpm --filter=@plane/blocks test
pnpm turbo run check:types --filter=web --filter=space --filter=@plane/editor --filter=@plane/blocks --filter=@plane/types
pnpm check:lint && pnpm --filter=@plane/i18n check:sync
```

Live check on the Mini: real comment mentions Claude on a bound project; Run completes with a conclusion; second mention gets a second clone.

## Success criteria

- [ ] All 11 Given/When/Then cases of 2.7 and all 9 of 2.8 pass.
- [ ] Deferred Run-level criteria of 2.2-2.5 pass.
- [ ] `apps/space` still type-checks after the editor type change.
- [ ] Mockup rows I010, I011, I013-I017, I019-I022, I035, I036, I043, I074 pass browser review.

## Risks

| Risk | L x I | Mitigation |
| --- | --- | --- |
| Comment create becomes slower due to snapshot build | Medium x Medium | Snapshot query bounded by comment count budget; measure p95 on a 500-comment issue (target < 300 ms added) |
| Event table growth | Medium x Medium | Index (run, seq); page size cap 200; payload size cap with chunking |
| Duplicate Run on client retry | Medium x High | Unique (trigger_comment, agent) |
| `apps/space` breaks from editor type change | Low x Medium | New fields are optional; typecheck `space` in verification |

## Rollback

Revert the PR and migrate `db` back to the Phase 2 migration. Comments created during the phase stay valid; agent mentions render as plain mention text. Stop the Worker before rollback so no Run is mid-turn.
