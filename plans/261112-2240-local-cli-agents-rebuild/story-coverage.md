# Story coverage

Each story from [epics.md](../2026-09-28-plane-local-cli-agents-epics/epics.md) is in exactly one phase.
The acceptance criteria are the Given/When/Then blocks at the cited lines. Phase files cite them again per story.
Totals: Epic 1 = 8, Epic 2 = 26, Epic 3 = 9, all = 43. Plus 7 plan-level GitLab stories G1-G7 (table below), so the plan delivers 50 stories. <!-- 2026-11-14 --> After Q25 (2.23, 2.24) and Q36 (3.1-3.9, G6, G7) the plan delivers 32 epics.md stories and G1-G5 = 37 stories.

| Story | Title                                          | epics.md lines | Phase                                                                                         | Mockup rows                                      |
| ----- | ---------------------------------------------- | -------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| 1.1   | Connect a GitHub account with device flow      | 370-406        | 1                                                                                             | I046, I054, I055, I056, I057, I077               |
| 1.2   | Connect a GitHub organization                  | 408-432        | 1                                                                                             | I047, I050                                       |
| 1.3   | Remove one GitHub installation                 | 434-454        | 1                                                                                             | I049                                             |
| 1.4   | Disconnect the workspace GitHub account        | 456-476        | 1                                                                                             | I048                                             |
| 1.5   | Bind one repository while creating a project   | 478-518        | 1                                                                                             | I068, I069, I070, I071, I076                     |
| 1.6   | Set the draft pull-request default             | 520-540        | 1                                                                                             | I051                                             |
| 1.7   | Set conclusion mirroring to pull requests      | 542-562        | 1                                                                                             | I052                                             |
| 1.8   | Choose the Agent branch format                 | 564-588        | 1                                                                                             | I053                                             |
| 2.1   | Connect Claude Code as a local Harness         | 595-627        | 2 (Q18: quick check plus per-version suite; Q21: AC 5 changed, pending confirmation) <!-- 2026-11-14 --> (Q31, from Phase 3: suite runs in the probe sandbox; AD-4 permission check reads as bypass mode) | I046, I058, I063, I064, I065, I066, I078         |
| 2.2   | Rename a workspace Agent                       | 629-649        | 2                                                                                             | I060                                             |
| 2.3   | Set a unique Agent mention handle              | 651-671        | 2                                                                                             | I060 (handle row)                                |
| 2.4   | Set an Agent's workspace instructions          | 673-693        | 2                                                                                             | I061                                             |
| 2.5   | Toggle whether an Agent is mentionable         | 695-715        | 2                                                                                             | I059                                             |
| 2.6   | Select a model reported by a connected Harness | 717-741        | 2 (Q21: AC 3 changed, pending confirmation)                                                   | I062                                             |
| 2.7   | Ask Claude Code about a work item              | 743-795        | 3 <!-- 2026-11-14 --> (Q31-Q35: runs in the Q&A sandbox; clone is a read-only mount (AC wording "OS boundary" reads "read-only mount of the microVM")) | I010, I011, I013, I014, I035, I043, I074         |
| 2.8   | Inspect a durable Run timeline                 | 797-841        | 3                                                                                             | I015, I016, I017, I019, I020, I021, I022, I036   |
| 2.9   | Resize the Run panel                           | 843-859        | 4                                                                                             | I018                                             |
| 2.10  | Follow an Agent's plan                         | 861-881        | 4                                                                                             | I023, I024                                       |
| 2.11  | Choose a repository for an unbound Run         | 883-907        | 4                                                                                             | I032, I033                                       |
| 2.12  | Retrieve older authorized issue comments       | 909-929        | 4                                                                                             | none (context only)                              |
| 2.13  | Send a follow-up in the same Run               | 931-955        | 4 <!-- 2026-11-14 --> (Q35: rebuild when the sandbox was recreated) | I034                                             |
| 2.14  | Queue a message during active work             | 957-989        | 5                                                                                             | I025, I026, I029                                 |
| 2.15  | Send a queued message now                      | 991-1015       | 5 (Q19: Claude uses AC 2 only)                                                                | I027                                             |
| 2.16  | Remove an undelivered queued message           | 1017-1037      | 5                                                                                             | I028                                             |
| 2.17  | Stop an active Run                             | 1039-1063      | 5 <!-- 2026-11-14 --> (Q31: Stop kills the process inside the sandbox) | I030                                             |
| 2.18  | Resume a stopped Run                           | 1065-1085      | 5 <!-- 2026-11-14 --> (Q31: sandbox health check before resume) | I031                                             |
| 2.19  | Retry a stale Run safely                       | 1087-1111      | 5 <!-- 2026-11-14 --> (Q31: reconcile by in-sandbox pidfile) | I044                                             |
| 2.20  | Mark a stale Run failed                        | 1113-1133      | 5                                                                                             | I044                                             |
| 2.21  | Connect Codex CLI as a local Harness           | 1135-1155      | 6 (Q18, Q20, Q21, Q23) <!-- 2026-11-14 --> (Q20, Q23 superseded by Q31; Codex sandbox; login path open) | I063, I064 (Codex states)                        |
| 2.22  | Ask and converse with Codex on a work item     | 1157-1177      | 6 (Q20, Q23) <!-- 2026-11-14 --> (Q31: Codex sandbox) | I075                                             |
| 2.23  | Connect Grok CLI as a local Harness            | 1179-1203      | Removed by Q25 (was 6) | Grok idle detail state                           |
| 2.24  | Ask and converse with Grok on a work item      | 1205-1229      | Removed by Q25 (was 6) | none new                                         |
| 2.25  | Connect Omp as a local Harness                 | 1231-1251      | 6 (Q18) <!-- 2026-11-14 --> (Q31: Omp sandbox kit) | none new                                         |
| 2.26  | Ask and converse with Omp on a work item       | 1253-1273      | 6 <!-- 2026-11-14 --> (Q31: Omp sandbox kit) | none new                                         |
| 3.1   | Deliver a code change after one-time approval  | 1280-1349      | Removed by Q36 (no Code jobs; was 7) | I037, I038, I039 (Code-job card), I041 ("Allow") |
| 3.2   | Grant a matching effect for the rest of a Run  | 1351-1371      | Removed by Q36 (no Code jobs; was 7) | I040 removed by Q22                              |
| 3.3   | Deny a proposed Agent effect                   | 1373-1393      | Removed by Q36 (no Code jobs; was 7) | I042                                             |
| 3.4   | Decide a Code job's network escalation         | 1395-1415      | Removed by Q36 (no Code jobs; was 7) | none (network variant of I039 removed)           |
| 3.5   | Decide a Code job's path escalation            | 1417-1437      | Removed by Q36 (no Code jobs; was 7) | none (path variant of I039 removed)              |
| 3.6   | Wait for a Code-job capacity slot              | 1439-1463      | Removed by Q36 (no Code jobs; was 7) | I045 (waiting state, no Docker wording)          |
| 3.7   | Stop a Code job and retain its Worktree        | 1465-1485      | Removed by Q36 (no Code jobs; was 7) | I030 (Code variant)                              |
| 3.8   | Resume a stopped Code job in its Worktree      | 1487-1507      | Removed by Q36 (no Code jobs; was 7) | I031 (Code variant)                              |
| 3.9   | Mirror a Run conclusion to its pull request    | 1509-1529      | Removed by Q36 (no Code jobs; was 7) | I052 (consumer)                                  |

Phase totals (epics.md): 1 = 8, 2 = 6, 3 = 2, 4 = 5, 5 = 7, 6 = 4, removed = 11 (2.23, 2.24 by Q25; 3.1-3.9 by Q36) (sum 43).

## GitLab stories (plan-level)

epics.md has no GitLab story. These stories come from [gitlab-scope-decisions.md](./gitlab-scope-decisions.md) (user-accepted 2026-11-12). Their acceptance criteria are in the owning phase file. Mockup rows are the GitHub rows, reused with the GitLab name, icon and terms only.

| Story | Title                                                  | Acceptance criteria                                                                                                                | Phase                                   | Mockup rows (reused)  |
| ----- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | --------------------- |
| G1    | Connect a self-hosted GitLab with a Group Access Token | [phase-01 G1](./phase-01-github-connection-and-repository.md#g1-connect-a-self-hosted-gitlab-with-a-group-access-token) (AC1-AC10) | 1                                       | I046, I054-I057, I077 |
| G2    | List the group's projects as repositories              | [phase-01 G2](./phase-01-github-connection-and-repository.md#g2-list-the-groups-projects-as-repositories)                          | 1                                       | I047, I050            |
| G3    | Bind a GitLab repository while creating a project      | [phase-01 G3](./phase-01-github-connection-and-repository.md#g3-bind-a-gitlab-repository-while-creating-a-project)                 | 1                                       | I068-I071, I076       |
| G4    | Disconnect GitLab (revoke-free)                        | [phase-01 G4](./phase-01-github-connection-and-repository.md#g4-disconnect-gitlab-revoke-free)                                     | 1 (AC2 change-request path closes in 7) | I048                  |
| G5    | Set GitLab merge-request policy                        | [phase-01 G5](./phase-01-github-connection-and-repository.md#g5-set-gitlab-merge-request-policy)                                   | 1 (AC4 closes in 3 and 7)               | I051, I052, I053      |
| G6    | Deliver a draft merge request from a Code job          | [phase-07 G6](./phase-07-code-jobs-and-draft-pr.md#g6-deliver-a-draft-merge-request-from-a-code-job) (Q22: AC1, AC6 changed) <!-- 2026-11-14 --> (Q31: AC6 "a command in the Harness sandbox" reads "a command in the Code sandbox") | Removed by Q36 (was 7) | I037-I039, I041       |
| G7    | Mirror a Run conclusion to its merge request           | [phase-07 G7](./phase-07-code-jobs-and-draft-pr.md#g7-mirror-a-run-conclusion-to-its-merge-request)                                | Removed by Q36 (was 7) | I052 (consumer)       |

Phase totals with GitLab: 1 = 13, 2 = 6, 3 = 2, 4 = 5, 5 = 7, 6 = 4 (sum 37); removed: 2.23, 2.24, 3.1-3.9, G6, G7.

Provider-neutral consumers of Epic 1 behavior (no new story): Phase 3 (Run snapshot with provider, Worker clone through `git_transport.py`), Phase 4 (2.11 options from both providers), Phase 5 (resume remote check, `git-credential` fencing, purpose `fetch`). <!-- 2026-11-14 --> The Phase 7 consumer and the policy snapshot are removed by Q36.

## Mockup scenes to phases

| Scene | Name             | Phases                                      |
| ----- | ---------------- | ------------------------------------------- |
| 1     | Mention          | 2 (picker reasons), 3                       |
| 2     | In progress      | 3, 4 (plan), 5 (queue, Stop)                |
| 3     | Elicit           | 4                                           |
| 4     | Completed        | 3                                           |
| 5     | Code job + PR    | Not built (Q36)                             |
| 6     | Permission       | Not built (Q36)                             |
| 7     | Failed           | 3                                           |
| 8     | Stale            | 5                                           |
| 9     | Capacity         | Not built (Q36; the banner is the Code-job limit, I045) |
| 10    | Stopped to steer | 5                                           |
| 11    | Integrations     | 1 (GitHub and GitLab), 2 (Harnesses)        |
| 12    | New project      | 1                                           |

Row I070 shows clone progress at project creation. UX-DR16 (epics.md:309) forbids a shared Mirror clone state, so Phase 1 implements the selection part of I070 and omits clone progress.

<!-- red-team 2026-11-12 --> Two Epic 1 criteria need a Run and close in later phases: 1.4 AC 2 (epics.md:472) in Phase 3 (new launches) and Phase 7 (pending change-request delivery); 1.8 AC 4 (epics.md:588) in Phase 7 (3.1). Stories 1.4 and 1.8 are "done" only after those tests pass. <!-- 2026-11-14 --> Q36: the Phase 7 parts are removed; 1.4 AC 2 and G4 AC2 close in Phase 3; 1.8 AC 4 and G5 AC4 are removed. The same applies to G4 AC2 (Phase 3 launch, Phase 7 delivery) and G5 AC4 (Phase 3 snapshot, Phase 7 G6). The missing-connection code is `provider_disconnected` with a `provider` field for both providers.

## Q22 effect on Epic 3 and mockup rows (2026-11-14)

<!-- 2026-11-14 --> Superseded by Q36 (section below). Kept for history.

Decision Q22 ([plan.md](./plan.md#multica-comparison-decisions-2026-11-14)) keeps every Epic 3 story in Phase 7, so the totals above do not change. Some criteria change or are removed; the full per-criterion table is [Phase 7 spec deviations](./phase-07-code-jobs-and-draft-pr.md#spec-deviations-q22-2026-11-14).

- 3.4 and 3.5 keep their rows, but their decision cards are gone. <!-- 2026-11-14 --> 3.4 closes with the command network open in the Code sandbox only (Q27, Q31). 3.5 closes on its AC 3 (epics.md:1435-1437) through the Code sandbox mounts.
- 3.2 closes on the Code-job approval as the Run grant.
- Mockup rows: I039 ("Write approval state") becomes the Code-job card; I041 ("Allow once") becomes "Allow"; I040 ("Allow for this run") is removed; I042 (Deny) is kept; I045 ("Docker capacity refusal state") becomes the Code waiting state with no Docker wording. <!-- 2026-11-14 --> Q31 brings back a Docker Sandbox per Code job, but the slot pool stays dropped; I045 keeps the neutral wording "Waiting for a Code slot". The browser review counts 64 rows (65 minus I040).
- Decisions Q18-Q21, Q23 and Q24 change no story assignment. Their criterion changes are marked in the rows above and in the owning phase files.

## Q31-Q35 effect (Docker Sandboxes, 2026-11-14)

Decisions Q31-Q35 ([plan.md](./plan.md#docker-sandboxes-decisions-2026-11-14)) move every Run into a Docker Sandbox. No story changes phase, and the totals above do not change. Criterion effects:

- AD-4 permission check (2.1, 2.21, 2.25): under full permissions there is no deny to prove; the check proves bypass mode and no permission request. The read-only mount is proven by the Phase 3 `sbx` verification and by native tests. Spec deviation.
- 2.7 (epics.md:763) "under an OS boundary that denies writes": met by the read-only clone mount inside the microVM. The agent can write inside the VM and its scratch folder, never to the clone or the host.
- 3.1 AC 7 (epics.md:1315): memory limit returns through the sandbox memory setting; no process-count limit; network open (Q27). 3.5 AC 3: kept through the mounts. 3.6 and 3.7: Code sandbox wording (Phase 7 spec deviations).
- Stories 2.17-2.19 and 3.7: no criterion change; the Stop and reconcile mechanism is the in-sandbox pidfile kill.
- No mockup row changes. Connect error text for a missing Docker sign-in reuses the existing "missing action" row of the Harness detail (I063, I064).

## Q36 effect: no Code jobs (2026-11-14)

Decision Q36 ([plan.md](./plan.md#docker-sandboxes-decisions-2026-11-14)) removes Code jobs. Code work goes to Archon through the Archon MCP server; Plane builds no UI for it.

- Removed stories: 3.1-3.9, G6, G7. The Q31-Q35 criterion notes on 3.1, 3.5-3.7 above have no consumer.
- Mockup rows not built: I037 (Code job completed), I038 (draft pull request card), I039 (write approval), I041 (Allow once), I042 (Deny), I045 (Code-job capacity). I040 was already removed by Q22. The browser review counts 58 rows (65 minus 7).
- Rows kept in their Q&A form only: I030 (Stop) and I031 (Stopped); their Code variants are not built. The run kind pill "Code job · worktree" and the PR line of the Run card (design README Screen 1) are not built.
- Scenes not built: 5 (Code job + PR), 6 (Permission), 9 (Capacity; the banner shows the Code-job limit).
- Phase 1 rows I051, I052, I053 (policy rows, merged) stay as built; they have no consumer now (plan.md Q36 follow-up).
