---
title: "Local CLI Agents rebuild on current preview"
description: "Rebuild all 43 Local CLI Agents stories, plus self-hosted GitLab parity, on current preview in seven PR-sized, test-first phases."
status: pending
priority: P1
effort: "67d"
branch: feat/local-cli-agents
tags: [feature, backend, frontend, worker, github, gitlab, security]
blockedBy: []
blocks: []
created: 2026-11-12
---

# Local CLI Agents rebuild on current preview

## Overview

Rebuild the Git provider connection (GitHub and self-hosted GitLab), four local Harness Agents, durable Q&A Runs and safe Code jobs with draft pull requests (GitHub) or draft merge requests (GitLab) on current `preview`. No agent code exists in this worktree. The prior plan is reference only. Mode: hard, `--tdd`. Scope: HOLD (deliver all 43 stories and the 7 plan-level GitLab stories G1-G7, add nothing).

- Shared contracts, verified codebase facts, carried decisions and lessons: [architecture-contracts.md](./architecture-contracts.md)
- Story-to-phase table and mockup scenes: [story-coverage.md](./story-coverage.md)
- GitLab scope (user-accepted 2026-11-12): [gitlab-scope-decisions.md](./gitlab-scope-decisions.md). The GitLab acceptance criteria are plan-level (epics.md covers GitHub only): G1-G5 in [Phase 1](./phase-01-github-connection-and-repository.md#gitlab-stories-and-acceptance-criteria), G6-G7 in [Phase 7](./phase-07-code-jobs-and-draft-pr.md#gitlab-stories-and-acceptance-criteria).

## Scope challenge

- Existing code: bot users, Fernet helpers, instance config, entity search, mention extension point, activity feed, resizable sidebar pattern, `@plane/blocks` vitest. Legacy GitHub sync models and the unrouted Integrations page are not reused as-is.
- Requested scope: 43 stories in [epics.md](../2026-09-28-plane-local-cli-agents-epics/epics.md) plus GitLab parity ([gitlab-scope-decisions.md](./gitlab-scope-decisions.md)). Nothing deferred.
- Extension trace (provider boundary): GitHub and GitLab are two real cases, so one small provider interface (`GitProviderClient`, six methods) is justified. There is no registry, plugin loader or provider config layer. Details and proof: [architecture-contracts.md §11](./architecture-contracts.md#11-git-provider-boundary-and-extension-trace).
- Complexity: more than 3 phases because one PR per prior phase would carry 9-26 stories; seven phases keep each PR reviewable.

## Prior phase to new phase

| Prior phase | New phases | Epic |
| --- | --- | --- |
| 1 GitHub and repository | 1 | Epic 1 |
| 2 Run control plane and UI + 3 Four-harness Worker | 2, 3, 4, 5, 6 | Epic 2 |
| 4 Code jobs and draft PR | 7 | Epic 3 |

## Phases

| # | Phase | Stories | Depends on | Status |
|---|-------|---------|------------|--------|
| 1 | [Git provider connection (GitHub and GitLab) and project repository](./phase-01-github-connection-and-repository.md) | 1.1-1.8 (8), G1-G5 (5) | none | Pending |
| 2 | [Agent settings and Claude connection](./phase-02-agent-settings-and-claude-connection.md) | 2.1-2.6 (6) | 1 | Pending |
| 3 | [Claude Q&A Run and durable timeline](./phase-03-claude-qa-run-and-timeline.md) | 2.7-2.8 (2) | 1, 2 | Pending |
| 4 | [Run context and conversation](./phase-04-run-context-and-conversation.md) | 2.9-2.13 (5) | 3 | Pending |
| 5 | [Steering, Stop and stale recovery](./phase-05-steering-stop-and-stale-recovery.md) | 2.14-2.20 (7) | 4 | Pending |
| 6 | [Codex, Grok and Omp Harnesses](./phase-06-codex-grok-and-omp-harnesses.md) | 2.21-2.26 (6) | 5 | Pending |
| 7 | [Code jobs and draft pull or merge request](./phase-07-code-jobs-and-draft-pr.md) | 3.1-3.9 (9), G6-G7 (2) | 1, 5 | Pending |

Effort: 11d + 6d + 9d + 6d + 8d + 10d + 17d = 67d. GitLab adds 5d to Phase 1, 1d to Phase 3 and 3d to Phase 7 compared with the GitHub-only plan (58d).

Order: 1, 2, 3, 4, 5, then 6 and 7 in either order. They run one after the other, not in parallel: their Worker files are disjoint (`drivers/{codex,grok,omp}.py` vs `code/*`), but both add keys to `packages/i18n/src/locales/*/agent.json`. Each phase branches from `preview` after the previous merge because each PR regenerates `apps/api/migrations_lockfile.txt`.

## Delivery rules

One PR per phase to `preview`; one commit per story; no plan IDs in code, tests, migrations or commits; COPYRIGHT header on new `.py/.ts/.tsx`; all locales carry new i18n keys. Details: [architecture-contracts.md §8](./architecture-contracts.md).

## Success criteria

- [ ] Every Given/When/Then case of all 43 stories and of GitLab stories G1-G7 passes with a test or recorded live/browser evidence.
- [ ] The provider contract suite (`test_agent_git_provider_contract.py`) passes for GitHub and GitLab with recorded responses; the GitLab live read-only check passes against git.oceanlabs.dev when `PLANE_TEST_GITLAB_TOKEN` is set.
- [ ] The 65 changed mockup rows pass browser review in Light and Dark at 375, 768 and 1280 px.
- [ ] API, Worker, web, migration, copyright and i18n checks pass in every phase PR.
- [ ] Q&A cannot write; Code effects need a matching grant; Docker never exceeds N slots; the Agent cannot push or merge to the default branch or a protected branch on either provider.
- [ ] No provider token appears in an API response, Run context, log line, git argv, process environment, remote URL or `.git/config` (asserted by tests).

## User decisions (2026-11-12)

The user accepted all recommended answers on 2026-11-12.

1. Q1, disposable runtime: accepted. Each Codex, Grok and Omp turn gets a private runtime directory outside the clone. Only that process can write to it, and the Worker deletes it after the turn. The clone, credentials and other Runs stay read-only. This is an accepted exception to AD-7. Phase 6 is unblocked.
2. Q2, network grants by hostname (3.4): the user approves a hostname. At approval time the Worker resolves the hostname and pins the resolved IP and port set. If the IP changes later, the Worker asks for a new decision.
3. Q3, GitHub App: the user registers the GitHub App. The client ID, secret and slug come from instance configuration (admin app). When the instance configuration is empty, the values come from environment variables.
4. Q4, Phase 7 size: Phase 7 can split into two PRs at the 3.5/3.6 boundary.
5. Q5, browser tests: no Playwright in CI. UI logic is tested with Vitest in `packages/blocks`. Each phase has a manual browser check script and records its evidence in the phase report.
6. Q6, Worker CI: add a CI job for `apps/agent-worker` that runs ruff and the unit tests.
7. Q7, hard-link probe: if the probe reads foreign content, the Worker provides the read, list and search tools instead of native Harness reads.
8. Q8, repository availability (1.2): a repository is available to a member when the workspace grant is active and the member can create projects. Members have no GitHub identity of their own.
9. Q9, installation attachment (red-team F13, decided 2026-11-12): the admin explicitly selects which GitHub installations (organisations or accounts) attach to the workspace. Sync shows installations as candidates only. An unselected installation never attaches, and sync never attaches one. GitLab equivalent: one token is bound to one group that the admin names on connect; that group is the single attached account.
10. Q10, connecting admin leaves (red-team F14, decided 2026-11-12): when the admin whose GitHub token backs the connection leaves the workspace or loses the Admin role, Plane marks the GitHub connection `reconnect_required` and stops using that token. Another admin reconnects. GitLab: not applicable, because a Group Access Token belongs to a group bot user, not to a workspace member. (See open question 1 for personal GitLab tokens.)

## GitLab facts and provisional choices

- Target instance git.oceanlabs.dev runs GitLab 18.10.3-ee (read with a test token on 2026-11-12). Details: [gitlab-scope-decisions.md](./gitlab-scope-decisions.md).
- Minimum supported GitLab version: 15.5. Reason: `GET /api/v4/personal_access_tokens/self` was introduced in 15.5, and the connect check needs it for scopes, expiry and active state. All other GitLab APIs in this plan are older (group access tokens 14.7, `Draft:` title prefix 13.2, `members/all/:user_id` 12.4). Sources: [architecture-contracts.md §11](./architecture-contracts.md#11-git-provider-boundary-and-extension-trace).
- Provisional (coordinator recommendation, not yet a user decision): a personal access token is accepted with a warning, not rejected. See open question 1.

## Open questions (need the user)

1. Personal GitLab token. The accepted scope says Group Access Token. The only test token now is a personal token of a human user (`bot=false`, scope `api`, no expiry). The plan warns and accepts it (pushes and merge requests then appear as that person, and Q10 has no GitLab equivalent: Plane notices that the person lost access only when GitLab returns 401 or 403). Keep warn, or reject non-bot tokens?
2. Live write check. The Phase 7 live check (push, draft merge request, merge-request note) needs a Group Access Token with role Developer and scopes `api` and `write_repository` on a test group of git.oceanlabs.dev. Can the user create one and put it in the secret store? Without it, Phase 7 G6/G7 close on recorded responses only, and the live check stays open.
3. Subgroups. Do the projects on git.oceanlabs.dev sit directly in the token's group or in subgroups? The plan lists group projects with `include_subgroups=true` by default; confirm or choose top level only.
4. Scope of the `api` token for Git push. GitLab docs list `write_repository` for Git-over-HTTPS push ("not using the API"); the plan requires `api` and `write_repository`. The current test token has `api` only, so the connect check reports `gitlab_scope_missing` for it. This is correct per the docs; confirm that the real token will carry both scopes.

## Red Team Review

### Session — 2026-11-12
**Findings:** 15 (13 accepted and applied, 2 surface-to-user; 0 rejected). Report: [reports/red-team-261112-local-cli-agents-rebuild.md](./reports/red-team-261112-local-cli-agents-rebuild.md)
**Severity breakdown:** 0 Critical, 4 High, 11 Medium
**Method note:** one reviewer applied all four lenses (no subagent tool in this run). The lead's brief authorised direct edits for findings that do not touch user decisions. No user decision Q1-Q8 was changed.

| # | Finding | Severity | Disposition | Applied To |
|---|---------|----------|-------------|------------|
| F1 | Project create plus binding not atomic; bind race gives 500 and an orphan project | High | Accept | Phase 1 Refactor, 1.5 |
| F2 | Binding trusts client repository fields; `base_ref` reaches git unvalidated | High | Accept | Phase 1 Key decisions, 1.5 |
| F3 | Single-use GitHub refresh tokens; concurrent refresh breaks connection | High | Accept | Phase 1 Key decisions, 1.1; Phase 7 Key decisions |
| F4 | Grant revoke disconnects other workspaces; expired token must not block revoke | Medium | Accept | Phase 1 Key decisions, 1.4 |
| F5 | `encrypt_data`/`decrypt_data` return `""` on error | Medium | Accept | Phase 1 Key decisions, 1.1 |
| F6 | Q3 env fallback differs from `get_configuration_value` semantics | Medium | Accept (implements Q3) | Phase 1 Key decisions, Files, 1.1 |
| F7 | Files list misses settings union, icon map, i18n namespace, constants export, admin form | Medium | Accept | Phase 1 Files |
| F8 | Uninstall needs App JWT; detach must survive the next sync | Medium | Accept | Phase 1 Key decisions, 1.3 |
| F9 | Device-flow poll has no concurrency guard | Medium | Accept | Phase 1 Key decisions, 1.1 |
| F10 | Phase 3 pytest command with two `-k` skips agent contract tests | Medium | Accept | Phase 3 Verification |
| F11 | 1.4 AC 2 and 1.8 AC 4 have no test in any phase | Medium | Accept | Phase 3 2.7, Phase 7 3.1, story-coverage, Phase 1 Success criteria |
| F12 | Local `makemigrations --check` needs CI env; run in test container | Medium | Accept | Phases 1-5, 7 Verification; architecture-contracts §7 |
| F13 | Installation scoping: connecting admin's token decides what all members can bind | High | Decided by user 2026-11-12 (Q9) | Phase 1 Key decisions, 1.2, G1 |
| F14 | Connection outlives the admin who connected it | Medium | Decided by user 2026-11-12 (Q10) | Phase 1 Key decisions, 1.1, 1.4 |
| F15 | Tests Before 3 is not a regression test; log assertion scope | Medium | Accept | Phase 1 Tests Before, 1.1 |

### Whole-Plan Consistency Sweep
- Files reread: plan.md, phase-01 to phase-07, architecture-contracts.md, story-coverage.md
- Decision deltas checked: 11 (sync keeps detach, concurrency test DB mode, installation removal semantics, revoke endpoint, refresh locking, binding input source, `base_ref` rule, Q3 accessor, makemigrations command location, pytest `-k` split, deferred 1.4/1.8 ACs)
- Reconciled stale references: 8 (Phase 1 1.3 and 1.4 rows, Tests Before 1-3 reference, two `app/(all)` paths without the `apps/web/` prefix, makemigrations lines in Phases 2, 3, 4, 5, 7 and architecture-contracts §7, Phase 7 PR token source)
- Unresolved contradictions: 0. F13 and F14 were decided by the user on 2026-11-12 (Q9, Q10).
- GitLab scope (2026-11-12, after this review): Phase 1 now uses the provider-neutral model and ships GitHub and GitLab; Phases 3, 4, 5 and 7 use the provider boundary in [architecture-contracts.md §11](./architecture-contracts.md#11-git-provider-boundary-and-extension-trace). Every red-team fix F1-F12 and F15 is kept on the neutral model; F3, F4, F6 and F8 stay GitHub-only. The red-team gate has not run on the GitLab additions. Rerun it on Phase 1 before implementation; the new attack surface is listed in Phase 1 Risks (admin-supplied base URL, custom CA, token handout to the Worker).
