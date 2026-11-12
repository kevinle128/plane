---
title: "Local CLI Agents rebuild on current preview"
description: "Rebuild all 43 Local CLI Agents stories on current preview in seven PR-sized, test-first phases."
status: pending
priority: P1
effort: "58d"
branch: feat/local-cli-agents
tags: [feature, backend, frontend, worker, github, security]
blockedBy: []
blocks: []
created: 2026-11-12
---

# Local CLI Agents rebuild on current preview

## Overview

Rebuild GitHub connection, four local Harness Agents, durable Q&A Runs and safe Code jobs with draft PRs on current `preview`. No agent code exists in this worktree. The prior plan is reference only. Mode: hard, `--tdd`. Scope: HOLD (deliver all 43 stories, add nothing).

- Shared contracts, verified codebase facts, carried decisions and lessons: [architecture-contracts.md](./architecture-contracts.md)
- Story-to-phase table and mockup scenes: [story-coverage.md](./story-coverage.md)

## Scope challenge

- Existing code: bot users, Fernet helpers, instance config, entity search, mention extension point, activity feed, resizable sidebar pattern, `@plane/blocks` vitest. Legacy GitHub sync models and the unrouted Integrations page are not reused as-is.
- Requested scope: 43 stories in [epics.md](../2026-09-28-plane-local-cli-agents-epics/epics.md). Nothing deferred.
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
| 1 | [GitHub connection and project repository](./phase-01-github-connection-and-repository.md) | 1.1-1.8 (8) | none | Pending |
| 2 | [Agent settings and Claude connection](./phase-02-agent-settings-and-claude-connection.md) | 2.1-2.6 (6) | 1 | Pending |
| 3 | [Claude Q&A Run and durable timeline](./phase-03-claude-qa-run-and-timeline.md) | 2.7-2.8 (2) | 1, 2 | Pending |
| 4 | [Run context and conversation](./phase-04-run-context-and-conversation.md) | 2.9-2.13 (5) | 3 | Pending |
| 5 | [Steering, Stop and stale recovery](./phase-05-steering-stop-and-stale-recovery.md) | 2.14-2.20 (7) | 4 | Pending |
| 6 | [Codex, Grok and Omp Harnesses](./phase-06-codex-grok-and-omp-harnesses.md) | 2.21-2.26 (6) | 5, decision Q1 | Pending |
| 7 | [Code jobs and draft PR](./phase-07-code-jobs-and-draft-pr.md) | 3.1-3.9 (9) | 1, 5 | Pending |

Order: 1, 2, 3, 4, 5, then 6 and 7 in either order (7 first if Q1 is still open). They run one after the other, not in parallel: their Worker files are disjoint (`drivers/{codex,grok,omp}.py` vs `code/*`), but both add keys to `packages/i18n/src/locales/*/agent.json`. Each phase branches from `preview` after the previous merge because each PR regenerates `apps/api/migrations_lockfile.txt`.

## Delivery rules

One PR per phase to `preview`; one commit per story; no plan IDs in code, tests, migrations or commits; COPYRIGHT header on new `.py/.ts/.tsx`; all locales carry new i18n keys. Details: [architecture-contracts.md §8](./architecture-contracts.md).

## Success criteria

- [ ] Every Given/When/Then case of all 43 stories passes with a test or recorded live/browser evidence.
- [ ] The 65 changed mockup rows pass browser review in Light and Dark at 375, 768 and 1280 px.
- [ ] API, Worker, web, migration, copyright and i18n checks pass in every phase PR.
- [ ] Q&A cannot write; Code effects need a matching grant; Docker never exceeds N slots; the Agent cannot push or merge to the default branch.

## Open questions (user decisions)

1. Q1: Accept a per-Run, per-turn disposable runtime directory for Codex, Grok and Omp (exception to AD-7)? Blocks Phase 6.
2. Q2: Hostname/DNS approval flow for network grants (3.4)? Literal-IP flow ships without it.
3. Q3: Who registers the GitHub App, and do its client ID, secret and slug come from instance configuration (admin app) or environment?
4. Q4: Phase 7 split into two PRs if it grows beyond review size?
5. Q5: Add committed browser e2e tooling (for example Playwright), or keep recorded browser evidence per phase?
6. Q6: Add a CI job for `apps/agent-worker` (ruff + unit tests)?
7. Q7: If the hard-link probe fails, adopt Worker-side read/list/search tools (prior repair) instead of native Harness reads?
8. Q8: Is "repositories available to that member" (1.2) satisfied by workspace grant plus project-create role, with no per-member GitHub identity?
