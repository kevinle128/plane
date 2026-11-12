---
phase: 7
title: "Code jobs and draft pull or merge request"
status: todo
priority: P1
effort: "17d"
dependencies: [1, 5]
---

# Phase 7: Code jobs and draft pull or merge request

## Goal

A member asks an existing Run to implement or fix. The Run becomes a Code job with its own Worktree and Run-unique branch, waits for a bounded Docker slot, asks permission before each protected effect, and delivers a draft change request that a human merges: a pull request on GitHub, a merge request on GitLab. All provider calls go through `GitProviderClient` ([architecture-contracts.md §11](./architecture-contracts.md#11-git-provider-boundary-and-extension-trace)); the Worker uses `git_transport.py` for clone and push. One PR, one commit per story 3.1-3.9, then G6 and G7.

The file name keeps `draft-pr` so that existing links stay valid. "Change request" in this file means a pull request or a merge request.

Effort note: this is the largest phase. If the PR exceeds review capacity, split it in two PRs at the 3.5/3.6 boundary (3.1-3.5 effects and permission; 3.6-3.9, G6, G7 capacity, Stop/resume, mirroring and GitLab delivery). The split keeps one commit per story. GitLab adds 3d (provider methods, credential handout, protected-ref checks, G6/G7 tests).

## Context links

- Stories: [epics.md:1275-1529](../2026-09-28-plane-local-cli-agents-epics/epics.md); GitLab stories G6-G7 [below](#gitlab-stories-and-acceptance-criteria) (plan-level, [gitlab-scope-decisions.md](./gitlab-scope-decisions.md)). Contracts: [architecture-contracts.md](./architecture-contracts.md) §3 (`AgentPermissionRequest`, `AgentCodeSlot`, `AgentRunChangeRequest`, `AgentChangeRequestCommentMirror`), §9 (AD-8 exception), §10, §11 (provider boundary). Spine AD-6..AD-9, AD-11.
- Design: Screen 1 PR line, Screen 2 HITL permission card, capacity banner; scenes 5, 6, 9, 10. GitLab reuses the PR line with the GitLab icon and "Merge request !<iid>".
- Prior evidence and lessons: [prior phase 4](../2026-09-28-plane-local-cli-agents-implementation/phase-04-code-jobs-and-draft-pr.md), [capacity](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-capacity-concurrency-progress.md), [command executor](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-command-executor-progress.md), [network boundary](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-network-boundary-progress.md), [Run grant](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-run-grant-acceptance.md), [denied effect](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-denied-effect-acceptance.md), [Code Stop](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-code-stop-acceptance.md), [Code resume](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-code-resume-progress.md), [worker foundation: commit, push, PR, mirror sections](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-worker-foundation-progress.md).

## Data flow (protected effect)

1. Harness calls a Plane MCP effect tool (`plane_write_file`, `plane_create_file`, `plane_run_command`, `plane_read_path`, `plane_network`, `plane_commit`, `plane_push`, `plane_open_change_request`). The Harness has no native write or network route: the Q&A OS profile stays active on the Host process and the Code container has no credentials.
2. Worker normalizes the scope, computes `effect_hash`, and posts a permission request with Run, turn and lease generation.
3. Plane matches an existing Run grant (same action, scope inside the approved scope, same Run). If none, it stores `pending`, sets status `approval`, and the panel shows the card.
4. Member decides. Plane records decision, actor and time as a timeline event.
5. Worker polls, then calls `consume` (atomic, once). Plane rechecks lease, Stop and slot. Worker writes a journal record before execution.
6. Worker executes in the Code container. For file effects Docker produces the content and the Worker publishes it through pinned no-follow descriptors (AD-8 exception).
7. Worker reports the result with the request ID; Plane stores it; the journal record clears only after Plane confirms receipt. Recovery reports retained state and never replays.

## Data flow (push and change request)

1. When the Worker posts the `plane_push` permission request, Plane calls `GitProviderClient.is_protected_ref(repository, branch_name)` before it stores the request (no row lock is held during this HTTP call) and records the result on the request. A protected result stores the request as refused with `protected_ref`; the card shows the reason and offers no Allow. At consume, Plane checks without HTTP that `branch_name` differs from the snapshot `default_branch` and that the recorded result is not protected, so consume stays a database-only atomic step.
2. GitLab only (`credential_mode=plane_token`): the Worker calls `POST runs/<id>/git-credential/` with purpose `push` and the consumed grant ID. Plane checks lease, grant and purpose, then returns the token from `usable_token(connection)`. GitHub (`credential_mode=host`) skips this step.
3. Worker pushes `refs/heads/<branch_name>` only, with an expected-old-SHA lease, through `git_transport.py` (credential helper on a pipe, CA bundle scoped to the base URL). Transport failures report a fixed `git_*` code.
4. `plane_open_change_request` grant is consumed. Plane calls `create_change_request` with source `branch_name`, target `base_ref`, title, body, and `draft` from the Run policy snapshot. GitLab sets the `Draft: ` title prefix; both read the `draft` flag back and store it in `AgentRunChangeRequest`.
5. Conclusion with `mirror_conclusions=true` creates `AgentChangeRequestCommentMirror(pending)`; the Celery task posts once through `post_comment` (GitHub issue comment, GitLab merge-request note).

## Key decisions

- Escalation: the MCP tool `plane_request_code_job` is available only on a turn whose input is a member message. Plane switches `kind=code`, sets `code_enqueued_at`, and puts the Run in the capacity wait. The card, timeline and Run ID stay the same.
- Worktree and branch: `<run_root>/<run_id>/clone` gets a Worktree at `<run_root>/<run_id>/worktree` on branch from `plane/agent/services/branch_name.py` (Phase 1). `branch_name` is unique in the database. `active_workspace=worktree` for every later turn. No pull or rebase while the Worktree is dirty.
- Capacity: `AgentCodeSlot` rows 1..N (`PLANE_AGENT_CODE_SLOTS`, default 2). Acquire with `select_for_update(skip_locked=True)` for the oldest waiting Run by (`code_enqueued_at`, `id`) that still has a valid repository grant. The Worker must hold a slot before `docker create`. Release only after the Worker confirms the container stopped. Stale slot recovery inspects the real container first. Q&A never takes a slot.
- Docker: one container per Code Run, non-root, no capabilities, memory, pids and CPU limits, network `none` by default. The active Worktree is the only writable bind mount (3.1 AC 7), and only an approved command runs against it. File-write tools produce content in a private scratch area, and the Worker publishes it (AD-8 exception). No Plane checkout, no Docker socket, no credentials. Task 1 of 3.1 re-probes this mount layout on the Mini's Docker Desktop version and records the result before any effect code.
- Network (3.4): grants pin literal IP and port sets; a namespace filter allows only the granted set. Hostname requests follow decision Q2: the user approves the hostname, the Worker resolves it at approval time and pins the resolved IP and port set; a changed IP needs a new decision (carried lesson).
- Push and change request: push runs only in the Worker, to `refs/heads/<branch_name>` with an expected-old-SHA lease; never the default branch and never a protected branch (Plane checks `is_protected_ref` when the push request is created, compares with `default_branch` at consume, and the Worker refuses any refspec other than `refs/heads/<branch_name>`; the provider rejects a push to a protected ref server-side as a second guard, reported as `git_push_rejected`). Credentials per `credential_mode`: GitHub uses Mini-held Git credentials; GitLab uses the connection token handed out per consumed push grant over HTTPS with the connection CA bundle (architecture-contracts §11). Change-request creation goes through Plane API with `usable_token(connection)`: for GitHub this is the locked refresh function in `github_connection.py` (Phase 1; refresh tokens are single-use) <!-- red-team 2026-11-12 --> with the Q10 admin check; for GitLab it is the decrypted group token. `draft` comes from the Run policy snapshot (`AgentGitPolicy.open_as_draft` of the binding's provider). Each of commit, push and change request needs its own grant (3.1 AC "does not use a prior file-write grant").
- Mirroring (3.9, G7): when `mirror_conclusions=true` and the Run has a change request, the conclusion transaction creates `AgentChangeRequestCommentMirror(pending)`; a Celery task posts once after commit. Each mirrored body carries a hidden marker with the mirror ID (`<!-- plane-agent-mirror:<id> -->`). `[UNVERIFIED]` that GitLab hides HTML comments in merge-request notes: the GitLab live check confirms it; if the marker renders, move it to a short visible footer line (`Plane Run <short_id>`) and search for that line instead. A retry after an uncertain POST calls `find_comment` with that marker before any second POST. A minute beat entry recovers missed tasks.
- GitLab token use by the Worker: the token has scope `api`, which is broader than push needs, and GitLab has no narrower per-push credential. Limits: handed out only per consumed `push` grant or per clone/fetch of a leased Run, held in memory for one git command, never given to the Harness or the container (tests below).
- <!-- red-team 2026-11-12 gitlab --> Git metadata outside the container's reach: the Worktree root is the container's writable bind mount, and it holds the `.git` file (`gitdir: <clone>/.git/worktrees/<name>`). A Code container can rewrite that file to point at a directory it controls, with a `config` that sets `credential.helper=!<cmd>`, `core.hooksPath`, `core.fsmonitor` or a filter driver. The Worker then runs `git commit` or `git push` on the Host, with the GitLab token on the helper pipe or the Mini-held GitHub credentials in reach, and the attacker command runs on the Mini. Rule: every Worker git command on a Worktree passes `--git-dir=<clone>/.git/worktrees/<name>` and `--work-tree=<worktree>` from Run state (never discovery through the `.git` file), plus `-c core.hooksPath=/dev/null -c core.fsmonitor=false` and the Phase 3 transport options. Before commit and push the Worker checks that the `.git` file content equals the value it wrote at Worktree creation; a difference fails the effect with `worktree_tampered` and runs no git command. The clone directory and `.git/worktrees/<name>` are never mounted into the container.
- The effect conformance checks live in `plane_agent_worker/code/conformance_code.py` and run as the Code preflight. They do not edit `conformance.py` or `drivers/*` (Phase 6 ownership).

## Files

Create (backend): `apps/api/plane/agent/services/{permissions,capacity,code_job,change_request,change_request_mirror}.py`; `apps/api/plane/app/views/agent/permissions.py`; `apps/api/plane/bgtasks/agent_change_request_mirror_task.py`; migrations `<next>_agent_permissions`, `<next>_agent_code_capacity`, `<next>_agent_change_request` (generated); recorded GitLab responses for project, protected branches, merge request create (draft and non-draft), notes list and create, 401, 403 and 409 in `apps/api/plane/tests/fixtures/gitlab/`; tests `test_agent_permission_request.py`, `test_agent_permission_run_grant.py`, `test_agent_permission_deny.py`, `test_agent_network_scope.py`, `test_agent_path_scope.py`, `test_agent_code_capacity.py`, `test_agent_code_stop_resume.py`, `test_agent_change_request.py`, `test_agent_change_request_mirror.py`, `test_agent_git_credential.py`.

Modify (backend): `apps/api/plane/agent/worker_api/views.py`, `apps/api/plane/app/views/agent/runs.py`, `apps/api/plane/agent/services/conclusion.py`, `apps/api/plane/agent/git_providers/{base,github,gitlab}.py` (the four Phase 7 methods of §11), `apps/api/plane/tests/unit/test_agent_git_provider_contract.py` (same suite, new methods), `apps/api/plane/celery.py:46-101` (one beat entry for mirror recovery); `apps/api/plane/tests/smoke/test_agent_gitlab_live.py` (write check, skipped unless `PLANE_TEST_GITLAB_GAT` is set).

Create (Worker): `plane_agent_worker/code/{__init__,capacity,docker_sandbox,effects,journal,publish,git_ops,network,conformance_code}.py`; extend `mcp_server.py` with effect tools; `workspace.py` gains Worktree functions; `git_ops.py` pushes through `git_transport.py` (Phase 3) with purpose `push`; tests `tests/test_effect_journal.py`, `tests/test_publish_descriptors.py`, `tests/test_git_ops.py`, `tests/test_git_push_credentials.py`, `tests/test_code_capacity.py`, `tests/test_docker_sandbox.py` (`docker`), `tests/test_network_filter.py` (`docker`), `tests/test_code_turn.py`.

Create (web): `packages/blocks/src/agent-run/{permission-card.tsx,change-request-card.tsx,capacity-banner.tsx,permission-scope.ts}` with tests (the card uses `provider-terms.ts` from Phase 1); `apps/web/components/agent-run/{permission-request,change-request-line}.tsx`.

Modify (web): `apps/web/components/agent-run/{timeline,run-card,panel-header}.tsx`, `apps/web/store/agent/run.store.ts`, `apps/web/services/agent/run.service.ts`, `packages/i18n/src/locales/*/agent.json`.

## API endpoints

| Path | Auth | Story |
| --- | --- | --- |
| `POST .../agent-runs/<id>/permissions/<pid>/decide/` (`allow_once`, `allow_run`, `deny`) | comment permission | 3.1-3.5 |
| `POST api/agent-worker/v1/runs/<id>/code-job/`, `POST .../permissions/`, `GET .../permissions/<pid>/`, `POST .../permissions/<pid>/consume/`, `POST .../permissions/<pid>/result/` | Worker token + lease | 3.1-3.5 |
| `POST api/agent-worker/v1/code-slots/acquire/`, `POST .../code-slots/<n>/release/`, `POST .../code-slots/<n>/reconcile/` | Worker token | 3.6, 3.7 |
| `POST api/agent-worker/v1/runs/<id>/change-request/` (Plane creates the pull or merge request with `usable_token` after the grant) | Worker token + lease | 3.1, G6 |
| `POST api/agent-worker/v1/runs/<id>/git-credential/` (purpose `push` with a consumed push grant; GitLab only, 400 for `credential_mode=host`) | Worker token + lease | 3.1, G6 |

## Tests Before

1. All Phase 3-5 Q&A tests pass; Q&A Runs never take a slot.
2. Branch name unit tests from Phase 1 pass.
3. Policy read tests from Phase 1 pass (Worker reads the same values).
4. Provider contract suite from Phase 1 (`test_agent_git_provider_contract.py`) and the Phase 3 `git_transport.py` tests (fetch credential, CA scope, error codes) pass.

## Refactor

Protected by Tests Before 1-4: `conclusion.py` gains the change-request line and mirror record inside the same transaction; `git_providers/{github,gitlab}.py` gain the Phase 7 methods behind the same seam and pass the same contract suite; `git_transport.py` gains purpose `push` without changing fetch; `plane/celery.py` gains one beat entry; `workspace.py` gains Worktree functions without changing clone functions.

## Story steps and Tests After

| Story | Steps | Tests After |
| --- | --- | --- |
| 3.1 | Escalation, Worktree, branch, first-write permission, Allow once, Docker boundary, auth preflight, commit/push/PR grants, draft policy, delivery failure, two Runs on one issue | API: escalation keeps Run ID and card; permission card fields present; Allow once consumed once and second consume 409; push needs its own grant; draft follows policy; change-request failure keeps branch and claims no change request; <!-- red-team 2026-11-12 --> GitHub disconnected before delivery: the change-request step fails with `provider_disconnected` (provider `github`), branch kept, none claimed (1.4 AC 2, epics.md:472); Q10: connecting admin demoted before delivery gives `provider_reconnect_required` and no GitHub call; a push request for a ref matching a protected rule is stored refused with `protected_ref` and offers no Allow; consume for a ref equal to the snapshot default branch returns `protected_ref`; `is_protected_ref` is not called inside the consume transaction (assert no HTTP while the row lock is held); GitHub check for a branch that does not exist yet returns a result, not a 404 failure; workspace `branch_format` changed after the Run owns a branch: the Run keeps its existing `branch_name` on later turns and resume (1.8 AC 4, epics.md:588); Worker: preflight auth failure starts no container; refspec other than `refs/heads/<branch_name>` refused before git runs; publish via descriptors rejects symlink and replaced parent; no pull/rebase on dirty Worktree; `docker`: container sees only Worktree, no checkout, no credentials, limits applied; blocks vitest: card keyboard order and labels |
| 3.2 | Allow for this Run, scope matching | API: later in-scope request auto-granted with linked audit; broader path, network, action or other Run asks again |
| 3.3 | Deny | API: decision recorded; consume of denied 409; changed effect gets a new request; Worker: denial delivered to Harness as event, file unchanged |
| 3.4 | Network escalation with pinned scope | API: scope hash includes IPs and ports; changed IP needs new decision; `docker`: allowed endpoint reachable, others blocked, UDP blocked |
| 3.5 | Path escalation | API: normalized path shown; Plane checkout and symlink escape rejected at request; Worker: only approved path and operation available within grant lifetime |
| 3.6 | Capacity wait, FIFO, slot before Docker, stale slot reconcile, Q&A exempt | API: concurrent acquire never exceeds N (threaded test); order by enqueue time and ID; revoked-grant head skipped; Worker: reconcile inspects container before release; browser: scene 9 banner |
| 3.7 | Code Stop | Worker: interrupts Harness and container, clears queue; Worktree, branch, change request kept; slot released after container stop; waiting Run takes the slot |
| 3.8 | Code resume | Worker: launches in same Worktree after new slot; same branch and active CWD; missing Worktree, changed remote or revoked grant gives visible error and no launch |
| 3.9 | Change-request comment mirroring | API: mirroring off posts nothing; on posts once and stores comment ID; retry after uncertain POST finds existing comment by marker; GitHub rejection records failure and work-item conclusion unchanged |
| G6 | GitLab draft merge request delivery | See [G6](#g6-deliver-a-draft-merge-request-from-a-code-job) ACs. API (recorded responses): draft on gives title `Draft: <title>` and stored `draft=true` read from the response; draft off gives no prefix; a title that already starts with `Draft:` is not prefixed twice; target is `base_ref`; protected default branch and wildcard rule (`release/*`) store the push request refused with `protected_ref`; 401 sets `provider_reconnect_required`; 403 or 409 on create keeps the branch and claims no merge request; disconnected GitLab fails with `provider_disconnected` (provider `gitlab`, closes G4 AC2); Run on a GitLab project reads the GitLab policy, not the GitHub one (closes G5 AC4); `git-credential` refuses without lease, without a consumed push grant, for an old lease generation, and for a GitHub Run. Worker: push against the local HTTPS test remote with a self-signed CA succeeds only with the bundle; token absent from argv and environment of the git process (recorded by the Phase 3 git shim, not a `ps` sample) <!-- red-team 2026-11-12 gitlab -->, remote URL, `.git/config`, Run events and logs; the Harness environment and the container environment contain no token; transport failures map to `git_*` codes; <!-- red-team 2026-11-12 gitlab --> a container-side rewrite of the Worktree `.git` file (to a gitdir with `credential.helper=!touch <marker>` and a `pre-commit` hook) makes commit and push fail with `worktree_tampered`, the marker file is never created, and the git shim shows `--git-dir` and `--work-tree` on every Worker git call; GitLab `is_protected_ref` reads every page of `protected_branches` (fixture with 25 rules, the matching rule on page 2) |
| G7 | GitLab conclusion mirroring to the merge request | See [G7](#g7-mirror-a-run-conclusion-to-its-merge-request) ACs. API (recorded responses): note posted once with the marker; retry after an uncertain POST lists notes and finds the marker, no second POST; GitLab rejection records failure and the work-item conclusion is unchanged; mirroring off posts nothing |

## Verification

```bash
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app -k "agent_permission or agent_network or agent_path or agent_code or agent_change_request or agent_git_credential"
docker compose -f docker-compose-test.yml run --rm api-tests python manage.py makemigrations --check --dry-run
docker compose -f docker-compose-test.yml run --rm api-tests pytest plane/tests/unit/test_agent_git_provider_contract.py
cd apps/api && uv run ruff check .
cd apps/agent-worker && uv run pytest -m "not native and not docker"
cd apps/agent-worker && uv run pytest -m docker   # needs Docker
cd apps/agent-worker && uv run pytest -m native tests/test_code_turn.py   # Mini only
pnpm --filter=@plane/blocks test && pnpm turbo run check:types --filter=web --filter=@plane/blocks
pnpm check:lint && pnpm --filter=@plane/i18n check:sync
```

Live check (operator GitHub App and a test repository): one Code job from mention to draft PR, with Allow once, Allow for this Run, Deny, Stop, resume and mirroring on. Record in `reports/`.

GitLab live check (needs a Group Access Token with role Developer and scopes `api`, `write_repository` on a test group of git.oceanlabs.dev; plan.md open question 2): one Code job from mention to draft merge request with mirroring on; confirm `/personal_access_tokens/self` works with the Group Access Token and remove the `[UNVERIFIED]` mark in Phase 1. Gated test (same container and guard as Phase 1; a skip exits 0, so `PLANE_TEST_GITLAB_REQUIRED=1` turns a missing token into a failure) <!-- red-team 2026-11-12 gitlab -->: `docker compose -f docker-compose-test.yml run --rm -e PLANE_TEST_GITLAB_REQUIRED=1 -e PLANE_TEST_GITLAB_URL -e PLANE_TEST_GITLAB_GROUP -e PLANE_TEST_GITLAB_GAT api-tests pytest -rs plane/tests/smoke/test_agent_gitlab_live.py -k write`. Record in `reports/`. Without that token, G6 and G7 close on recorded responses and the live item stays open.

## Success criteria

- [ ] All Given/When/Then cases of 3.1-3.9 and G6-G7 pass.
- [ ] Denied, pending, mismatched and stale grants cause no protected effect (contract and Worker tests).
- [ ] Docker never exceeds N Code containers under 3 concurrent Workers and 6 waiting Runs (load test recorded).
- [ ] The Agent cannot push to or merge into the default branch or a protected branch on either provider (Git test with a protected local remote; `protected_ref` contract tests for GitHub and GitLab).
- [ ] No GitLab token reaches the Harness, the container, git argv or environment, a remote URL, `.git/config`, a Run event or a log (Worker and API tests).
- [ ] Mockup rows I037-I042, I045 pass browser review.

## Risks

| Risk | L x I | Mitigation |
| --- | --- | --- |
| Docker Desktop on macOS cannot prove bind-mount identity | High x High | AD-8 exception: content produced in Docker, published by the Worker through pinned descriptors |
| Uncertain effect after Worker crash | Medium x High | Journal before consume; result receipt before clear; recovery reports, never replays; new user command required |
| DNS answer changes after approval | Medium x Medium | Pinned IP set; a changed IP needs a new decision (Q2) |
| No live GitHub App during development | High x Medium | Client seam mocked; live check blocks the "done" mark only |
| No Group Access Token for live GitLab writes | High x Medium | Recorded responses and the local HTTPS remote cover G6/G7; the live write check blocks only the "done" mark (plan.md open question 2) |
| GitLab token in the Worker has scope `api` (broader than push) | Medium x High | Handed out only per consumed push grant or leased fetch; memory only for one git command; never to Harness or container; tests assert absence in argv, env, URL, config, events, logs |
| Protected-branch rules change between check and push | Low x Medium | Push only to the Run-unique `refs/heads/<branch_name>` with an expected-old-SHA lease; GitLab and GitHub enforce their own protection server-side as a second guard |
| GitLab draft by title prefix: a project template or user edit removes it | Low x Low | `draft` is read back from the create response and shown as stored; the human owns the merge request after creation |
| Slot leak after container crash | Medium x High | Reconcile inspects real container before release; slot rows are finite and visible |

## Rollback

Revert the PR and migrate `db` back to the last Phase 5 migration. Before rollback, Stop all Code Runs and confirm no Code container runs (`docker ps --filter label=plane.agent.run`). Worktrees and branches stay on disk and on GitHub or GitLab for manual review. Open draft pull or merge requests stay open; humans close them.

## GitLab stories and acceptance criteria

Plan-level stories under [gitlab-scope-decisions.md](./gitlab-scope-decisions.md). Each is one commit after 3.9. Mockup rows reused: I037-I041 (PR line with GitLab name, icon and "merge request" terms), I052 (consumer).

### G6. Deliver a draft merge request from a Code job

- AC1: Given a Code job on a project bound to a GitLab repository and the GitLab policy "Open as draft merge request" is on, when the member approves commit, push and open-change-request, then the Worker pushes only `refs/heads/<branch_name>` over HTTPS with the connection token and CA bundle, and Plane creates a merge request from that branch to `base_ref` whose title starts with `Draft: `; the Run card shows "Draft merge request !<iid>" with its link.
- AC2: Given the draft policy is off, then the merge request is created without the prefix and shown as ready.
- AC3: Given the branch name equals the default branch or matches a protected-branch rule, then the push request is refused with `protected_ref`, the card shows the reason, and nothing is pushed.
- AC4: Given GitLab returns an error on create or the token is invalid, then the branch is kept, no merge request is claimed, and the Run shows the reason (`provider_reconnect_required` for 401).
- AC5: The Agent never merges a merge request; no Plane code path calls a merge API.
- AC6: The token never reaches the Harness, the Code container, git argv or environment, the remote URL, `.git/config`, a Run event or a log.

### G7. Mirror a Run conclusion to its merge request

- AC1: Given "Mirror conclusions to the merge request" is on and the Run has a merge request, when the Run concludes, then Plane posts one note with the conclusion to that merge request and stores the note ID.
- AC2: Given the note POST result is uncertain, when the task retries, then it finds the existing note by its marker and posts no second note.
- AC3: Given GitLab rejects the note, then the mirror records the failure and the work-item conclusion is unchanged.
- AC4: Given mirroring is off, then no note is posted.
