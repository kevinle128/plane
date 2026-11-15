---
phase: 1
title: "Git provider connection (GitHub and GitLab) and project repository"
status: todo
priority: P1
effort: "11d"
dependencies: []
---

# Phase 1: Git provider connection (GitHub and GitLab) and project repository

## Goal

A workspace administrator connects GitHub with the device flow and a self-hosted GitLab with a pasted Group Access Token. The admin selects which GitHub installations attach, and sets the change-request policy per provider. A project creator binds one repository from either provider. The data model is provider-neutral, so later phases do not depend on one provider. One PR to `preview`, one commit per story: 1.1-1.8, then G1-G5.

The file name keeps `github` so that existing links stay valid. The phase covers both providers.

> **2026-11-14, decision Q36 (after merge):** there are no Code jobs, so the policies of 1.6, 1.7, 1.8 and G5 (`AgentGitPolicy`) and the `write_repository` scope check of G1 have no consumer. The merged code does not change now; plan.md Q36 lists the follow-up (hide or remove later). 1.4 AC 2 and G4 AC2 still close in Phase 3 (Run launch); their change-request parts are removed. 1.8 AC 4 and G5 AC4 are removed (only Code jobs read the policy).

## Context links

- Stories: [epics.md:366-588](../2026-09-28-plane-local-cli-agents-epics/epics.md) (Epic 1, GitHub). GitLab stories G1-G5: [below](#gitlab-stories-and-acceptance-criteria) (plan-level; epics.md has no GitLab story). Scope: [gitlab-scope-decisions.md](./gitlab-scope-decisions.md). Coverage: [story-coverage.md](./story-coverage.md).
- Contracts: [architecture-contracts.md](./architecture-contracts.md) §2-§4, §7, §11 (provider boundary). Spine AD-9.
- Design: handoff README Screen 3 (GitHub) and Screen 4 (New project); scenes 11 and 12. GitLab reuses the GitHub screens. Only the provider name, the icon and the terms change ("Merge Request" for "Pull Request", "Group" for "Organization"). The GitLab connect card replaces the device-flow card with a token form (base URL, group path, token, optional CA bundle); it uses the same card, field and button components.
- Prior lessons: [device flow](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-github-device-flow-progress.md), [installations](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-github-installations-progress.md), [repository and policy](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-repository-and-pr-policy-progress.md), [PR policy acceptance](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-github-pr-policy-acceptance.md), [branch format](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-branch-format-acceptance.md).

## Data flow

1. Connect. GitHub: browser -> device-flow endpoints -> `github_connection.py` -> GitHub -> encrypted tokens in `AgentGitConnection(provider=github)`. GitLab: browser posts base URL, group path, token and optional CA bundle -> `gitlab_connection.py` runs the connect checks (G1) through `git_providers/http.py` -> on success stores `AgentGitConnection(provider=gitlab)` with the encrypted token, scopes, expiry, server version and token user, plus one attached `AgentGitAccount` for the group.
2. Accounts. GitHub: sync stores installations as `candidate`; the admin attaches the ones they select (Q9). GitLab: the group is the only account; it is `attached` at connect.
3. Catalog. A Celery task takes the connection ID, gets a `GitProviderClient` from `git_providers.client_for(connection)`, lists repositories of each attached account page by page, and swaps the `AgentGitRepository` snapshot after the last page.
4. Bind. Project create sends a catalog row ID and an optional `base_ref`. The view copies provider, host, external ID, `full_name`, `clone_url`, `web_url` and `default_branch` from that row into `ProjectRepositoryBinding` inside the project transaction.
5. Exit. Later phases read the binding and `AgentGitPolicy(workspace, provider)`. No later phase reads a GitHub-only or GitLab-only table, except Phase 7 through the provider interface.

## Key decisions

Provider-neutral:

- Models and API are provider-neutral (architecture-contracts §3, §11). Provider-specific code is only in `plane/agent/git_providers/github.py`, `plane/agent/git_providers/gitlab.py`, `plane/agent/services/github_connection.py` and `plane/agent/services/gitlab_connection.py`. `git_providers/__init__.py` has one function `client_for(connection)` with one branch per provider. There is no registry.
- All provider HTTP goes through one seam, `plane/agent/git_providers/http.py`. It calls `pinned_fetch` (`plane/utils/url_security.py:198`) with timeouts, no redirects, no proxy, and the connection CA bundle. It maps transport failures to fixed reason codes (G1 table). Tests patch this seam only. This replaces the earlier "GitHub host is fixed, plain `requests`" rule.
- Store tokens and device codes with `encrypt_data` (`plane/license/utils/encryption.py:20`). Serializers never return tokens. Log redaction tests cover the device flow and the GitLab connect.
- Repository catalog: a Celery task refreshes one provider page at a time and swaps the snapshot only after the last page succeeds (prior lesson). Search uses `icontains` on indexed `full_name`; add a trigram index only if a 10k-row probe exceeds 50 ms.
- Binding availability is derived: a binding is usable only when its account is `attached`, its connection is `connected`, and the binding host equals the connection host. Removal and disconnect keep the binding row for audit (1.3, 1.4, G4).
- Branch format enum and the name helper live in `plane/agent/services/branch_name.py` (shared with Phase 3 and 7). Run-short-id suffix keeps names unique. The format is read from the policy of the binding's provider.
- Policy is per (workspace, provider): `open_as_draft` (default true), `mirror_conclusions` (default false), `branch_format` (default `issue`). Each provider detail page shows its own policy rows.
- Integrations page: members can read; only admins can change (1.6, 1.7 "I cannot change it"). This changes the existing admin-only gate at `page.tsx:39`.
- <!-- red-team 2026-11-12 --> Encryption result check: `encrypt_data`/`decrypt_data` return `""` on any error (`encryption.py:20-44`). The service rejects an empty ciphertext before it sets `status=connected`, and treats an empty decrypt of a non-empty stored value as `reconnect_required` (no provider call with an empty token). This applies to both providers; the check lives in `git_connection.py`.
- <!-- red-team 2026-11-12 --> Binding input: the create request carries only the catalog repository row ID and an optional `base_ref`. `provider`, host, external ID, `full_name`, `clone_url` and account come from this workspace's catalog row under an attached account; other client fields are ignored. `base_ref` defaults to the repository `default_branch` and must pass git ref-name rules (no leading `-`, no `..`, no `@{`, no space, no control characters, max 255 bytes), because Phases 3 and 7 pass it to git.
- <!-- red-team 2026-11-12 --> Celery tasks take connection and workspace IDs only, never tokens, so no token reaches the broker or task logs.

GitHub:

- Use a GitHub App with device flow enabled. The user-to-server token lists `/user/installations` and their repositories. "Connect organisation" opens the App install URL, then Plane re-syncs installations through a second device-flow poll or a refresh action. App credentials come from instance configuration (decision Q3: instance configuration, environment variables as fallback).
- Installation attachment (decision Q9, 2026-11-12): `AgentGitAccount.state` is `candidate`, `attached` or `detached`. Sync creates new installations as `candidate` and updates names of existing rows. Sync never sets `attached` and never clears `detached`. Only an admin `POST accounts/<id>/attach/` sets `attached`. The catalog and binding read only `attached` accounts.
- Connecting admin check (decision Q10, 2026-11-12): the locked token function below checks, after it takes the row lock, that `connected_by` is an active Admin of the workspace (`WorkspaceMember` at `plane/db/models/workspace.py:198`, `role` at `:205` with 20 = Admin, `is_active` at `:210`). If not, it sets `status=reconnect_required`, `last_error=connected_admin_lost`, and makes no GitHub call. Every token user (catalog task, revoke, Phase 7 change request and mirror) goes through this function, so one check covers leave, removal, demotion and deactivation without hooks on each member mutation path. `GET connection/` runs the same check, so the detail page shows "Reconnect required" without waiting for a token use.
- <!-- red-team 2026-11-12 --> App credentials accessor (Q3, exact semantics): one function in `github_connection.py` returns the instance-configuration value when it is non-empty, else the environment value. `get_configuration_value` (`plane/license/utils/instance_value.py:17-39`) returns a stored empty string as-is, and `configure_instance` copies env only when the row is created (`configure_instance.py:28-37`), so it cannot be used directly. New keys get their own names (for example `GITHUB_APP_CLIENT_ID`, `GITHUB_APP_CLIENT_SECRET` encrypted, `GITHUB_APP_SLUG`); they do not reuse the GitHub login keys at `core.py:74-85`.
- <!-- red-team 2026-11-12 --> Token refresh: GitHub App refresh tokens are single-use ("Once you use a refresh token, that refresh token and the old user access token will no longer work", GitHub docs, refreshing user access tokens). Refresh runs only in `github_connection.py`, under `select_for_update` on the connection row; it re-reads the token after the lock, refreshes only if still expired, and saves the new pair in the same transaction. Every caller (catalog task, Phase 7 change request and mirror) goes through this function.
- <!-- red-team 2026-11-12 --> Device-flow poll: lock the authorization row with `select_for_update`; if the row is already terminal, return the stored result without a GitHub call; upsert the workspace connection. A second concurrent poll never changes `completed` to another state.
- <!-- red-team 2026-11-12 --> Installation removal (1.3) is a Plane-side detach (`state=detached`, `removed_at`) plus a link to the GitHub installation settings. Uninstall at GitHub (`DELETE /app/installations/{id}`) needs an App JWT and private key, which decision Q3 does not supply. Sync (1.2 and every device-flow poll) never clears `detached`: a detached installation stays detached until an admin attaches it again explicitly, although `/user/installations` still returns it.
- <!-- red-team 2026-11-12 --> Disconnect (1.4) revokes only this workspace's token with `DELETE /applications/{client_id}/token` (Basic auth with client ID and secret). Do not use `DELETE /applications/{client_id}/grant`: it deletes every token of that GitHub user for the App, which also disconnects other workspaces the same user connected. The access token in the body expires after 8 h: refresh it through the locked refresh function first when it is expired. GitHub documents only 204 and 422 for this endpoint and does not say what an invalid token returns, so a 404 or a 422 for an invalid token counts as already revoked and Plane clears the local tokens; only network errors and 5xx keep the connection. When the connection is `reconnect_required` because of Q10, disconnect clears the local tokens without a revoke call (the departed admin's token is not used again) and the detail page tells the admin to revoke it in GitHub.

GitLab:

- Authentication: a workspace admin pastes a Group Access Token, the GitLab base URL, the group full path, and an optional CA bundle (PEM). Header `PRIVATE-TOKEN`. The token is stored encrypted; the CA bundle is not secret and is stored as text.
- <!-- red-team 2026-11-12 gitlab --> Connect checks run in this order and stop at the first failure (codes in the G1 table): URL form; operator allowlist; reachability and TLS; `GET /api/v4/personal_access_tokens/self` (401 maps to `gitlab_token_invalid`; then `active=true`, `revoked=false`, `expires_at` null or in the future, `scopes` contain `api` and `write_repository`); `GET /api/v4/version` (404 or non-JSON maps to `gitlab_not_gitlab`; minimum 15.5, compare major.minor of a value such as `18.10.3-ee`); `GET /api/v4/user` (`bot` flag); `GET /api/v4/groups/<url-encoded path>`; `GET /api/v4/groups/<id>/members/all/<user_id>` (`access_level >= 30`, Developer). When `self` returns 404, call `/api/v4/version`: a JSON version below 15.5 gives `gitlab_version_unsupported`, a 404 or a non-JSON body gives `gitlab_not_gitlab`, and any other status (for example 403 from a `write_repository`-only token on a pre-15.5 server) gives `gitlab_unexpected_response`. Reason for this order: `self` accepts a token of any scope (GitLab source `lib/api/personal_access_tokens/self_information.rb:13-16`), but `/version` accepts only `api`, `read_api` (`lib/api/api.rb:57-58`) and `read_user`, `ai_features`, `ai_workflows` (`lib/api/metadata.rb:8`). With `/version` first, a `write_repository`-only token gets 403 `insufficient_scope` there, and G1 AC2 (`gitlab_scope_missing`) cannot occur. Any other unexpected status maps to `gitlab_unexpected_response` with the HTTP status, never to a 500.
- Minimum version 15.5: `GET /personal_access_tokens/self` "Introduced in GitLab 15.5" (GitLab docs at tag v15.5.0-ee, `doc/api/personal_access_tokens.md`, "Using a request header"). Every other API this plan uses is older; see architecture-contracts §11. `[UNVERIFIED until the Group Access Token live check]`: the docs do not state that `/personal_access_tokens/self` accepts a Group Access Token. Group token bot users hold ordinary personal access tokens (GitLab docs v16.0.0-ee `group_access_tokens.md` show `bot.personal_access_tokens.create`), so the plan expects it to work; the endpoint was verified on git.oceanlabs.dev with a personal token only. <!-- red-team 2026-11-12 gitlab --> More evidence, not proof: the endpoint refuses only tokens whose `token_type` is not `PersonalAccessToken` (`self_information.rb:19-23`, GitLab master), and a group token is a `PersonalAccessToken` record of the bot user. The live Group Access Token check still decides.
- Required scopes `api` and `write_repository`. `api` covers merge requests and notes. GitLab docs (v15.5.0-ee `personal_access_tokens.md` scope table) say `write_repository` "Grants read-write access to repositories on private projects using Git-over-HTTP (not using the API)", and Phase 7 pushes over HTTPS. A token with fewer scopes fails with `gitlab_scope_missing` and names the missing scope. <!-- red-team 2026-11-12 gitlab --> Evidence for plan.md open question 4 (no decision made here): in GitLab source (master) Git-over-HTTP token auth uses `abilities_for_scopes` (`lib/gitlab/auth.rb:308-329`), which maps `api` to `full_authentication_abilities` (`:350-352`), and those include `push_code` (`:475-486`). So an `api`-only token can likely push over HTTPS; the scope docs (`doc/security/tokens/access_token_scopes.md:41,44`) do not say so. The `api` scope alone is already broader than push.
- Non-bot token (provisional, plan.md open question 1): when `/user` returns `bot=false`, connect succeeds with a stored warning `gitlab_token_not_bot`. The detail page says that pushes and merge requests appear as that person and that the connection stops when that person loses access to the group.
- Base URL: `https` only; no user info, query or fragment; a path is allowed (relative-root installs such as `https://host/gitlab`); trailing `/` removed. Stored per workspace. A different base URL needs Disconnect first.
- Private network: a GitLab URL that resolves to a private address is blocked (`gitlab_url_not_allowed_or_unresolved`) unless the instance operator allows it with new settings `AGENT_GIT_ALLOWED_HOSTS` and `AGENT_GIT_ALLOWED_IPS`. They use the same parse rules as `WEBHOOK_ALLOWED_HOSTS`/`WEBHOOK_ALLOWED_IPS` (`plane/settings/common.py:57-80`); extract the parse loop into one helper in that file and use it for both pairs. A workspace admin cannot change the allowlist.
- <!-- red-team 2026-11-12 gitlab --> Hostile-server limits in `http.py` (a workspace admin chooses the server, so its responses are untrusted): read bodies with `stream=True` and stop at 1 MiB per response (`gitlab_unexpected_response`); one connect timeout of 5 s and read timeout of 10 s per call, and one total budget of 30 s for all connect checks, because `_fetch_validated_hop` tries every resolved address with the full timeout (`url_security.py:183-192`); reject a base URL whose host is the Plane request host or in `WEBHOOK_DISALLOWED_DOMAINS`, as the webhook serializer does (`plane/app/serializers/webhook.py:49-55`); the redirect message shows only the scheme and host of `Location`, not the full value.
- Custom CA bundle: validated at connect with `ssl.create_default_context(cadata=...)` (rejects bad PEM with `gitlab_ca_invalid`), max 256 KB. The bundle replaces system trust for this connection's host only; other hosts in the same process keep system trust. The http seam writes the bundle to a private file (mode 0600, name from its SHA-256) and passes it as `verify`. It writes a temporary file in the same directory and renames it into place, so a concurrent reader never sees a partial bundle. This needs a change in `url_security.py`: `_request_to_ip` hard-codes `verify=True` (`url_security.py:133`) and forwards `**kwargs` to `session.request`, so a caller `verify=` raises a duplicate-keyword `TypeError`. Add a `verify` parameter (default `True`) to `pinned_fetch`, `_fetch_validated_hop` and `_request_to_ip`. `PinnedIPAdapter.get_connection_with_tls_context` (`url_security.py:67-77`) already receives `verify`, so the path reaches urllib3 unchanged. Existing callers keep the default.
- One token = one group. The group is the single `attached` `AgentGitAccount` (Q9 equivalent). There is no candidate list and no sync action for GitLab. <!-- red-team 2026-11-12 gitlab --> A successful connect sets every other `AgentGitAccount` of this connection to `detached` in the same transaction. Otherwise a reconnect on the same base URL with another group leaves the old group `attached`; its bindings pass the availability rule (account attached, connection connected, same host) and Runs fail later at clone with `git_not_found`, or work through a token that the admin did not mean for that group.
- Catalog: `GET /api/v4/groups/<id>/projects?include_subgroups=true&with_shared=false&archived=false&per_page=100` (offset pages). A project whose `http_url_to_repo` host or scheme differs from the connection base URL is skipped and logged by ID, so the Worker is never pointed at a third host through an API response. `private` is true when `visibility` is not `public`.
- Disconnect is revoke-free (accepted scope): Plane clears the encrypted token, sets `disconnected`, keeps bindings with `available=false`, and the confirm dialog and result tell the admin to revoke the token in GitLab (group Settings > Access tokens). Plane does not call `DELETE /personal_access_tokens/self`.
- Worker reachability: the provider detail page shows `worker_last_error` and `worker_checked_at` when set ("Worker cannot reach <host>: <reason>"). The fields exist from this phase; Phase 3 writes them from clone results, because the Worker does not exist before Phase 2.
- Token expiry or revocation after connect: any 401 from GitLab sets `reconnect_required` with `gitlab_token_invalid`. <!-- red-team 2026-11-12 gitlab --> A 403 does not change the connection status: it is a per-resource refusal (for example a merge request on a project where the bot has a lower role) and is reported on that operation only. The detail page shows `expires_at` and a warning when expiry is within 14 days (no beat task; computed on read).
- Q10 (connecting admin leaves) does not apply to a Group Access Token: the token belongs to a group bot user, not to a workspace member. `connected_by` is stored for audit only.

## GitLab stories and acceptance criteria

These are plan-level stories. They extend Epic 1 for GitLab under [gitlab-scope-decisions.md](./gitlab-scope-decisions.md). Each is one commit, after 1.8.

### G1. Connect a self-hosted GitLab with a Group Access Token

Mockup rows (reused): I046 (card), I054-I057 (connect states, with token form in place of device code), I077.

- AC1 success: Given I am a workspace admin and I enter a reachable base URL (GitLab 15.5 or later), a group path, and an active Group Access Token with scopes `api` and `write_repository` and role Developer or higher in that group, when I select Connect, then the connection is `connected`, the detail page shows the base URL, GitLab version, group, token name, token user and expiry, and the token is never returned by any API.
- AC2 wrong scope: Given the token lacks `api` or `write_repository`, when I connect, then the connection is not stored and the message names each missing scope (`gitlab_scope_missing`).
- AC3 expired or revoked: Given the token is expired, revoked or inactive (`/api/v4/version` or `/personal_access_tokens/self` returns 401, or the token has `active=false`, `revoked=true`, or a past `expires_at`), when I connect, then nothing is stored and the message says the token is expired or revoked (`gitlab_token_invalid`).
- AC4 unreachable URL: Given the Plane API cannot resolve, connect to, or get a response from the base URL within the timeout, when I connect, then nothing is stored and the message names the failed step: connection or timeout (`gitlab_url_unreachable`), redirect (`gitlab_url_redirected`, shows the `Location`), or not a GitLab API (`gitlab_not_gitlab`, non-JSON or 404 on `/api/v4/version`).
- AC5 unresolved or blocked URL: Given the base URL does not resolve, or resolves to a private or loopback address that the operator has not allowed, when I connect, then nothing is stored and one message says the address cannot be resolved or is not allowed (`gitlab_url_not_allowed_or_unresolved`). The two cases give the same code and message, so a workspace admin cannot use the form to find which internal host names exist (same rule as `apps/api/plane/app/serializers/webhook.py:37`).
- AC6 too-old version: Given `/api/v4/version` returns a version below 15.5, when I connect, then nothing is stored and the message shows the found version and the minimum (`gitlab_version_unsupported`).
- AC7 bad certificate: Given the certificate does not validate against system trust and I give no CA bundle, when I connect, then nothing is stored and the message says the certificate is not trusted and that a CA bundle can be added (`gitlab_tls_failed`). Given I add the correct CA bundle, when I connect again, then the connection succeeds. Given the bundle is not valid PEM, then the message is `gitlab_ca_invalid`.
- AC8 role and group: Given the group path does not exist or the token cannot see it, then `gitlab_group_not_found`. Given the token user has a role below Developer in the group, then `gitlab_role_too_low` with the found role.
- AC9 non-bot token (provisional): Given the token belongs to a human user (`bot=false`), when I connect, then the connection succeeds and the detail page shows the warning `gitlab_token_not_bot`.
- AC10 permissions and coexistence: Given I am a member or guest, then connect returns 403. Given the workspace already has a GitHub connection, when I connect GitLab, then both connections are listed and work.

### G2. List the group's projects as repositories

Mockup rows (reused): I047, I050 (account row shows the group).

- AC1: Given a connected GitLab, when the catalog refreshes, then every non-archived project of the group and its subgroups appears once, with path, visibility, default branch and the group as owner.
- AC2: Given the refresh fails on a later page, then the previous catalog stays visible and unchanged.
- AC3: Given a project returns an `http_url_to_repo` on another host or scheme, then it is not listed.
- AC4: Given I am a member who can create projects, then I see the catalog read-only; given I am a guest, then 403 (Q8).

### G3. Bind a GitLab repository while creating a project

Mockup rows (reused): I068-I071, I076, with the GitLab icon on GitLab rows.

- AC1: Given both providers are connected, when I open the repository section, then rows are grouped by provider and owner, and each row shows its provider icon.
- AC2: Given I select a GitLab repository and create the project, then the binding stores provider `gitlab`, host, project ID, path, `clone_url` and `base_ref` (default branch when omitted), all copied from the catalog row.
- AC3: All 1.5 cases (duplicate bind 409, concurrent bind, other-workspace row 404, client-supplied fields ignored, invalid `base_ref` 400, no repository allowed, guest 403) pass for a GitLab row.
- AC4: Given a GitHub and a GitLab repository have the same numeric external ID, then both can be bound to different projects.

### G4. Disconnect GitLab (revoke-free)

Mockup rows (reused): I048.

- AC1: Given I am an admin, when I confirm Disconnect, then Plane clears the stored token, the connection is `disconnected`, bindings stay with `available=false`, and the dialog and the result tell me to revoke the token in GitLab, with a link to the group access-token settings.
- AC2: Given GitLab is disconnected, then the catalog and later change-request paths fail with `provider_disconnected` (provider `gitlab`), and a GitHub connection in the same workspace is unchanged.
- AC3: Given I reconnect with a different base URL, then old GitLab bindings stay unavailable (host differs) and new ones can bind.
- AC4: Plane makes no HTTP call to GitLab on disconnect.

### G5. Set GitLab merge-request policy

Mockup rows (reused): I051, I052, I053, with "merge request" terms.

- AC1: Given a GitLab connection, then its detail page shows "Open as draft merge request" (default on), "Mirror conclusions to the merge request" (default off) and the branch format selector (default `issue`).
- AC2: Given I change a GitLab policy value, then the GitHub policy is unchanged, and the reverse.
- AC3: Given I am a member, then I see the values with disabled controls, and PATCH returns 403.
- AC4: Given a Run on a GitLab-bound project, then Phases 3 and 7 read the GitLab policy (tested in Phase 3 snapshot and Phase 7 G6).

## Files

Create (backend):
- `apps/api/plane/db/models/agent_git.py` (`AgentGitConnection`, `AgentGithubDeviceAuthorization`, `AgentGitAccount`, `AgentGitRepository`, `ProjectRepositoryBinding`, `AgentGitPolicy`); export from `apps/api/plane/db/models/__init__.py` (modify).
- Migrations `<next>_agent_git_connection`, `<next>_agent_git_accounts`, `<next>_project_repository_binding`, `<next>_agent_git_policy` (generated; the first number is `0126` as of 2026-11-12).
- `apps/api/plane/agent/__init__.py`; `apps/api/plane/agent/git_providers/{__init__,base,http,github,gitlab}.py` (provider seam, architecture-contracts §11); `apps/api/plane/agent/services/{git_connection,github_connection,gitlab_connection,branch_name}.py`.
- `apps/api/plane/app/views/agent/git.py`, `apps/api/plane/app/serializers/agent_git.py`, `apps/api/plane/app/urls/agent.py`.
- `apps/api/plane/bgtasks/agent_git_catalog_task.py`.
- Recorded GitLab responses (scrubbed of tokens, e-mails and `last_used_ips`): `apps/api/plane/tests/fixtures/gitlab/*.json` for version, token self (active, expired, revoked, missing scope, 404 from a pre-15.5 server), `/version` 403 `insufficient_scope` (from a `write_repository`-only token; record it, do not hand-write it) <!-- red-team 2026-11-12 gitlab -->, user (bot, human), group, member (Developer, Reporter), group projects (two pages, one foreign host).
- Tests: `apps/api/plane/tests/contract/app/test_agent_github_device_flow.py`, `test_agent_github_installations.py`, `test_agent_github_disconnect.py`, `test_agent_gitlab_connect.py`, `test_agent_gitlab_disconnect.py`, `test_agent_git_catalog.py`, `test_agent_repository_binding.py`, `test_agent_git_policy.py`; `apps/api/plane/tests/unit/test_agent_branch_name.py`, `test_agent_git_provider_contract.py` (one suite parametrized over GitHub and GitLab fakes); `apps/api/plane/tests/smoke/test_agent_gitlab_live.py` (read-only; uses the registered `smoke` marker plus `skipif` on `PLANE_TEST_GITLAB_TOKEN`, so no new marker is added under `--strict-markers`; <!-- red-team 2026-11-12 gitlab --> when `PLANE_TEST_GITLAB_REQUIRED=1` a missing token fails the module instead of skipping it).

Modify (backend):
- `apps/api/plane/app/urls/__init__.py` (register agent URLs).
- `apps/api/plane/utils/instance_config_variables/core.py` (GitHub App keys beside `:73`; new key names, see Key decisions). <!-- red-team 2026-11-12 -->
- `apps/api/plane/app/views/project/base.py:259-313` and `apps/api/plane/app/serializers/project.py:31` (accept optional `repository` on create; return binding with provider and availability).
- `apps/api/plane/utils/url_security.py:103-222` (`verify` parameter, default `True`); new cases in the existing `apps/api/plane/tests/unit/bg_tasks/test_url_security.py`.
- `apps/api/plane/settings/common.py:57-80` (shared allowlist parse helper; `AGENT_GIT_ALLOWED_HOSTS`, `AGENT_GIT_ALLOWED_IPS`).

Create (web):
- `packages/types/src/agent/git.ts`, `packages/constants/src/agent.ts` (provider labels and term keys).
- `apps/web/services/agent/git.service.ts`, `apps/web/store/agent/git.store.ts`, `apps/web/hooks/store/use-agent-git.ts`.
- `apps/web/components/settings/integrations/index-page.tsx`; `.../git/{provider-meta,detail-page,accounts-list,change-request-policy}.tsx` (shared by both providers); `.../git/github/{setup-card,device-flow}.tsx`; `.../git/gitlab/{setup-card,token-form}.tsx`.
- `apps/web/app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/integrations/github/page.tsx`, `.../integrations/gitlab/page.tsx`.
- `apps/web/components/projects/create/repository-section.tsx`.
- <!-- red-team 2026-11-12 --> Admin app (Q3 source): a GitHub App form beside the existing GitHub login form (`apps/admin/app/(all)/(dashboard)/authentication/github/form.tsx`, `apps/admin/components/authentication/github-config.tsx`), for example `apps/admin/components/authentication/github-app-config.tsx`; key types in `packages/types/src/instance/auth.ts` (modify). The instance PATCH (`plane/license/api/views/configuration.py:43-59`) updates only keys that already exist, so the keys must be in `core.py` first. GitLab has no instance-level key; its settings are per workspace.
- `packages/blocks/src/agent-run/repository-list.ts` (group by provider and owner, filter, availability logic) + `repository-list.test.ts`; `packages/blocks/src/agent-run/provider-terms.ts` + test; `packages/blocks/src/agent-run/index.ts`.
- `packages/i18n/src/locales/*/agent.json`.
- GitLab icon: use an icon from `@makeplane/propel/icons` if one exists; else add it to `packages/blocks/src/icons/` (exported as `@plane/blocks/icons`, `packages/blocks/package.json:31`) next to the GitHub icon the mockup uses. Check before coding; no literal colors.

Modify (web):
- `apps/web/app/routes/core.ts:258-285` (add `settings/integrations`, `settings/integrations/github`, `settings/integrations/gitlab`).
- `packages/constants/src/settings/workspace.ts:29-81` (add `integrations` tab, members read, admins write).
- `apps/web/app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/integrations/page.tsx` (replace legacy content and admin-only gate).
- `apps/web/components/projects/create/root.tsx` (render repository section, submit binding).
- `apps/web/store/root.store.ts`, `packages/types/src/index.ts`, `packages/blocks/package.json` (add `./agent-run` export).
- <!-- red-team 2026-11-12 --> `packages/types/src/settings.ts:13` (add `"integrations"` to `TWorkspaceSettingsTabs`); `apps/web/components/settings/workspace/sidebar/item-icon.tsx:19` (icon for `integrations`; the `Record` fails typecheck without it); `packages/constants/src/index.ts` (export `./agent`); `packages/i18n/src/constants/namespaces.ts:7-36` (add `"agent"`; a namespace missing here never loads and the UI shows raw keys, and `check:sync` does not detect it).

Do not modify: `apps/web/components/integration/github/*`, `apps/web/components/integration/slack/*`, legacy `plane/db/models/integration/github.py`.

## API endpoints (member, session auth)

| Method and path under `api/workspaces/<slug>/agent-git/` | Role | Story |
| --- | --- | --- |
| `GET connections/` (both providers, status, warnings, never tokens) | member read | 1.1, G1 |
| `POST github/device-authorizations/` (kind user or organization), `POST github/device-authorizations/<id>/poll/`, `POST github/device-authorizations/<id>/cancel/` | admin | 1.1, 1.2 |
| `POST gitlab/connection/` (base URL, group path, token, optional CA bundle) | admin | G1 |
| `GET <provider>/accounts/`, `POST github/accounts/sync/`, `POST <provider>/accounts/<id>/attach/` (GitHub only in practice), `DELETE <provider>/accounts/<id>/` (GitHub; GitLab returns 400 and points to Disconnect) | admin (list: member) | 1.2, 1.3, G2 |
| `DELETE <provider>/connection/` | admin | 1.4, G4 |
| `GET repositories/?provider=&search=&owner=&cursor=` | member, filtered by attached account and member access | 1.2, 1.5, G2, G3 |
| `GET <provider>/policy/`, `PATCH <provider>/policy/` | member read, admin write | 1.6-1.8, G5 |
| `POST api/workspaces/<slug>/projects/` with `repository` | existing create, extended | 1.5, G3 |

`<provider>` is `github` or `gitlab`; any other value returns 404.

## Tests Before (regression on touched surfaces)

1. Project create without `repository` returns the same 201 body as today (`test_project_app.py` stays green; add one explicit case).
2. Existing settings routes render for admin and member (typecheck of `routes/core.ts` and constants; vitest for any helper moved).
3. `pinned_fetch` callers keep behavior: the existing `plane/tests/unit/bg_tasks/test_url_security.py`, `test_ssrf_advisories.py` and `test_work_item_link_task.py` pass unchanged before and after the `verify` parameter is added; add one case that the default still verifies against system trust.
4. Webhook allowlist settings parse the same values before and after the parse helper is extracted (unit case with CIDR, invalid entry and hostnames).

<!-- red-team 2026-11-12 --> The former item 3 (non-admin 403 on GitHub write endpoints) tests new endpoints, so it moved to Tests After (1.1, 1.6).

## Refactor

Protected by Tests Before 1-4: extend `ProjectViewSet.create` (`plane/app/views/project/base.py:259`) and `ProjectSerializer` (`plane/app/serializers/project.py:31`) with an optional nested `repository`; replace the admin-only gate of the Integrations page with member read and admin write; add the `integrations` tab to `packages/constants/src/settings/workspace.ts`; add `verify` to `pinned_fetch`; extract the allowlist parse helper in `settings/common.py`. Behavior without `repository` and of existing `pinned_fetch` callers stays identical.

<!-- red-team 2026-11-12 --> `ProjectViewSet.create` today saves the project, members and states without a transaction (`base.py:262-296`; no `ATOMIC_REQUESTS`). With a repository, put project, members, states and binding in one `transaction.atomic` block, map `IntegrityError` on the binding to 409, and keep `model_activity.delay` after the block. `ProjectSerializer` uses `fields = "__all__"` (`project.py:35`): pop `repository` before `Project.objects.create`.

## Story steps and Tests After

All GitLab HTTP in tests uses the recorded responses in `plane/tests/fixtures/gitlab/` through a `mocker` patch of `git_providers/http.py`. No test outside `smoke` opens a network connection.

| Story | Steps | Tests After (write first, then implement) |
| --- | --- | --- |
| 1.1 | Neutral models, provider seam, device code start, poll with interval and expiry, cancel, token encrypt, refresh; setup card, device-flow card with URL, code, expiry, "I entered the code", Cancel; connected detail with back link | Contract: start, pending, success stores connection, expired, denied, cancelled creates no connection, token absent from responses and `caplog`; blocks vitest for expiry countdown label; browser: keyboard order and labels. <!-- red-team 2026-11-12 --> Also: member and guest get 403 on start, poll, cancel; two concurrent polls on one authorization give one connection and the row stays `completed`; empty ciphertext from `encrypt_data` does not set `connected`; empty decrypt of a stored token returns `reconnect_required` with no provider call; two concurrent refresh calls on an expired token cause one GitHub refresh call; App credentials accessor returns env when the DB row is empty and the DB value when set; the `caplog` check covers the provider http seam and service loggers and asserts Celery task arguments contain no token. Q10: demote `connected_by` to Member, then the next token use returns `reconnect_required` with `connected_admin_lost` and zero GitHub calls; the same for `is_active=false` (left or removed); `GET connections/` shows `reconnect_required` after demotion; another admin's reconnect restores `connected` with the new `connected_by` |
| 1.2 | Organization flow opens install URL, then installation sync as candidates; admin attach; idempotent upsert by installation ID | Contract: new org appears once as `candidate`; repeated sync no duplicate; cancel/deny leaves list unchanged; repository list filtered by member access. Q9: a candidate installation adds no repository to the catalog and cannot be bound (404); after admin attach its repositories appear; sync never changes `candidate` to `attached`; member attach 403 |
| 1.3 | Remove one installation with confirm (Plane-side detach, link to GitHub settings for uninstall); mark bindings from it unavailable | Contract: only target removed; binding kept with `available=false`; a failed detach (forced DB error) keeps the installation visible and returns an actionable error; detach, then sync: the installation stays `detached` and its binding stays `available=false` <!-- red-team 2026-11-12 --> |
| 1.4 | Disconnect with confirm; revoke this token at GitHub (`DELETE /applications/{client_id}/token`); clear tokens; keep history | Contract: list and change-request paths fail with `provider_disconnected` (provider `github`); bindings kept; GitHub failure returns error and keeps connection; <!-- red-team 2026-11-12 --> the revoke call targets the token endpoint, not the grant endpoint, and sends only this workspace's token. Expired access token is refreshed before revoke; 404 or invalid-token 422 from GitHub clears local tokens; a 5xx or network error keeps the connection. Q10: disconnect of a `reconnect_required` connection makes no GitHub call and clears tokens. A GitLab connection in the same workspace is unchanged. AC 2 for new Launches is tested in Phase 3 and for pending change-request delivery in Phase 7 |
| 1.5 | Repository section in create form: search, owner filter, provider groups, unavailable rows, selected state, no-repository warning, disconnected link; API stores one identity and base ref; no Mirror or clone | Contract: bind, duplicate bind 409, unavailable repo 409, no repo allowed, disconnected rejects; blocks vitest for grouping/filter/availability labels; browser: keyboard selection, 375 px, Light/Dark. <!-- red-team 2026-11-12 --> Also: catalog row of another workspace returns 404; client-supplied `clone_url`/`full_name`/`provider` are ignored and the stored values equal the catalog row; `base_ref` with leading `-`, `..` or a control character returns 400; omitted `base_ref` stores `default_branch`; concurrent binds of one repository give one 201 and one 409 and leave no project without its binding (`django_db(transaction=True)`, real threads); guest create stays 403 |
| 1.6 | Policy model per provider with `open_as_draft=true` default; switch row | Contract: default true, admin PATCH persists, member PATCH 403; browser: member sees disabled switch |
| 1.7 | `mirror_conclusions=false` default; switch row | Same three checks as 1.6 |
| 1.8 | `branch_format` enum and selector with both Run-unique labels | Unit: both formats, two Runs on one issue differ, invalid identifiers sanitized; contract: persist and reload. <!-- red-team 2026-11-12 --> AC 4 (a Run keeps its branch after a format change) needs a Run and is tested in Phase 7 (3.1) |
| G1 | GitLab connect form, connect checks in order, encrypted token, version, CA bundle, `verify` in `pinned_fetch`, operator allowlist, warnings | Contract: one test per AC1-AC10 with recorded responses; each failure stores nothing and returns its code; checks stop at the first failure <!-- red-team 2026-11-12 gitlab --> (no `/api/v4/version` call after a token failure; a 401 on `/personal_access_tokens/self` gives `gitlab_token_invalid`; a 404 on `self` followed by version `15.4.9-ee` gives `gitlab_version_unsupported`, and followed by non-JSON gives `gitlab_not_gitlab`; a `write_repository`-only token gives `gitlab_scope_missing` naming `api`; an unexpected status gives `gitlab_unexpected_response`, not 500); a response body over 1 MiB and a server that exceeds the 30 s budget fail with a code and store nothing; a base URL on the Plane request host is rejected; reconnect on the same base URL with another group sets the old group account `detached` and its bindings unavailable; token absent from responses and `caplog`; `gitlab_scope_missing` names `write_repository` for an `api`-only token; version parse of `18.10.3-ee`, `15.5.0`, `15.4.9-ee`, garbage; empty `encrypt_data` result does not set `connected`. Unit (`bg_tasks/test_url_security.py`, new cases): a CA path reaches the adapter; a second host in the same process still uses system trust; a TLS error maps to `gitlab_tls_failed`; DNS, timeout, refused, 3xx and private-IP cases map to their codes. Provider contract suite: GitHub and GitLab fakes return the same neutral `RepositoryInfo` shape. Smoke (`PLANE_TEST_GITLAB_TOKEN`, read-only): version, token self, user and one group projects page against git.oceanlabs.dev |
| G2 | GitLab catalog through the same task and swap rule | Contract: two pages give one snapshot; failure on page 2 keeps the old snapshot; foreign-host project skipped; subgroup projects included; member reads, guest 403 |
| G3 | GitLab rows in the repository section and bind | Contract: all 1.5 cases with a GitLab row; same numeric external ID on both providers binds twice; binding host equals connection host. Blocks vitest: provider grouping and icon label; browser: GitLab rows with keyboard |
| G4 | Revoke-free disconnect | Contract: no HTTP call (assert the http seam was not called); token cleared; bindings `available=false`; GitHub connection unchanged; reconnect with another base URL leaves old bindings unavailable; after reconnect a 403 from GitLab on one call leaves the connection `connected` and a 401 sets `reconnect_required` <!-- red-team 2026-11-12 gitlab -->. Browser: dialog text tells the admin to revoke in GitLab |
| G5 | Policy rows on the GitLab detail page with merge-request terms | Contract: GitLab and GitHub policies are independent; member 403. Blocks vitest: `provider-terms.ts` returns "merge request" for GitLab and "pull request" for GitHub in each policy label key |

## Verification

```bash
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app/test_agent_github_device_flow.py plane/tests/contract/app/test_agent_github_installations.py plane/tests/contract/app/test_agent_github_disconnect.py plane/tests/contract/app/test_agent_gitlab_connect.py plane/tests/contract/app/test_agent_gitlab_disconnect.py plane/tests/contract/app/test_agent_git_catalog.py plane/tests/contract/app/test_agent_repository_binding.py plane/tests/contract/app/test_agent_git_policy.py plane/tests/contract/app/test_project_app.py plane/tests/unit/test_agent_branch_name.py plane/tests/unit/test_agent_git_provider_contract.py
docker compose -f docker-compose-test.yml run --rm api-tests pytest plane/tests/unit/bg_tasks/test_url_security.py plane/tests/unit/bg_tasks/test_ssrf_advisories.py plane/tests/unit/bg_tasks/test_work_item_link_task.py   # pinned_fetch callers unchanged
docker compose -f docker-compose-test.yml run --rm api-tests python manage.py makemigrations --check --dry-run
cd apps/api && uv run ruff check . && uv run ruff format --check .   # host uv must equal required-version in apps/api/pyproject.toml
pnpm --filter=@plane/blocks test
pnpm turbo run check:types --filter=web --filter=@plane/blocks --filter=@plane/types --filter=@plane/constants
pnpm check:lint && pnpm check:format && pnpm --filter=@plane/i18n check:sync
# Optional live check, read-only (token from the secret store, never in a file or chat):
# red-team 2026-11-12 gitlab: the test skips when PLANE_TEST_GITLAB_TOKEN is unset, and a skip exits 0. PLANE_TEST_GITLAB_REQUIRED=1 makes the module fail instead of skip; -rs prints skip reasons. Evidence = "N passed" with 0 skipped.
docker compose -f docker-compose-test.yml run --rm -e PLANE_TEST_GITLAB_REQUIRED=1 -e PLANE_TEST_GITLAB_URL=https://git.oceanlabs.dev -e PLANE_TEST_GITLAB_GROUP -e PLANE_TEST_GITLAB_TOKEN api-tests pytest -rs plane/tests/smoke/test_agent_gitlab_live.py
```

Opt-in live checks (operator credentials): connect a real GitHub App, add and attach one organization, remove it, disconnect. Connect git.oceanlabs.dev with a Group Access Token, list the catalog, bind one project, disconnect. Record both in `reports/`. With only the personal test token, record the read-only smoke result and the `gitlab_token_not_bot` warning.

## Success criteria

- [ ] All Given/When/Then cases of 1.1-1.8 and G1-G5 pass with the tests above or recorded browser evidence.
- [ ] No token value appears in any API response, Run context or log line (asserted by test).
- [ ] Mockup rows I046-I057, I068-I071, I076, I077 pass browser review for GitHub, and the same rows pass with GitLab name, icon and terms; I070 has no clone progress.
- [ ] Existing project-create and `pinned_fetch` caller tests pass unchanged.
- [ ] The read-only GitLab smoke check passes against git.oceanlabs.dev (version 18.10.3-ee recorded), run with `PLANE_TEST_GITLAB_REQUIRED=1`; a skipped run does not count. <!-- red-team 2026-11-12 gitlab -->
- [ ] <!-- red-team 2026-11-12 --> 1.4 AC 2 and 1.8 AC 4 need a Run; they are listed as pending and close in Phases 3 and 7. G4 AC2 (change-request path) and G5 AC4 close in Phase 7.
- [ ] <!-- red-team 2026-11-12 --> The `makemigrations --check` line runs in the test container (local `manage.py` defaults to production settings and does not load `apps/api/.env`).

## Risks

| Risk | L x I | Mitigation |
| --- | --- | --- |
| No GitHub App credentials during development | High x Medium | Provider seam mocked in tests; live check is opt-in and blocks only the "done" mark, not the merge of tested code |
| Device flow for GitHub Apps needs "Enable Device Flow" on the App | Medium x High | Setup doc in README of `plane/agent/git_providers/`; start endpoint returns `device_flow_disabled` error with hint |
| Catalog refresh interrupted mid-pagination | Medium x Medium | Snapshot swap only after the last page; resume from saved page |
| "Available to that member" (1.2) has no per-member provider identity in the spec | Medium x Medium | V1 rule: a repository is available when its account is attached and the caller is a workspace Admin or Member who can create projects. Guests get 403. Confirmed by the user (decision Q8) |
| Admin-supplied GitLab base URL is a server-side request target (SSRF) | Medium x High | `pinned_fetch` resolves, validates and pins the IP; no redirects; private addresses blocked unless the operator allowlist names them; catalog rejects repository URLs on other hosts |
| Custom CA bundle weakens TLS for other hosts | Low x High | Bundle is per connection and passed as `verify` only for that host; unit test shows a second host keeps system trust |
| `/personal_access_tokens/self` behaviour with a Group Access Token is not documented | Low x Medium | Recorded responses cover the expected shape; the Group Access Token live check confirms it; marked `[UNVERIFIED]` until then |
| Only a personal GitLab token is available for testing | High x Low | Read-only smoke check only; writes wait for a Group Access Token (plan.md open question 2) |
| Personal token accepted with a warning attributes pushes to a person, and Plane cannot see when that person leaves | Medium x Medium | Warning on the detail page; any 401 sets `reconnect_required` (a 403 fails only that operation, see Key decisions); user decides warn or reject (plan.md open question 1) <!-- red-team 2026-11-12 gitlab --> |
| GitLab token expiry stops all GitLab work | Medium x Medium | Expiry shown with a 14-day warning; 401 sets `reconnect_required` with `gitlab_token_invalid` |
| Phase 1 grows from 8 to 13 stories in one PR | Medium x Medium | One commit per story; the PR can split after 1.8 (GitHub) and G1-G5 (GitLab) if review needs it; the neutral model lands with 1.1 either way |

## Rollback

Revert the PR. Run `uv run python manage.py migrate db 0125` (the last migration before this phase) before the revert on any database that applied the new migrations. New tables hold no data used by other features. The project create path accepts requests without `repository`, so old clients keep working. The `pinned_fetch` `verify` parameter defaults to `True`, so reverting it changes no existing caller. Stored GitLab tokens are deleted with the tables; tell admins to revoke them in GitLab.
