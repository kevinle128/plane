# Story coverage

Each story from [epics.md](../2026-09-28-plane-local-cli-agents-epics/epics.md) is in exactly one phase.
The acceptance criteria are the Given/When/Then blocks at the cited lines. Phase files cite them again per story.
Totals: Epic 1 = 8, Epic 2 = 26, Epic 3 = 9, all = 43.

| Story | Title | epics.md lines | Phase | Mockup rows |
| --- | --- | --- | --- | --- |
| 1.1 | Connect a GitHub account with device flow | 370-406 | 1 | I046, I054, I055, I056, I057, I077 |
| 1.2 | Connect a GitHub organization | 408-432 | 1 | I047, I050 |
| 1.3 | Remove one GitHub installation | 434-454 | 1 | I049 |
| 1.4 | Disconnect the workspace GitHub account | 456-476 | 1 | I048 |
| 1.5 | Bind one repository while creating a project | 478-518 | 1 | I068, I069, I070, I071, I076 |
| 1.6 | Set the draft pull-request default | 520-540 | 1 | I051 |
| 1.7 | Set conclusion mirroring to pull requests | 542-562 | 1 | I052 |
| 1.8 | Choose the Agent branch format | 564-588 | 1 | I053 |
| 2.1 | Connect Claude Code as a local Harness | 595-627 | 2 | I046, I058, I063, I064, I065, I066, I078 |
| 2.2 | Rename a workspace Agent | 629-649 | 2 | I060 |
| 2.3 | Set a unique Agent mention handle | 651-671 | 2 | I060 (handle row) |
| 2.4 | Set an Agent's workspace instructions | 673-693 | 2 | I061 |
| 2.5 | Toggle whether an Agent is mentionable | 695-715 | 2 | I059 |
| 2.6 | Select a model reported by a connected Harness | 717-741 | 2 | I062 |
| 2.7 | Ask Claude Code about a work item | 743-795 | 3 | I010, I011, I013, I014, I035, I043, I074 |
| 2.8 | Inspect a durable Run timeline | 797-841 | 3 | I015, I016, I017, I019, I020, I021, I022, I036 |
| 2.9 | Resize the Run panel | 843-859 | 4 | I018 |
| 2.10 | Follow an Agent's plan | 861-881 | 4 | I023, I024 |
| 2.11 | Choose a repository for an unbound Run | 883-907 | 4 | I032, I033 |
| 2.12 | Retrieve older authorized issue comments | 909-929 | 4 | none (context only) |
| 2.13 | Send a follow-up in the same Run | 931-955 | 4 | I034 |
| 2.14 | Queue a message during active work | 957-989 | 5 | I025, I026, I029 |
| 2.15 | Send a queued message now | 991-1015 | 5 | I027 |
| 2.16 | Remove an undelivered queued message | 1017-1037 | 5 | I028 |
| 2.17 | Stop an active Run | 1039-1063 | 5 | I030 |
| 2.18 | Resume a stopped Run | 1065-1085 | 5 | I031 |
| 2.19 | Retry a stale Run safely | 1087-1111 | 5 | I044 |
| 2.20 | Mark a stale Run failed | 1113-1133 | 5 | I044 |
| 2.21 | Connect Codex CLI as a local Harness | 1135-1155 | 6 | I063, I064 (Codex states) |
| 2.22 | Ask and converse with Codex on a work item | 1157-1177 | 6 | I075 |
| 2.23 | Connect Grok CLI as a local Harness | 1179-1203 | 6 | Grok idle detail state |
| 2.24 | Ask and converse with Grok on a work item | 1205-1229 | 6 | none new |
| 2.25 | Connect Omp as a local Harness | 1231-1251 | 6 | none new |
| 2.26 | Ask and converse with Omp on a work item | 1253-1273 | 6 | none new |
| 3.1 | Deliver a code change after one-time approval | 1280-1349 | 7 | I037, I038, I039, I041 |
| 3.2 | Grant a matching effect for the rest of a Run | 1351-1371 | 7 | I040 |
| 3.3 | Deny a proposed Agent effect | 1373-1393 | 7 | I042 |
| 3.4 | Decide a Code job's network escalation | 1395-1415 | 7 | I039 (network variant) |
| 3.5 | Decide a Code job's path escalation | 1417-1437 | 7 | I039 (path variant) |
| 3.6 | Wait for a Code-job capacity slot | 1439-1463 | 7 | I045 |
| 3.7 | Stop a Code job and retain its Worktree | 1465-1485 | 7 | I030 (Code variant) |
| 3.8 | Resume a stopped Code job in its Worktree | 1487-1507 | 7 | I031 (Code variant) |
| 3.9 | Mirror a Run conclusion to its pull request | 1509-1529 | 7 | I052 (consumer) |

Phase totals: 1 = 8, 2 = 6, 3 = 2, 4 = 5, 5 = 7, 6 = 6, 7 = 9 (sum 43).

## Mockup scenes to phases

| Scene | Name | Phases |
| --- | --- | --- |
| 1 | Mention | 2 (picker reasons), 3 |
| 2 | In progress | 3, 4 (plan), 5 (queue, Stop) |
| 3 | Elicit | 4 |
| 4 | Completed | 3 |
| 5 | Code job + PR | 7 |
| 6 | Permission | 7 |
| 7 | Failed | 3 |
| 8 | Stale | 5 |
| 9 | Capacity | 7 |
| 10 | Stopped to steer | 5 |
| 11 | Integrations | 1 (GitHub), 2 (Harnesses) |
| 12 | New project | 1 |

Row I070 shows clone progress at project creation. UX-DR16 (epics.md:309) forbids a shared Mirror clone state, so Phase 1 implements the selection part of I070 and omits clone progress.

<!-- red-team 2026-11-12 --> Two Epic 1 criteria need a Run and close in later phases: 1.4 AC 2 (epics.md:472) in Phase 3 (new launches) and Phase 7 (pending PR delivery); 1.8 AC 4 (epics.md:588) in Phase 7 (3.1). Stories 1.4 and 1.8 are "done" only after those tests pass.
