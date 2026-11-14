---
title: "Local CLI Agents rebuild on current preview"
description: "Rebuild all 43 Local CLI Agents stories, plus self-hosted GitLab parity, on current preview in seven PR-sized, test-first phases."
status: in-progress
priority: P1
effort: "60.5d"
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
- Extension trace (provider boundary): GitHub and GitLab are two real cases, so one small provider interface (`GitProviderClient`, five methods) is justified. There is no registry, plugin loader or provider config layer. Details and proof: [architecture-contracts.md §11](./architecture-contracts.md#11-git-provider-boundary-and-extension-trace).
- Complexity: more than 3 phases because one PR per prior phase would carry 9-26 stories; seven phases keep each PR reviewable.

## Prior phase to new phase

| Prior phase                                        | New phases    | Epic   |
| -------------------------------------------------- | ------------- | ------ |
| 1 GitHub and repository                            | 1             | Epic 1 |
| 2 Run control plane and UI + 3 Four-harness Worker | 2, 3, 4, 5, 6 | Epic 2 |
| 4 Code jobs and draft PR                           | 7             | Epic 3 |

## Phases

| #   | Phase                                                                                                                | Stories                    | Depends on | Effort | Status  |
| --- | -------------------------------------------------------------------------------------------------------------------- | -------------------------- | ---------- | ------ | ------- |
| 1   | [Git provider connection (GitHub and GitLab) and project repository](./phase-01-github-connection-and-repository.md) | 1.1-1.8 (8), G1-G5 (5)     | none       | 11d    | Pending |
| 2   | [Agent settings and Claude connection](./phase-02-agent-settings-and-claude-connection.md)                           | 2.1-2.6 (6)                | 1          | 8d     | Pending |
| 3   | [Claude Q&A Run and durable timeline](./phase-03-claude-qa-run-and-timeline.md)                                      | 2.7-2.8 (2)                | 1, 2       | 9d     | Pending |
| 4   | [Run context and conversation](./phase-04-run-context-and-conversation.md)                                           | 2.9-2.13 (5)               | 3          | 6d     | Pending |
| 5   | [Steering, Stop and stale recovery](./phase-05-steering-stop-and-stale-recovery.md)                                  | 2.14-2.20 (7)              | 4          | 7.5d   | Pending |
| 6   | [Codex and Omp Harnesses (Grok dropped, Q25)](./phase-06-codex-grok-and-omp-harnesses.md)                            | 2.21, 2.22, 2.25, 2.26 (4) | 5          | 7d     | Pending |
| 7   | [Code jobs and draft pull or merge request](./phase-07-code-jobs-and-draft-pr.md)                                    | 3.1-3.9 (9), G6-G7 (2)     | 1, 5, 6    | 10d    | Pending |

Effort (re-estimated 2026-11-14 after decisions Q17-Q24): 11d + 8d + 9d + 6d + 7.5d + 9d + 10d = 60.5d (was 67d).

- Phase 2: +2d (6d planned plus the remaining Q18/Q21 work in [Phase 2 remaining work](./phase-02-agent-settings-and-claude-connection.md#remaining-work-to-pr-readiness-2026-11-14)).
- Phase 3: unchanged 9d. The Q18 Run-time version check and the Q24 MCP config replace the boundary work that Q16 moved into Phase 2.
- Phase 5: -0.5d (Q19: no Claude midturn injection path).
- Phase 6: -1d (Q20 and Q23 save about 2.5d; the restored outer profile for Grok and Omp, the Codex read and `apply_patch` proof and the Grok route check add about 1.5d).
- Phase 7: -7d (Q22: no Docker sandbox, no slot pool, no per-effect cards, no file-publish path; the Code-job approval, the Code-mode boundary per Harness and the Worker commit add about 2d).
- GitLab adds 5d to Phase 1, 1d to Phase 3 and 3d to Phase 7 compared with a GitHub-only plan.

Order: 1, 2, 3, 4, 5, 6, 7. <!-- 2026-11-14 --> Phase 7 now depends on Phase 6: the Code mode of Codex, Grok and Omp uses their Phase 6 drivers and boundaries (Q22). Both phases also add keys to `packages/i18n/src/locales/*/agent.json`. Each phase branches from `preview` after the previous merge because each PR regenerates `apps/api/migrations_lockfile.txt`.

## Delivery rules

One PR per phase to `preview`; one commit per story; no plan IDs in code, tests, migrations or commits; COPYRIGHT header on new `.py/.ts/.tsx`; all locales carry new i18n keys. Details: [architecture-contracts.md §8](./architecture-contracts.md).

## Success criteria

- [ ] Every Given/When/Then case of all 43 stories and of GitLab stories G1-G7 passes with a test or recorded live/browser evidence.
- [ ] The provider contract suite (`test_agent_git_provider_contract.py`) passes for GitHub and GitLab with recorded responses; the GitLab live read-only check passes against git.oceanlabs.dev when `PLANE_TEST_GITLAB_TOKEN` is set.
- [ ] The 65 changed mockup rows pass browser review in Light and Dark at 375, 768 and 1280 px. Exception (Q22, 2026-11-14): I040 ("Allow for this run" button) is removed; I039, I041 and I045 are reviewed in their Q22 form ([story-coverage.md](./story-coverage.md#q22-effect-on-epic-3-and-mockup-rows-2026-11-14)).
- [ ] API, Worker, web, migration, copyright and i18n checks pass in every phase PR.
- [ ] Q&A cannot write. A Code job writes only inside its Worktree and only after its Code-job approval. Push and change-request creation each need their own approval. A Worker never runs more Code turns at once than its configured limit. The Agent cannot push or merge to the default branch or a protected branch on either provider. (Changed 2026-11-14 by Q22.)
- [ ] No provider token appears in an API response, Run context, log line, git argv, the environment of the Harness process or of a command in its sandbox, remote URL or `.git/config` (asserted by tests).

## User decisions (2026-11-12)

The user accepted all recommended answers on 2026-11-12.

1. Q1, disposable runtime: accepted. Each Codex, Grok and Omp turn gets a private runtime directory outside the clone. Only that process can write to it, and the Worker deletes it after the turn. The clone, credentials and other Runs stay read-only. This is an accepted exception to AD-7. Phase 6 is unblocked.
2. Q2, network grants by hostname (3.4) <!-- 2026-11-14 --> (superseded by Q22 when the user confirms the Code-job network proposal; until then it has no consumer, because Q22 removes the network card): the user approves a hostname. At approval time the Worker resolves the hostname and pins the resolved IP and port set. If the IP changes later, the Worker asks for a new decision.
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

## GitLab decisions (2026-11-12)

The user accepted the recommended answers on 2026-11-12. The answer came through a Paseo agent message that relayed the user's choice.

11. Q11, personal GitLab token: warn and accept. The connect screen says that pushes and merge requests appear as that person.
12. Q12, live write check: the user creates a Group Access Token (role Developer, scopes `api` and `write_repository`) on a test group before Phase 7. Phase 7 stops and asks for it before its live write check.
13. Q13, subgroups: the repository catalog includes subgroup projects (`include_subgroups=true`).
14. Q14, token scopes: the connect check requires both `api` and `write_repository`. The current test token has `api` only, so it is used only for read-only checks.
15. Q15, connect error detail: one code `gitlab_url_not_allowed_or_unresolved` for a name that does not resolve and for a blocked address. The other connect codes stay unchanged.

## Claude sandbox decision (2026-11-13)

16. Q16, Claude Q&A boundary: the user chose Claude Code's built-in sandbox instead of the outer OS sandbox around the whole `claude` process. This applies to the Claude Harness only; Codex, Grok and Omp keep decision Q1.
    - Bash commands and their child processes run in Claude Code's built-in sandbox (OS-level, filesystem and network isolation). Writes are denied everywhere; reads of other Runs, the Worker token, credentials and other session folders are denied (`sandbox.filesystem.denyRead`).
    - Built-in file tools (Edit, Write, NotebookEdit) are denied by permission rules; Read is limited to the Run clone by permission rules. MCP servers and hooks are turned off for Runs (no MCP config, no hooks, restricted setting sources).
    - The `claude` process itself runs outside the boundary, so it writes its own session history normally and `--resume` works without an exception.
    - This replaces, for Claude only, the AD-4/AD-7 rule "Q&A writes are denied at the OS boundary": file-tool denial is enforced by Claude Code's permission system, not by the OS. The probe's permission check changes from "write denied under the OS boundary" to "Edit/Write denied by permission rule and a Bash write denied by the built-in sandbox".
    - Accepted trade-off (user, 2026-11-13): weaker isolation for Claude's own file tools, MCP and hooks than an outer OS sandbox, in exchange for no session-folder exception and simpler setup.
    - <!-- 2026-11-14 --> Amendment 1 (Phase 2 finding, implemented in `apps/agent-worker/plane_agent_worker/drivers/claude_boundary.py:14-19`): "writes are denied everywhere" has one narrow exception. Sandboxed Bash can write Claude Code's own temporary folder, because the Bash tool keeps its shell state there and every Bash command fails without it. The Worker sets `CLAUDE_CODE_TMPDIR` and `TMPDIR` to the private `tmp` folder of the probe or Run (`drivers/claude.py:108-113`); without that variable Claude Code uses `/tmp/claude-<uid>`. The folder is outside the clone and is removed with the probe or Run. An `Edit` deny rule wider than the working directory also denies this folder (`claude_boundary.py:30-32`), so the rule stays limited to the working directory.
    - <!-- 2026-11-14 --> Amendment 2 (Q24): "MCP servers are turned off for Runs" changes to "user MCP servers stay off; only the Worker-supplied Plane MCP server runs". Each Run turn gets `--strict-mcp-config --mcp-config <generated file>` with that one server. Hooks stay off. The probe and the per-version suite use no MCP server.

## Multica comparison decisions (2026-11-14)

Source: [reports/research-multica-agent-integration.md](./reports/research-multica-agent-integration.md) (simplifications S1-S5, spec items F1-F7). The user decided Q18-Q24 on 2026-11-14. Q17 was decided on 2026-11-13 and is recorded here because no earlier section had it. Each item names the spec rule or story it changes; the phase files carry the per-criterion detail.

17. Q17, Worker access (decided 2026-11-13; closes Phase 2 review finding F2 as an accepted risk): no workspace allowlist for the Worker and no rate limit on Connect or Retry. Reason: the instance is reachable only through Tailscale, so only trusted people can sign up and create workspaces. Revisit before any public exposure of the instance (then add an instance allowlist that Connect and `claim_probe` both check, and a Connect throttle per workspace). Spec effect: none; this records a deployment assumption. Details: [Phase 2 risks](./phase-02-agent-settings-and-claude-connection.md#risks).
18. Q18, connection check (S1; reading of AD-4 accepted by the user): Connect and Retry run a quick check only: CLI found, `--version`, login status and model list. The behavior conformance suite (the seven AD-4 checks) runs once per CLI version and its result is cached per (Harness, CLI version, suite version) on the Worker. A Connect on a version without a passing cached result runs the suite in the same probe. A Run on a version without a passing cached result runs the suite before its first turn; it does not fail at once. Reason: Claude Code native installs "automatically update in the background" and an update takes effect "the next time you start Claude Code" ([code.claude.com/docs/en/setup](https://code.claude.com/docs/en/setup), sections "Update Claude Code" and "Auto-updates"), so a version change without operator action is the normal case. Failing the Run would break every Run after each update until an admin selects Retry in every workspace. Running the suite first costs about 25-35 s once per version and keeps the AD-4 rule that no Run uses an unverified version. A failed suite fails that Run with `harness_version_unverified` and the failed check, and sets that Agent's connection to Connection failed. Spec effect: AD-4 (reading, accepted); stories 2.1, 2.21, 2.23, 2.25 (Connect is fast; the suite result can come from the cache). Details: [Phase 2](./phase-02-agent-settings-and-claude-connection.md#key-decisions), [Phase 3](./phase-03-claude-qa-run-and-timeline.md#key-decisions), [Phase 6](./phase-06-codex-grok-and-omp-harnesses.md#key-decisions).
19. Q19, Claude Send now (S2 option a): Send now for Claude cancels the current turn, waits for the process to exit, then sends the message as the next turn (AD-5 fallback). No hook-based midturn injection. The Claude driver reports `midturn_input=false` and does not measure it. Spec effect: none (2.15 AC 2, epics.md:1005-1007, is the path for Claude; AC 1 applies to Codex and Omp only). Details: [Phase 5](./phase-05-steering-stop-and-stale-recovery.md#key-decisions).
20. Q20, Codex runtime directory (S4): the Q1 private runtime directory for Codex is a per-Run `CODEX_HOME` with a Worker-written `config.toml`. Spec effect: none (this is how Q1 is implemented). Details: [Phase 6](./phase-06-codex-grok-and-omp-harnesses.md#key-decisions).
21. Q21, model listing (S3): one control request per CLI. Claude: one `initialize` control request in a one-shot process, with a static fallback list. Codex: `model/list`, with `codex debug models` as fallback. Spec effect for the Claude static fallback: it changes 2.1 AC 5 (epics.md:621-623, "rather than a hard-coded model list") and 2.6 AC 3 (epics.md:735-737, "no mock model is presented as verified"). The plan keeps both criteria as close as possible: the suite still requires a real model report for each version, the fallback applies only when the Connect-time request fails, and the selector labels fallback models as not reported by the CLI. This needs user confirmation (open question 6). Details: [Phase 2](./phase-02-agent-settings-and-claude-connection.md#key-decisions).
22. Q22, Code jobs (research F1, F3, and F2 kept): one approval per Code job instead of a permission card per effect. The agent works in its own CLI sandbox inside the per-job Worktree (Claude: built-in sandbox in Code mode, per Q16; Codex: its own `workspace-write` sandbox; Grok and Omp: the Q1 outer profile in Code mode). Approval is asked again only before push and before opening the pull or merge request. The Worker (not the agent) commits and pushes; Plane opens the draft change request; provider tokens never reach the agent. The Docker slot pool (AD-11) is dropped; a simple limit of concurrent Code turns per Worker stays, with the durable visible waiting state. Command network: proposal "deny all command network; the CLI process itself still reaches its model host", which needs user confirmation (open question 7). Spec effect: AD-7 (Code boundary is the CLI sandbox, not Docker), AD-8 (per-effect requests and the file-publish exception removed), AD-11 (slot pool removed, waiting state kept); stories 3.1-3.8 and G6 change, 3.9 and G7 do not. Per-criterion table: [Phase 7 spec deviations](./phase-07-code-jobs-and-draft-pr.md#spec-deviations-q22-2026-11-14).
23. Q23, Codex Q&A boundary (research F4): Codex Q&A uses Codex's own sandbox in `read-only` mode with `approval_policy = "never"`, the same model as Q16 for Claude. The Phase 6 connection check must prove that Codex cannot write under that mode, including `apply_patch`, and that it cannot read the Worker token, other Runs or credential stores. Spec effect: AD-7 "read-only OS boundary" for Codex (same exception as Q16 gives Claude). Grok and Omp keep Q1 with the outer profile. Details: [Phase 6](./phase-06-codex-grok-and-omp-harnesses.md#key-decisions).
24. Q24, Harness questions (S5 rejected): keep the structured question card (`plane_ask_question`, `AgentRunQuestion(kind=harness)`) and the "Waiting for you" state as specified. Consequence: Runs need the Plane MCP server, so Q16 is amended (amendment 2 above). Spec effect: none on epics.md; it fixes the conflict between Q16 and the Phase 3 data flow. Details: [Phase 3](./phase-03-claude-qa-run-and-timeline.md#key-decisions), [Phase 4](./phase-04-run-context-and-conversation.md).

Also from the research (F7, information only): Multica runs Grok through ACP (`grok agent stdio`), while the PRD says "No ACP". Phase 6 lists "re-check the Grok route before Phase 6" as a risk. No decision changes.

The red-team gate has not run on the Q17-Q24 changes. Recommended before Phase 3 starts: a focused pass on the Q18 cache, the Q22 Code-mode boundary and the Q23 Codex read isolation.

25. Q25, Grok dropped (user, 2026-11-14): the Grok Harness is out of scope. Stories 2.23 (connect Grok CLI) and 2.24 (ask and converse with Grok) are removed. The Integrations page shows three Harnesses: Claude Code, Codex and Omp. Grok is removed from the mention list, the Harness cards, the Worker drivers, Phase 6 and the Phase 7 Code mode. Where Q1, Q18, Q22 and Q23 name Grok, read them without Grok. The research note about the Grok ACP route no longer applies. Spec effect: epics.md stories 2.23 and 2.24 removed; design handoff rows and scenes that show `@Grok` are not built. Phase 6 effort drops by about 2d.

### Answers to the open questions (user, 2026-11-14)

26. Q26, Claude model fallback (was open question 6): accepted. When the single model-list request fails at Connect, the static list (`opus`, `sonnet`, `haiku`) is shown, marked by source and labelled "Not reported by Claude Code". The changes to 2.1 AC 5 and 2.6 AC 3 are accepted.
27. Q27, command network in Code jobs (was open question 7): the network is NOT blocked for commands the agent runs in a Code job (the proposal "deny all command network" is rejected). Package installs and tests that need the network work. Provider tokens still never reach the agent or its commands (Q22 keeps the Worker as the only party that pushes, and Plane opens the change request), so network access does not give the agent push rights. Accepted risk: an agent command can send repository content to any host; this is accepted because the instance and its users are trusted (Q17, Tailscale only). Q&A Runs are unchanged by this answer. Q2 (hostname grants) is superseded, because there are no per-host network grants any more. Details: [Phase 7](./phase-07-code-jobs-and-draft-pr.md).

## Red Team Review

### Session — 2026-11-12

**Findings:** 15 (13 accepted and applied, 2 surface-to-user; 0 rejected). Report: [reports/red-team-261112-local-cli-agents-rebuild.md](./reports/red-team-261112-local-cli-agents-rebuild.md)
**Severity breakdown:** 0 Critical, 4 High, 11 Medium
**Method note:** one reviewer applied all four lenses (no subagent tool in this run). The lead's brief authorised direct edits for findings that do not touch user decisions. No user decision Q1-Q8 was changed.

| #   | Finding                                                                                  | Severity | Disposition                      | Applied To                                                         |
| --- | ---------------------------------------------------------------------------------------- | -------- | -------------------------------- | ------------------------------------------------------------------ |
| F1  | Project create plus binding not atomic; bind race gives 500 and an orphan project        | High     | Accept                           | Phase 1 Refactor, 1.5                                              |
| F2  | Binding trusts client repository fields; `base_ref` reaches git unvalidated              | High     | Accept                           | Phase 1 Key decisions, 1.5                                         |
| F3  | Single-use GitHub refresh tokens; concurrent refresh breaks connection                   | High     | Accept                           | Phase 1 Key decisions, 1.1; Phase 7 Key decisions                  |
| F4  | Grant revoke disconnects other workspaces; expired token must not block revoke           | Medium   | Accept                           | Phase 1 Key decisions, 1.4                                         |
| F5  | `encrypt_data`/`decrypt_data` return `""` on error                                       | Medium   | Accept                           | Phase 1 Key decisions, 1.1                                         |
| F6  | Q3 env fallback differs from `get_configuration_value` semantics                         | Medium   | Accept (implements Q3)           | Phase 1 Key decisions, Files, 1.1                                  |
| F7  | Files list misses settings union, icon map, i18n namespace, constants export, admin form | Medium   | Accept                           | Phase 1 Files                                                      |
| F8  | Uninstall needs App JWT; detach must survive the next sync                               | Medium   | Accept                           | Phase 1 Key decisions, 1.3                                         |
| F9  | Device-flow poll has no concurrency guard                                                | Medium   | Accept                           | Phase 1 Key decisions, 1.1                                         |
| F10 | Phase 3 pytest command with two `-k` skips agent contract tests                          | Medium   | Accept                           | Phase 3 Verification                                               |
| F11 | 1.4 AC 2 and 1.8 AC 4 have no test in any phase                                          | Medium   | Accept                           | Phase 3 2.7, Phase 7 3.1, story-coverage, Phase 1 Success criteria |
| F12 | Local `makemigrations --check` needs CI env; run in test container                       | Medium   | Accept                           | Phases 1-5, 7 Verification; architecture-contracts §7              |
| F13 | Installation scoping: connecting admin's token decides what all members can bind         | High     | Decided by user 2026-11-12 (Q9)  | Phase 1 Key decisions, 1.2, G1                                     |
| F14 | Connection outlives the admin who connected it                                           | Medium   | Decided by user 2026-11-12 (Q10) | Phase 1 Key decisions, 1.1, 1.4                                    |
| F15 | Tests Before 3 is not a regression test; log assertion scope                             | Medium   | Accept                           | Phase 1 Tests Before, 1.1                                          |

### Whole-Plan Consistency Sweep

- Files reread: plan.md, phase-01 to phase-07, architecture-contracts.md, story-coverage.md
- Decision deltas checked: 11 (sync keeps detach, concurrency test DB mode, installation removal semantics, revoke endpoint, refresh locking, binding input source, `base_ref` rule, Q3 accessor, makemigrations command location, pytest `-k` split, deferred 1.4/1.8 ACs)
- Reconciled stale references: 8 (Phase 1 1.3 and 1.4 rows, Tests Before 1-3 reference, two `app/(all)` paths without the `apps/web/` prefix, makemigrations lines in Phases 2, 3, 4, 5, 7 and architecture-contracts §7, Phase 7 PR token source)
- Unresolved contradictions: 0. F13 and F14 were decided by the user on 2026-11-12 (Q9, Q10).
- GitLab scope (2026-11-12, after this review): Phase 1 now uses the provider-neutral model and ships GitHub and GitLab; Phases 3, 4, 5 and 7 use the provider boundary in [architecture-contracts.md §11](./architecture-contracts.md#11-git-provider-boundary-and-extension-trace). Every red-team fix F1-F12 and F15 is kept on the neutral model; F3, F4, F6 and F8 stay GitHub-only. The red-team gate ran on the GitLab additions on 2026-11-12 (session below).

### Session — 2026-11-12 (GitLab additions)

**Findings:** 12 (10 accepted and applied, 1 surface-to-user, 1 rejected). Report: [addendum in reports/red-team-261112-local-cli-agents-rebuild.md](./reports/red-team-261112-local-cli-agents-rebuild.md#addendum-gitlab-red-team-pass-2026-11-12). Edits carry the marker `<!-- red-team 2026-11-12 gitlab -->`.
**Severity breakdown:** 0 Critical, 4 High, 6 Medium, 2 Low
**Method note:** one reviewer, four lenses, scope = diff `acd8965582` vs `d6f6b43d25`. No user decision (Q1-Q10, GitLab scope items 1-6) was changed; open questions 1-4 were not decided (evidence added to 4).

| #    | Finding                                                                                                             | Severity | Disposition                    | Applied To                                                                    |
| ---- | ------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------ | ----------------------------------------------------------------------------- |
| GL1  | `/version` refuses `write_repository`-only tokens (403), so `gitlab_scope_missing` cannot occur; check `self` first | High     | Accept                         | Phase 1 Key decisions, Files (fixtures), G1 tests                             |
| GL2  | Worker token in `X-Api-Key` would store `git-credential` responses (GitLab token) through `APITokenLogMiddleware`   | High     | Accept                         | Phase 2 Key decisions, architecture-contracts §4                              |
| GL3  | Container rewrites the Worktree `.git` file; Worker git on the Host runs attacker config with the token in reach    | High     | Accept                         | Phase 7 Key decisions, G6 tests, architecture-contracts §11                   |
| GL4  | Worker git transport: system credential helper stores the token, redirects followed, no SSRF guard on the Mini      | High     | Accept                         | Phase 3 Key decisions, 2.7 tests, architecture-contracts §11                  |
| GL5  | GitLab reconnect with another group leaves the old group `attached`                                                 | Medium   | Accept                         | Phase 1 Key decisions, G1 tests                                               |
| GL6  | Hostile GitLab server: no body cap, timeout multiplied by resolved IPs, no request-host guard                       | Medium   | Accept                         | Phase 1 Key decisions, G1 tests                                               |
| GL7  | Phase 3 `-k` never selects `test_agent_git_credential_fetch.py`                                                     | Medium   | Accept                         | Phase 3 Verification                                                          |
| GL8  | Live GitLab smoke passes as a skip (exit 0); Phase 7 command runs outside the test container                        | Medium   | Accept                         | Phase 1 Files, Verification, Success criteria; Phase 7 Verification           |
| GL9  | `ps` capture of git argv is a racy phantom test                                                                     | Medium   | Accept                         | Phase 3 2.7 tests, Phase 7 G6 tests                                           |
| GL10 | `gitlab_dns_failed` vs `gitlab_url_blocked` is an internal-name oracle                                              | Medium   | Surface to user (scope item 4) | plan.md open question 5                                                       |
| GL11 | `get_repository` has no caller; 401/403 status rule inconsistent; `protected_branches` paginated                    | Low      | Accept                         | architecture-contracts §11, plan.md, Phase 1 Key decisions and Risks, Phase 7 |
| GL12 | Custom CA bundle widens trust for other hosts                                                                       | Low      | Reject (verified safe)         | none                                                                          |

### Whole-Plan Consistency Sweep (GitLab pass)

- Files reread: plan.md, phase-01, phase-02 (Worker token line), phase-03, phase-07, architecture-contracts.md, gitlab-scope-decisions.md
- Reconciled: "six methods" to five (plan.md, architecture-contracts §11 table and extension trace), Phase 7 "five Phase 7 methods" to four, Phase 1 G1 test order matches the new check order, 401/403 rule matches between Phase 1 Key decisions and Risks
- Unresolved contradictions: 0. Open: questions 1-5.
