---
phase: 1
title: "GitHub connection and project repository"
status: todo
priority: P1
effort: "6d"
dependencies: []
---

# Phase 1: GitHub connection and project repository

## Goal

A workspace administrator connects GitHub with the device flow, manages installations and pull-request policy, and a project creator binds one repository. One PR to `preview`, one commit per story 1.1-1.8.

## Context links

- Stories: [epics.md:366-588](../2026-09-28-plane-local-cli-agents-epics/epics.md) (Epic 1). Coverage: [story-coverage.md](./story-coverage.md).
- Contracts: [architecture-contracts.md](./architecture-contracts.md) §2-§4, §7. Spine AD-9.
- Design: handoff README Screen 3 (GitHub) and Screen 4 (New project); scenes 11 and 12.
- Prior lessons: [device flow](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-github-device-flow-progress.md), [installations](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-github-installations-progress.md), [repository and policy](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-repository-and-pr-policy-progress.md), [PR policy acceptance](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-github-pr-policy-acceptance.md), [branch format](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-branch-format-acceptance.md).

## Key decisions

- Use a GitHub App with device flow enabled. The user-to-server token lists `/user/installations` and their repositories. "Connect organisation" opens the App install URL, then Plane re-syncs installations through a second device-flow poll or a refresh action. App credentials come from instance configuration (decision Q3: instance configuration, environment variables as fallback).
- Store tokens and device codes with `encrypt_data` (`plane/license/utils/encryption.py:20`). Serializers never return tokens. Log redaction test covers the device flow.
- Repository catalog: a Celery task refreshes one GitHub page at a time and swaps the snapshot only after the last page succeeds (prior lesson). Search uses `icontains` on indexed `full_name`; add a trigram index only if a 10k-row probe exceeds 50 ms.
- Binding availability is derived: a binding is usable only when its installation is active and the connection is connected. Removal and disconnect keep the binding row for audit (1.3, 1.4).
- Branch format enum and the name helper live in `plane/agent/services/branch_name.py` (shared with Phase 3 and 7). Run-short-id suffix keeps names unique.
- Integrations page: members can read; only admins can change (1.6, 1.7 "I cannot change it"). This changes the existing admin-only gate at `page.tsx:39`.

## Files

Create (backend):
- `apps/api/plane/db/models/agent_github.py` (connection, device authorization, installation, repository, binding, policy); export from `apps/api/plane/db/models/__init__.py` (modify).
- Migrations `<next>_agent_github_connection`, `<next>_agent_github_installations`, `<next>_project_repository_binding`, `<next>_agent_github_policy` (generated; the first number is `0126` as of 2026-11-12).
- `apps/api/plane/agent/__init__.py`, `apps/api/plane/agent/github/client.py` (only GitHub HTTP seam), `apps/api/plane/agent/services/github_connection.py`, `apps/api/plane/agent/services/branch_name.py`.
- `apps/api/plane/app/views/agent/github.py`, `apps/api/plane/app/serializers/agent_github.py`, `apps/api/plane/app/urls/agent.py`.
- `apps/api/plane/bgtasks/agent_github_catalog_task.py`.
- Tests: `apps/api/plane/tests/contract/app/test_agent_github_device_flow.py`, `test_agent_github_installations.py`, `test_agent_github_disconnect.py`, `test_agent_repository_binding.py`, `test_agent_github_policy.py`; `apps/api/plane/tests/unit/test_agent_branch_name.py`.

Modify (backend):
- `apps/api/plane/app/urls/__init__.py` (register agent URLs).
- `apps/api/plane/utils/instance_config_variables/core.py` (GitHub App keys beside `:73`).
- `apps/api/plane/app/views/project/base.py:259-313` and `apps/api/plane/app/serializers/project.py:31` (accept optional `repository` on create; return binding with availability).

Create (web):
- `packages/types/src/agent/github.ts`, `packages/constants/src/agent.ts`.
- `apps/web/services/agent/github.service.ts`, `apps/web/store/agent/github.store.ts`, `apps/web/hooks/store/use-agent-github.ts`.
- `apps/web/components/settings/integrations/index-page.tsx`, `.../github/{setup-card,device-flow,detail-page,installations-list,pr-policy}.tsx`.
- `app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/integrations/github/page.tsx`.
- `apps/web/components/projects/create/repository-section.tsx`.
- `packages/blocks/src/agent-run/repository-list.ts` (group, filter, availability logic) + `repository-list.test.ts`; `packages/blocks/src/agent-run/index.ts`.
- `packages/i18n/src/locales/*/agent.json`.

Modify (web):
- `apps/web/app/routes/core.ts:258-285` (add `settings/integrations` and `settings/integrations/github`).
- `packages/constants/src/settings/workspace.ts:29-81` (add `integrations` tab, members read, admins write).
- `app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/integrations/page.tsx` (replace legacy content and admin-only gate).
- `apps/web/components/projects/create/root.tsx` (render repository section, submit binding).
- `apps/web/store/root.store.ts`, `packages/types/src/index.ts`, `packages/blocks/package.json` (add `./agent-run` export).

Do not modify: `apps/web/components/integration/github/*`, `apps/web/components/integration/slack/*`, legacy `plane/db/models/integration/github.py`.

## API endpoints (member, session auth)

| Method and path under `api/workspaces/<slug>/agent-github/` | Role | Story |
| --- | --- | --- |
| `GET connection/` | member read | 1.1 |
| `POST device-authorizations/` (kind user or organization), `POST device-authorizations/<id>/poll/`, `POST device-authorizations/<id>/cancel/` | admin | 1.1, 1.2 |
| `GET installations/`, `POST installations/sync/`, `DELETE installations/<id>/` | admin (list: member) | 1.2, 1.3 |
| `DELETE connection/` | admin | 1.4 |
| `GET repositories/?search=&owner=&cursor=` | member, filtered by grant and member access | 1.2, 1.5 |
| `GET policy/`, `PATCH policy/` | member read, admin write | 1.6-1.8 |
| `POST api/workspaces/<slug>/projects/` with `repository` | existing create, extended | 1.5 |

## Tests Before (regression on touched surfaces)

1. Project create without `repository` returns the same 201 body as today (`test_project_app.py` stays green; add one explicit case).
2. Existing settings routes render for admin and member (typecheck of `routes/core.ts` and constants; vitest for any helper moved).
3. Non-admin access to GitHub write endpoints returns 403.

## Refactor

Protected by Tests Before 1-3: extend `ProjectViewSet.create` (`plane/app/views/project/base.py:259`) and `ProjectSerializer` (`plane/app/serializers/project.py:31`) with an optional nested `repository`; replace the admin-only gate of the Integrations page with member read and admin write; add the `integrations` tab to `packages/constants/src/settings/workspace.ts`. Behavior without `repository` stays identical.

## Story steps and Tests After

| Story | Steps | Tests After (write first, then implement) |
| --- | --- | --- |
| 1.1 | Models, device code start, poll with interval and expiry, cancel, token encrypt, refresh; setup card, device-flow card with URL, code, expiry, "I entered the code", Cancel; connected detail with back link | Contract: start, pending, success stores connection, expired, denied, cancelled creates no connection, token absent from responses and `caplog`; blocks vitest for expiry countdown label; browser: keyboard order and labels |
| 1.2 | Organization flow opens install URL, then installation sync; idempotent upsert by `installation_id` | Contract: new org appears once; repeated sync no duplicate; cancel/deny leaves list unchanged; repository list filtered by member access |
| 1.3 | Remove one installation with confirm; mark bindings from it unavailable | Contract: only target removed; binding kept with `available=false`; GitHub error keeps installation and returns actionable error |
| 1.4 | Disconnect with confirm; revoke token at GitHub; clear tokens; keep history | Contract: list and PR paths fail with `github_disconnected`; bindings kept; GitHub failure returns error and keeps connection |
| 1.5 | Repository section in create form: search, owner filter, groups, unavailable rows, selected state, no-repository warning, disconnected link; API stores one identity and base ref; no Mirror or clone | Contract: bind, duplicate bind 409, unavailable repo 409, no repo allowed, disconnected rejects; blocks vitest for grouping/filter/availability labels; browser: keyboard selection, 375 px, Light/Dark |
| 1.6 | Policy model with `open_as_draft=true` default; switch row | Contract: default true, admin PATCH persists, member PATCH 403; browser: member sees disabled switch |
| 1.7 | `mirror_conclusions=false` default; switch row | Same three checks as 1.6 |
| 1.8 | `branch_format` enum and selector with both Run-unique labels | Unit: both formats, two Runs on one issue differ, invalid identifiers sanitized; contract: persist and reload |

## Verification

```bash
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app/test_agent_github_device_flow.py plane/tests/contract/app/test_agent_github_installations.py plane/tests/contract/app/test_agent_github_disconnect.py plane/tests/contract/app/test_agent_repository_binding.py plane/tests/contract/app/test_agent_github_policy.py plane/tests/contract/app/test_project_app.py plane/tests/unit/test_agent_branch_name.py
cd apps/api && uv run python manage.py makemigrations --check --dry-run && uv run ruff check . && uv run ruff format --check .
pnpm --filter=@plane/blocks test
pnpm turbo run check:types --filter=web --filter=@plane/blocks --filter=@plane/types --filter=@plane/constants
pnpm check:lint && pnpm check:format && pnpm --filter=@plane/i18n check:sync
```

Opt-in live check (operator credentials): connect a real GitHub App, add one organization, remove it, disconnect. Record in `reports/`.

## Success criteria

- [ ] All Given/When/Then cases of 1.1-1.8 pass with the tests above or recorded browser evidence.
- [ ] No token value appears in any API response, Run context or log line (asserted by test).
- [ ] Mockup rows I046-I057, I068-I071, I076, I077 pass browser review; I070 has no clone progress.
- [ ] Existing project-create tests pass unchanged.

## Risks

| Risk | L x I | Mitigation |
| --- | --- | --- |
| No GitHub App credentials during development | High x Medium | Client seam mocked in tests; live check is opt-in and blocks only the "done" mark, not the merge of tested code |
| Device flow for GitHub Apps needs "Enable Device Flow" on the App | Medium x High | Setup doc in README of `plane/agent/github/`; start endpoint returns `device_flow_disabled` error with hint |
| Catalog refresh interrupted mid-pagination | Medium x Medium | Snapshot swap only after the last page; resume from saved page |
| "Available to that member" (1.2) has no per-member GitHub identity in the spec | Medium x Medium | V1 rule: a repository is available when the workspace grant is active and the caller is a workspace Admin or Member who can create projects. Guests get 403. Confirmed by the user (decision Q8) |

## Rollback

Revert the PR. Run `uv run python manage.py migrate db 0125` (the last migration before this phase) before the revert on any database that applied the new migrations. New tables hold no data used by other features. The project create path accepts requests without `repository`, so old clients keep working.
