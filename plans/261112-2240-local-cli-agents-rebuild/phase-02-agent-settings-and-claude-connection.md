---
phase: 2
title: "Agent settings and Claude connection"
status: todo
priority: P1
effort: "6d"
dependencies: [1]
---

# Phase 2: Agent settings and Claude connection

## Goal

An administrator sees four Harness cards, configures each workspace Agent (name, handle, instructions, Mentionable, model), and connects Claude Code through a real Worker probe. One PR, one commit per story 2.1-2.6.

## Context links

- Stories: [epics.md:595-741](../2026-09-28-plane-local-cli-agents-epics/epics.md). Contracts: [architecture-contracts.md](./architecture-contracts.md) §3 (`Agent`, `AgentConnection`, `AgentWorker`), §4, §5, §7. Spine AD-4.
- Design: Screen 3 Harness detail page; scene 11.
- Prior lessons: [harness runtime decision](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-harness-runtime-decision.md), [worker foundation](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-worker-foundation-progress.md) (Claude probe passed seven checks in about 33 s with safe mode and restricted settings), [name/handle](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-agent-name-and-handle-acceptance.md), [instructions](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-agent-instructions-acceptance.md), [Mentionable](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-agent-mentionable-acceptance.md).

## Dependency rationale

Phase 1 must merge first. Both phases change `apps/web/app/routes/core.ts`, `packages/constants/src/settings/workspace.ts`, the Integrations index page and `packages/blocks/package.json`. The Integrations index shows GitHub (Phase 1) above the Harness group (this phase).

## Key decisions

- Four `Agent` rows per workspace are created lazily on first Integrations read. The unique (workspace, harness) constraint guards `get_or_create`; an `IntegrityError` on a concurrent first read re-reads the existing row, so two reads never create two Agents or two bot users. Each Agent owns one bot `User` (`is_bot=True`, `bot_type="AGENT"`), not a `WorkspaceMember`.
- Connect/Retry sets `connecting`, increments `probe_generation` and stores `probe_requested_at`. The Worker claims the probe, runs it and posts a versioned report. A report for an older generation is rejected. A probe with no report after 120 s reads as `failed` with missing action "Worker did not answer" (derived at read time, no beat task).
- Connected requires all AD-4 checks: authentication, model report, one resumed follow-up, progress events, interruption, permission enforcement (write denied under the OS boundary) and recovery. The report lists each check with pass/fail and the native capability flags (`midturn_input`, `native_resume`, `permission_prompt`).
- Model list comes only from the report. The model selector renders only for `connected`. A selected model is copied to each new Run at creation (Phase 3), so later changes do not touch existing Runs.
- Handle: case-insensitive unique per workspace (DB constraint on `Lower(handle)` plus serializer error "An agent with this handle already exists in this workspace.").
- Save disables the whole fieldset while the request runs (prior lesson: edit-during-Save lost a draft).
- Worker token: `AgentWorker` row with SHA-256 hash, created by `manage.py create_agent_worker --name mini --token-file <path>`; the command writes the token to a `0600` file and never prints it in logs. Dedicated authentication class that sets an authenticated principal; Worker views use their own `APIView` base with `throttle_classes = []` (the API-key limit of 60/min at `plane/settings/common.py:163` would block polling).

## Files

Create (backend):
- `apps/api/plane/db/models/agent.py` (`Agent`, `AgentConnection`, `AgentWorker`), migration `<next>_agent_settings` (generated).
- `apps/api/plane/agent/services/agent_settings.py`, `apps/api/plane/agent/services/harness_probe.py`.
- `apps/api/plane/agent/worker_api/{__init__,authentication,urls,views,serializers}.py`.
- `apps/api/plane/db/management/commands/create_agent_worker.py`.
- `apps/api/plane/app/views/agent/settings.py`, `apps/api/plane/app/serializers/agent.py`.
- Tests: `apps/api/plane/tests/contract/app/test_agent_settings.py`, `test_agent_harness_probe.py`, `test_agent_worker_auth.py`.

Modify (backend): `apps/api/plane/urls.py:18-25` (mount `api/agent-worker/v1/`), `apps/api/plane/app/urls/agent.py`, `apps/api/plane/db/models/__init__.py`.

Create (Worker, first increment): `apps/agent-worker/pyproject.toml`, `uv.lock`, `ruff.toml`, `pytest.ini`, `README.md`, `plane_agent_worker/{__init__,__main__,config,plane_client,loop,process_registry,sandbox_macos,conformance}.py`, `plane_agent_worker/sandbox/qa-readonly.sb`, `plane_agent_worker/drivers/{__init__,base,claude}.py`, `tests/fakes/fake_claude.py`, `tests/transcripts/claude/*.jsonl`, `tests/test_config.py`, `tests/test_plane_client.py`, `tests/test_claude_probe.py`, `tests/test_sandbox_macos.py`.

Create (web): `packages/types/src/agent/agent.ts`; `apps/web/services/agent/agent.service.ts`; `apps/web/store/agent/agent.store.ts`; `apps/web/hooks/store/use-agent.ts`; `apps/web/components/settings/integrations/harness/{harness-card,harness-detail-page,connection-row,model-select}.tsx`; `app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/integrations/[harness]/page.tsx`; `packages/blocks/src/agent-run/connection-state.ts` + test.

Modify (web): `apps/web/app/routes/core.ts` (harness route), `apps/web/components/settings/integrations/index-page.tsx` (Harness group), `apps/web/store/root.store.ts`, `packages/i18n/src/locales/*/agent.json`, `packages/constants/src/agent.ts`.

## API endpoints

| Path | Auth | Story |
| --- | --- | --- |
| `GET api/workspaces/<slug>/agents/`, `GET/PATCH .../agents/<harness>/` | member read, admin write | 2.1-2.6 |
| `POST .../agents/<harness>/connect/`, `POST .../agents/<harness>/disconnect/` | admin | 2.1 |
| `POST api/agent-worker/v1/probes/claim/`, `POST api/agent-worker/v1/probes/<id>/report/` | Worker token | 2.1, 2.6 |
| `POST api/agent-worker/v1/heartbeat/` | Worker token | 2.1 |

## Tests Before

1. Settings index for admin and member still renders other tabs (types and constants check).
2. Existing `APIToken` auth and its throttle stay unchanged (`test_api_token.py` passes).

## Refactor

Protected by Tests Before 1-2: add the Worker URL include in `plane/urls.py:18-25` before the generic `api/` entry so no existing route changes. No other existing code changes.

## Story steps and Tests After

| Story | Steps | Tests After |
| --- | --- | --- |
| 2.1 | Worker auth: 120 Worker calls in one minute return no 429; revoked token 401. Agent and connection models; four cards with live tags; harness detail with selector tags, Enabled switch, back link; Worker config, client, probe loop, macOS read-only profile, Claude driver probe; Disconnect | API: connect sets `connecting`; old-generation report 409; report with a failed check sets `failed` with missing action; full pass sets `connected`; disconnect blocks new mentions flag; Worker: fake Claude passes all checks, fake with missing permission prompt fails with named action, config rejects non-localhost origin and token file inside the Run root; native (`-m native`, Mini only): real Claude probe passes; blocks vitest: tag mapping for four states |
| 2.2 | Name field with validation | API: valid name persists, empty name 400 keeps old name; Run identity unaffected (asserted again in Phase 3) |
| 2.3 | Handle field, uniqueness | API: unused handle saves; collision 400 with inline message and both handles unchanged; case-insensitive collision |
| 2.4 | Instructions textarea | API: multiline Unicode persists; snapshot copy test lands in Phase 3 (2.4 AC 2-3 is verified there with Run creation) |
| 2.5 | Mentionable switch | API: toggle persists; picker reason test lands in Phase 3 |
| 2.6 | Model selector from report | API: selection must be in reported list (400 otherwise); disconnected or failed hides selection; refresh keeps value |

Note: 2.4 AC 2-3, 2.5 AC 2-3 and 2.2/2.3 AC 3 need a Run. Phase 2 commits the settings behavior and adds those Run-level tests in the Phase 3 PR under the same story names. The story is "done" only after Phase 3 merges. This is the only cross-phase story split.

## Verification

```bash
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app/test_agent_settings.py plane/tests/contract/app/test_agent_harness_probe.py plane/tests/contract/app/test_agent_worker_auth.py plane/tests/contract/app/test_api_token.py
cd apps/api && uv run python manage.py makemigrations --check --dry-run && uv run ruff check .
cd apps/agent-worker && uv sync && uv run pytest -m "not native and not docker" && uv run ruff check . && uv run ruff format --check .
cd apps/agent-worker && uv run pytest -m native tests/test_claude_probe.py   # Mini only
pnpm --filter=@plane/blocks test && pnpm turbo run check:types --filter=web --filter=@plane/blocks
pnpm check:lint && pnpm --filter=@plane/i18n check:sync
```

Browser: scene 11 Harness states for Claude (Not connected, Connecting, Connected, Connection failed) with a real Worker; keyboard and 375 px.

## Success criteria

- [ ] 2.1 and 2.6 pass with a real Claude probe on the Mini; Codex, Grok and Omp cards show Not connected and can be configured but not connected (their probes arrive in Phase 6).
- [ ] 2.2, 2.3, 2.4, 2.5 settings criteria pass; Run-level criteria are listed as pending Phase 3.
- [ ] No mock model appears as verified (UI renders only report models).

## Risks

| Risk | L x I | Mitigation |
| --- | --- | --- |
| Claude CLI version changes its stream-JSON events | Medium x High | Driver records the CLI version; probe fails with "unsupported version" and keeps Connection failed; transcripts are re-recorded per version |
| `sandbox-exec` is deprecated on macOS | Low x High | Profile test runs on the Mini each release; failure blocks Connected |
| Worker token leak | Low x High | Hash at rest, `0600` file, token outside Run root, Worker rejects proxy and redirects |

## Rollback

Revert the PR and migrate `db` back to the Phase 1 migration. Stop the Worker process. No existing data depends on the new tables.
