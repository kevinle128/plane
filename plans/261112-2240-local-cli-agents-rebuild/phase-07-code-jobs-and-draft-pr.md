---
phase: 7
title: "Code jobs and draft PR"
status: todo
priority: P1
effort: "14d"
dependencies: [1, 5]
---

# Phase 7: Code jobs and draft PR

## Goal

A member asks an existing Run to implement or fix. The Run becomes a Code job with its own Worktree and Run-unique branch, waits for a bounded Docker slot, asks permission before each protected effect, and delivers a draft pull request that a human merges. One PR, one commit per story 3.1-3.9.

Effort note: this is the largest phase. If the PR exceeds review capacity, split it in two PRs at the 3.5/3.6 boundary (3.1-3.5 effects and permission; 3.6-3.9 capacity, Stop/resume and mirroring). The split keeps one commit per story.

## Context links

- Stories: [epics.md:1275-1529](../2026-09-28-plane-local-cli-agents-epics/epics.md). Contracts: [architecture-contracts.md](./architecture-contracts.md) §3 (`AgentPermissionRequest`, `AgentCodeSlot`, `AgentRunPullRequest`, `AgentPrCommentMirror`), §9 (AD-8 exception), §10. Spine AD-6..AD-9, AD-11.
- Design: Screen 1 PR line, Screen 2 HITL permission card, capacity banner; scenes 5, 6, 9, 10.
- Prior evidence and lessons: [prior phase 4](../2026-09-28-plane-local-cli-agents-implementation/phase-04-code-jobs-and-draft-pr.md), [capacity](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-capacity-concurrency-progress.md), [command executor](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-command-executor-progress.md), [network boundary](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-network-boundary-progress.md), [Run grant](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-run-grant-acceptance.md), [denied effect](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-denied-effect-acceptance.md), [Code Stop](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-code-stop-acceptance.md), [Code resume](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-code-resume-progress.md), [worker foundation: commit, push, PR, mirror sections](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-worker-foundation-progress.md).

## Data flow (protected effect)

1. Harness calls a Plane MCP effect tool (`plane_write_file`, `plane_create_file`, `plane_run_command`, `plane_read_path`, `plane_network`, `plane_commit`, `plane_push`, `plane_open_pr`). The Harness has no native write or network route: the Q&A OS profile stays active on the Host process and the Code container has no credentials.
2. Worker normalizes the scope, computes `effect_hash`, and posts a permission request with Run, turn and lease generation.
3. Plane matches an existing Run grant (same action, scope inside the approved scope, same Run). If none, it stores `pending`, sets status `approval`, and the panel shows the card.
4. Member decides. Plane records decision, actor and time as a timeline event.
5. Worker polls, then calls `consume` (atomic, once). Plane rechecks lease, Stop and slot. Worker writes a journal record before execution.
6. Worker executes in the Code container. For file effects Docker produces the content and the Worker publishes it through pinned no-follow descriptors (AD-8 exception).
7. Worker reports the result with the request ID; Plane stores it; the journal record clears only after Plane confirms receipt. Recovery reports retained state and never replays.

## Key decisions

- Escalation: the MCP tool `plane_request_code_job` is available only on a turn whose input is a member message. Plane switches `kind=code`, sets `code_enqueued_at`, and puts the Run in the capacity wait. The card, timeline and Run ID stay the same.
- Worktree and branch: `<run_root>/<run_id>/clone` gets a Worktree at `<run_root>/<run_id>/worktree` on branch from `plane/agent/services/branch_name.py` (Phase 1). `branch_name` is unique in the database. `active_workspace=worktree` for every later turn. No pull or rebase while the Worktree is dirty.
- Capacity: `AgentCodeSlot` rows 1..N (`PLANE_AGENT_CODE_SLOTS`, default 2). Acquire with `select_for_update(skip_locked=True)` for the oldest waiting Run by (`code_enqueued_at`, `id`) that still has a valid repository grant. The Worker must hold a slot before `docker create`. Release only after the Worker confirms the container stopped. Stale slot recovery inspects the real container first. Q&A never takes a slot.
- Docker: one container per Code Run, non-root, no capabilities, memory, pids and CPU limits, network `none` by default. The active Worktree is the only writable bind mount (3.1 AC 7), and only an approved command runs against it. File-write tools produce content in a private scratch area, and the Worker publishes it (AD-8 exception). No Plane checkout, no Docker socket, no credentials. Task 1 of 3.1 re-probes this mount layout on the Mini's Docker Desktop version and records the result before any effect code.
- Network (3.4): grants pin literal IP and port sets; a namespace filter allows only the granted set. Hostname requests follow decision Q2: the user approves the hostname, the Worker resolves it at approval time and pins the resolved IP and port set; a changed IP needs a new decision (carried lesson).
- Push and PR: push uses Mini-held Git credentials only in the Worker, to `refs/heads/<branch_name>` with an expected-old-SHA lease; never the default branch. PR creation goes through Plane API with the GitHub connection token obtained through the locked refresh function in `github_connection.py` (Phase 1; refresh tokens are single-use) <!-- red-team 2026-11-12 -->, `draft` from `AgentGithubPolicy.open_as_draft`. Each of commit, push and PR needs its own grant (3.1 AC "does not use a prior file-write grant").
- Mirroring (3.9): when `mirror_conclusions=true` and the Run has a PR, the conclusion transaction creates `AgentPrCommentMirror(pending)`; a Celery task posts once after commit. A retry after an uncertain POST lists PR comments to find the existing one before any second POST. A minute beat entry recovers missed tasks.
- The effect conformance checks live in `plane_agent_worker/code/conformance_code.py` and run as the Code preflight. They do not edit `conformance.py` or `drivers/*` (Phase 6 ownership).

## Files

Create (backend): `apps/api/plane/agent/services/{permissions,capacity,code_job,pull_request,pr_mirror}.py`; `apps/api/plane/app/views/agent/permissions.py`; `apps/api/plane/bgtasks/agent_pr_mirror_task.py`; migrations `<next>_agent_permissions`, `<next>_agent_code_capacity`, `<next>_agent_pull_request` (generated); tests `test_agent_permission_request.py`, `test_agent_permission_run_grant.py`, `test_agent_permission_deny.py`, `test_agent_network_scope.py`, `test_agent_path_scope.py`, `test_agent_code_capacity.py`, `test_agent_code_stop_resume.py`, `test_agent_pull_request.py`, `test_agent_pr_mirror.py`.

Modify (backend): `apps/api/plane/agent/worker_api/views.py`, `apps/api/plane/app/views/agent/runs.py`, `apps/api/plane/agent/services/conclusion.py`, `apps/api/plane/agent/github/client.py` (create PR, list/post comments), `apps/api/plane/celery.py:46-101` (one beat entry for mirror recovery).

Create (Worker): `plane_agent_worker/code/{__init__,capacity,docker_sandbox,effects,journal,publish,git_ops,network,conformance_code}.py`; extend `mcp_server.py` with effect tools; `workspace.py` gains Worktree functions; tests `tests/test_effect_journal.py`, `tests/test_publish_descriptors.py`, `tests/test_git_ops.py`, `tests/test_code_capacity.py`, `tests/test_docker_sandbox.py` (`docker`), `tests/test_network_filter.py` (`docker`), `tests/test_code_turn.py`.

Create (web): `packages/blocks/src/agent-run/{permission-card.tsx,pr-card.tsx,capacity-banner.tsx,permission-scope.ts}` with tests; `apps/web/components/agent-run/{permission-request,pull-request-line}.tsx`.

Modify (web): `apps/web/components/agent-run/{timeline,run-card,panel-header}.tsx`, `apps/web/store/agent/run.store.ts`, `apps/web/services/agent/run.service.ts`, `packages/i18n/src/locales/*/agent.json`.

## API endpoints

| Path | Auth | Story |
| --- | --- | --- |
| `POST .../agent-runs/<id>/permissions/<pid>/decide/` (`allow_once`, `allow_run`, `deny`) | comment permission | 3.1-3.5 |
| `POST api/agent-worker/v1/runs/<id>/code-job/`, `POST .../permissions/`, `GET .../permissions/<pid>/`, `POST .../permissions/<pid>/consume/`, `POST .../permissions/<pid>/result/` | Worker token + lease | 3.1-3.5 |
| `POST api/agent-worker/v1/code-slots/acquire/`, `POST .../code-slots/<n>/release/`, `POST .../code-slots/<n>/reconcile/` | Worker token | 3.6, 3.7 |
| `POST api/agent-worker/v1/runs/<id>/pull-request/` (Plane creates PR with GitHub token after grant) | Worker token + lease | 3.1 |

## Tests Before

1. All Phase 3-5 Q&A tests pass; Q&A Runs never take a slot.
2. Branch name unit tests from Phase 1 pass.
3. Policy read tests from Phase 1 pass (Worker reads the same values).

## Refactor

Protected by Tests Before 1-3: `conclusion.py` gains the PR line and mirror record inside the same transaction; `github/client.py` gains PR and comment calls behind the same seam; `plane/celery.py` gains one beat entry; `workspace.py` gains Worktree functions without changing clone functions.

## Story steps and Tests After

| Story | Steps | Tests After |
| --- | --- | --- |
| 3.1 | Escalation, Worktree, branch, first-write permission, Allow once, Docker boundary, auth preflight, commit/push/PR grants, draft policy, delivery failure, two Runs on one issue | API: escalation keeps Run ID and card; permission card fields present; Allow once consumed once and second consume 409; push needs its own grant; draft follows policy; PR failure keeps branch and claims no PR; <!-- red-team 2026-11-12 --> GitHub disconnected before PR delivery: PR step fails with `github_disconnected`, branch kept, no PR claimed (1.4 AC 2, epics.md:472); workspace `branch_format` changed after the Run owns a branch: the Run keeps its existing `branch_name` on later turns and resume (1.8 AC 4, epics.md:588); Worker: preflight auth failure starts no container; publish via descriptors rejects symlink and replaced parent; no pull/rebase on dirty Worktree; `docker`: container sees only Worktree, no checkout, no credentials, limits applied; blocks vitest: card keyboard order and labels |
| 3.2 | Allow for this Run, scope matching | API: later in-scope request auto-granted with linked audit; broader path, network, action or other Run asks again |
| 3.3 | Deny | API: decision recorded; consume of denied 409; changed effect gets a new request; Worker: denial delivered to Harness as event, file unchanged |
| 3.4 | Network escalation with pinned scope | API: scope hash includes IPs and ports; changed IP needs new decision; `docker`: allowed endpoint reachable, others blocked, UDP blocked |
| 3.5 | Path escalation | API: normalized path shown; Plane checkout and symlink escape rejected at request; Worker: only approved path and operation available within grant lifetime |
| 3.6 | Capacity wait, FIFO, slot before Docker, stale slot reconcile, Q&A exempt | API: concurrent acquire never exceeds N (threaded test); order by enqueue time and ID; revoked-grant head skipped; Worker: reconcile inspects container before release; browser: scene 9 banner |
| 3.7 | Code Stop | Worker: interrupts Harness and container, clears queue; Worktree, branch, PR kept; slot released after container stop; waiting Run takes the slot |
| 3.8 | Code resume | Worker: launches in same Worktree after new slot; same branch and active CWD; missing Worktree, changed remote or revoked grant gives visible error and no launch |
| 3.9 | PR comment mirroring | API: mirroring off posts nothing; on posts once and stores comment ID; retry after uncertain POST finds existing comment; GitHub rejection records failure and work-item conclusion unchanged |

## Verification

```bash
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app -k "agent_permission or agent_network or agent_path or agent_code or agent_pull_request or agent_pr_mirror"
docker compose -f docker-compose-test.yml run --rm api-tests python manage.py makemigrations --check --dry-run
cd apps/api && uv run ruff check .
cd apps/agent-worker && uv run pytest -m "not native and not docker"
cd apps/agent-worker && uv run pytest -m docker   # needs Docker
cd apps/agent-worker && uv run pytest -m native tests/test_code_turn.py   # Mini only
pnpm --filter=@plane/blocks test && pnpm turbo run check:types --filter=web --filter=@plane/blocks
pnpm check:lint && pnpm --filter=@plane/i18n check:sync
```

Live check (operator GitHub App and a test repository): one Code job from mention to draft PR, with Allow once, Allow for this Run, Deny, Stop, resume and mirroring on. Record in `reports/`.

## Success criteria

- [ ] All Given/When/Then cases of 3.1-3.9 pass.
- [ ] Denied, pending, mismatched and stale grants cause no protected effect (contract and Worker tests).
- [ ] Docker never exceeds N Code containers under 3 concurrent Workers and 6 waiting Runs (load test recorded).
- [ ] The Agent cannot push to or merge into the default branch (Git test with a protected local remote).
- [ ] Mockup rows I037-I042, I045 pass browser review.

## Risks

| Risk | L x I | Mitigation |
| --- | --- | --- |
| Docker Desktop on macOS cannot prove bind-mount identity | High x High | AD-8 exception: content produced in Docker, published by the Worker through pinned descriptors |
| Uncertain effect after Worker crash | Medium x High | Journal before consume; result receipt before clear; recovery reports, never replays; new user command required |
| DNS answer changes after approval | Medium x Medium | Pinned IP set; a changed IP needs a new decision (Q2) |
| No live GitHub App during development | High x Medium | Client seam mocked; live check blocks the "done" mark only |
| Slot leak after container crash | Medium x High | Reconcile inspects real container before release; slot rows are finite and visible |

## Rollback

Revert the PR and migrate `db` back to the last Phase 5 migration. Before rollback, Stop all Code Runs and confirm no Code container runs (`docker ps --filter label=plane.agent.run`). Worktrees and branches stay on disk and on GitHub for manual review.
