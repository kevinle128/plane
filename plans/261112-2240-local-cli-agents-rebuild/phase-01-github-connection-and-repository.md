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
- <!-- red-team 2026-11-12 --> App credentials accessor (Q3, exact semantics): one function in `github_connection.py` returns the instance-configuration value when it is non-empty, else the environment value. `get_configuration_value` (`plane/license/utils/instance_value.py:17-39`) returns a stored empty string as-is, and `configure_instance` copies env only when the row is created (`configure_instance.py:28-37`), so it cannot be used directly. New keys get their own names (for example `GITHUB_APP_CLIENT_ID`, `GITHUB_APP_CLIENT_SECRET` encrypted, `GITHUB_APP_SLUG`); they do not reuse the GitHub login keys at `core.py:74-85`.
- <!-- red-team 2026-11-12 --> Token refresh: GitHub App refresh tokens are single-use ("Once you use a refresh token, that refresh token and the old user access token will no longer work", GitHub docs, refreshing user access tokens). Refresh runs only in `github_connection.py`, under `select_for_update` on the connection row; it re-reads the token after the lock, refreshes only if still expired, and saves the new pair in the same transaction. Every caller (catalog task, Phase 7 PR and mirror) goes through this function.
- <!-- red-team 2026-11-12 --> Encryption result check: `encrypt_data`/`decrypt_data` return `""` on any error (`encryption.py:20-44`). The service rejects an empty ciphertext before it sets `status=connected`, and treats an empty decrypt of a non-empty stored value as `reconnect_required` (no GitHub call with an empty token).
- <!-- red-team 2026-11-12 --> Device-flow poll: lock the authorization row with `select_for_update`; if the row is already terminal, return the stored result without a GitHub call; upsert the workspace connection. A second concurrent poll never changes `completed` to another state.
- <!-- red-team 2026-11-12 --> Installation removal (1.3) is a Plane-side detach (`removed_at`) plus a link to the GitHub installation settings. Uninstall at GitHub (`DELETE /app/installations/{id}`) needs an App JWT and private key, which decision Q3 does not supply. Sync (1.2 and every device-flow poll) never clears `removed_at`: a detached installation stays detached until an admin re-adds it explicitly, although `/user/installations` still returns it.
- <!-- red-team 2026-11-12 --> Disconnect (1.4) revokes only this workspace's token with `DELETE /applications/{client_id}/token` (Basic auth with client ID and secret). Do not use `DELETE /applications/{client_id}/grant`: it deletes every token of that GitHub user for the App, which also disconnects other workspaces the same user connected. The access token in the body expires after 8 h: refresh it through the locked refresh function first when it is expired. GitHub documents only 204 and 422 for this endpoint and does not say what an invalid token returns, so a 404 or a 422 for an invalid token counts as already revoked and Plane clears the local tokens; only network errors and 5xx keep the connection.
- <!-- red-team 2026-11-12 --> Binding input: the create request carries only the catalog repository row ID and an optional `base_ref`. `full_name`, `clone_url`, `github_repository_id` and installation come from this workspace's catalog row under an active grant; other client fields are ignored. `base_ref` defaults to the repository `default_branch` and must pass git ref-name rules (no leading `-`, no `..`, no `@{`, no space, no control characters, max 255 bytes), because Phases 3 and 7 pass it to git.
- <!-- red-team 2026-11-12 --> Celery tasks take connection and workspace IDs only, never tokens, so no token reaches the broker or task logs.

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
- `apps/api/plane/utils/instance_config_variables/core.py` (GitHub App keys beside `:73`; new key names, see Key decisions). <!-- red-team 2026-11-12 -->
- `apps/api/plane/app/views/project/base.py:259-313` and `apps/api/plane/app/serializers/project.py:31` (accept optional `repository` on create; return binding with availability).

Create (web):
- `packages/types/src/agent/github.ts`, `packages/constants/src/agent.ts`.
- `apps/web/services/agent/github.service.ts`, `apps/web/store/agent/github.store.ts`, `apps/web/hooks/store/use-agent-github.ts`.
- `apps/web/components/settings/integrations/index-page.tsx`, `.../github/{setup-card,device-flow,detail-page,installations-list,pr-policy}.tsx`.
- `apps/web/app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/integrations/github/page.tsx`.
- `apps/web/components/projects/create/repository-section.tsx`.
- <!-- red-team 2026-11-12 --> Admin app (Q3 source): a GitHub App form beside the existing GitHub login form (`apps/admin/app/(all)/(dashboard)/authentication/github/form.tsx`, `apps/admin/components/authentication/github-config.tsx`), for example `apps/admin/components/authentication/github-app-config.tsx`; key types in `packages/types/src/instance/auth.ts` (modify). The instance PATCH (`plane/license/api/views/configuration.py:43-59`) updates only keys that already exist, so the keys must be in `core.py` first.
- `packages/blocks/src/agent-run/repository-list.ts` (group, filter, availability logic) + `repository-list.test.ts`; `packages/blocks/src/agent-run/index.ts`.
- `packages/i18n/src/locales/*/agent.json`.

Modify (web):
- `apps/web/app/routes/core.ts:258-285` (add `settings/integrations` and `settings/integrations/github`).
- `packages/constants/src/settings/workspace.ts:29-81` (add `integrations` tab, members read, admins write).
- `apps/web/app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/integrations/page.tsx` (replace legacy content and admin-only gate).
- `apps/web/components/projects/create/root.tsx` (render repository section, submit binding).
- `apps/web/store/root.store.ts`, `packages/types/src/index.ts`, `packages/blocks/package.json` (add `./agent-run` export).
- <!-- red-team 2026-11-12 --> `packages/types/src/settings.ts:13` (add `"integrations"` to `TWorkspaceSettingsTabs`); `apps/web/components/settings/workspace/sidebar/item-icon.tsx:19` (icon for `integrations`; the `Record` fails typecheck without it); `packages/constants/src/index.ts` (export `./agent`); `packages/i18n/src/constants/namespaces.ts:7-36` (add `"agent"`; a namespace missing here never loads and the UI shows raw keys, and `check:sync` does not detect it).

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

<!-- red-team 2026-11-12 --> The former item 3 (non-admin 403 on GitHub write endpoints) tests new endpoints, so it moved to Tests After (1.1, 1.6).

## Refactor

Protected by Tests Before 1-2: extend `ProjectViewSet.create` (`plane/app/views/project/base.py:259`) and `ProjectSerializer` (`plane/app/serializers/project.py:31`) with an optional nested `repository`; replace the admin-only gate of the Integrations page with member read and admin write; add the `integrations` tab to `packages/constants/src/settings/workspace.ts`. Behavior without `repository` stays identical.

<!-- red-team 2026-11-12 --> `ProjectViewSet.create` today saves the project, members and states without a transaction (`base.py:262-296`; no `ATOMIC_REQUESTS`). With a repository, put project, members, states and binding in one `transaction.atomic` block, map `IntegrityError` on the binding to 409, and keep `model_activity.delay` after the block. `ProjectSerializer` uses `fields = "__all__"` (`project.py:35`): pop `repository` before `Project.objects.create`.

## Story steps and Tests After

| Story | Steps | Tests After (write first, then implement) |
| --- | --- | --- |
| 1.1 | Models, device code start, poll with interval and expiry, cancel, token encrypt, refresh; setup card, device-flow card with URL, code, expiry, "I entered the code", Cancel; connected detail with back link | Contract: start, pending, success stores connection, expired, denied, cancelled creates no connection, token absent from responses and `caplog`; blocks vitest for expiry countdown label; browser: keyboard order and labels. <!-- red-team 2026-11-12 --> Also: member and guest get 403 on start, poll, cancel; two concurrent polls on one authorization give one connection and the row stays `completed`; empty ciphertext from `encrypt_data` does not set `connected`; empty decrypt of a stored token returns `reconnect_required` with no GitHub call; two concurrent refresh calls on an expired token cause one GitHub refresh call; App credentials accessor returns env when the DB row is empty and the DB value when set; the `caplog` check covers the GitHub client and service loggers and asserts Celery task arguments contain no token |
| 1.2 | Organization flow opens install URL, then installation sync; idempotent upsert by `installation_id` | Contract: new org appears once; repeated sync no duplicate; cancel/deny leaves list unchanged; repository list filtered by member access |
| 1.3 | Remove one installation with confirm (Plane-side detach, link to GitHub settings for uninstall); mark bindings from it unavailable | Contract: only target removed; binding kept with `available=false`; a failed detach (forced DB error) keeps the installation visible and returns an actionable error; detach, then sync: the installation stays removed and its binding stays `available=false` <!-- red-team 2026-11-12 --> |
| 1.4 | Disconnect with confirm; revoke this token at GitHub (`DELETE /applications/{client_id}/token`); clear tokens; keep history | Contract: list and PR paths fail with `github_disconnected`; bindings kept; GitHub failure returns error and keeps connection; <!-- red-team 2026-11-12 --> the revoke call targets the token endpoint, not the grant endpoint, and sends only this workspace's token. Expired access token is refreshed before revoke; 404 or invalid-token 422 from GitHub clears local tokens; a 5xx or network error keeps the connection. AC 2 for new Launches is tested in Phase 3 and for pending PR delivery in Phase 7 |
| 1.5 | Repository section in create form: search, owner filter, groups, unavailable rows, selected state, no-repository warning, disconnected link; API stores one identity and base ref; no Mirror or clone | Contract: bind, duplicate bind 409, unavailable repo 409, no repo allowed, disconnected rejects; blocks vitest for grouping/filter/availability labels; browser: keyboard selection, 375 px, Light/Dark. <!-- red-team 2026-11-12 --> Also: catalog row of another workspace returns 404; client-supplied `clone_url`/`full_name` are ignored and the stored values equal the catalog row; `base_ref` with leading `-`, `..` or a control character returns 400; omitted `base_ref` stores `default_branch`; concurrent binds of one repository give one 201 and one 409 and leave no project without its binding; guest create stays 403 |
| 1.6 | Policy model with `open_as_draft=true` default; switch row | Contract: default true, admin PATCH persists, member PATCH 403; browser: member sees disabled switch |
| 1.7 | `mirror_conclusions=false` default; switch row | Same three checks as 1.6 |
| 1.8 | `branch_format` enum and selector with both Run-unique labels | Unit: both formats, two Runs on one issue differ, invalid identifiers sanitized; contract: persist and reload. <!-- red-team 2026-11-12 --> AC 4 (a Run keeps its branch after a format change) needs a Run and is tested in Phase 7 (3.1) |

## Verification

```bash
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app/test_agent_github_device_flow.py plane/tests/contract/app/test_agent_github_installations.py plane/tests/contract/app/test_agent_github_disconnect.py plane/tests/contract/app/test_agent_repository_binding.py plane/tests/contract/app/test_agent_github_policy.py plane/tests/contract/app/test_project_app.py plane/tests/unit/test_agent_branch_name.py
docker compose -f docker-compose-test.yml run --rm api-tests python manage.py makemigrations --check --dry-run
cd apps/api && uv run ruff check . && uv run ruff format --check .   # host uv must equal required-version in apps/api/pyproject.toml
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
- [ ] <!-- red-team 2026-11-12 --> 1.4 AC 2 and 1.8 AC 4 need a Run; they are listed as pending and close in Phases 3 and 7.
- [ ] <!-- red-team 2026-11-12 --> The `makemigrations --check` line runs in the test container (local `manage.py` defaults to production settings and does not load `apps/api/.env`).

## Risks

| Risk | L x I | Mitigation |
| --- | --- | --- |
| No GitHub App credentials during development | High x Medium | Client seam mocked in tests; live check is opt-in and blocks only the "done" mark, not the merge of tested code |
| Device flow for GitHub Apps needs "Enable Device Flow" on the App | Medium x High | Setup doc in README of `plane/agent/github/`; start endpoint returns `device_flow_disabled` error with hint |
| Catalog refresh interrupted mid-pagination | Medium x Medium | Snapshot swap only after the last page; resume from saved page |
| "Available to that member" (1.2) has no per-member GitHub identity in the spec | Medium x Medium | V1 rule: a repository is available when the workspace grant is active and the caller is a workspace Admin or Member who can create projects. Guests get 403. Confirmed by the user (decision Q8) |
| <!-- red-team 2026-11-12 --> Open: which installations attach to the workspace. `/user/installations` returns every installation the connecting admin can see, including other organisations; Q8 covers member visibility, not installation attachment | Medium x High | Pending user decision: attach all visible installations, or only those the admin selects. See red-team report F13 |
| <!-- red-team 2026-11-12 --> Open: the connection keeps using the connecting admin's token after that admin leaves or is demoted | Medium x Medium | Pending user decision: keep and show "connected by", or mark disconnected. See red-team report F14 |

## Rollback

Revert the PR. Run `uv run python manage.py migrate db 0125` (the last migration before this phase) before the revert on any database that applied the new migrations. New tables hold no data used by other features. The project create path accepts requests without `repository`, so old clients keep working.
