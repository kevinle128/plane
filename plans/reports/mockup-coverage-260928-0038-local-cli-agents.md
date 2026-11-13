# Local CLI Agent mockup coverage check

The frozen inventory contains 78 visible controls or states: 13 unchanged Plane context items and 65 change items.
The prototype, support script, and Propel bundle still match the SHA-256 values in the inventory.
The inventory is provisional because no completed epic exists; this check establishes planning coverage, not implementation completion.

| Inventory IDs | Count | Epic and requirement coverage |
| --- | ---: | --- |
| I010–I011 | 2 | Epic 2: FR7–FR10; UX-DR1–UX-DR2 |
| I013–I018 | 6 | Epic 2: FR7–FR9; UX-DR1–UX-DR4 |
| I019–I024 | 6 | Epic 2: FR9, FR11; UX-DR5–UX-DR6 |
| I025–I030 | 6 | Epic 2: FR12, FR15; UX-DR7–UX-DR9 |
| I031–I036 | 6 | Epic 2: FR4, FR11, FR15; UX-DR5, UX-DR9, UX-DR11 |
| I037–I042 | 6 | Epic 3: FR13–FR14, FR18; UX-DR1, UX-DR10 |
| I043–I044 | 2 | Epic 2: FR11, FR19; UX-DR11 |
| I045 | 1 | Epic 3: FR19; UX-DR11; changed by the later capacity decision |
| I046 | 1 | Epics 1–2: FR1, FR5; UX-DR12 |
| I047–I057 | 11 | Epic 1: FR1–FR2; UX-DR13–UX-DR14 |
| I058–I066 | 9 | Epic 2: FR5–FR6; UX-DR15 |
| I068–I071 | 4 | Epic 1: FR3; UX-DR16; I070 is partly changed by the fresh-clone decision |
| I074–I075 | 2 | Epic 2: FR7–FR8; UX-DR2 |
| I076–I078 | 3 | Epics 1–2: FR3, FR5; UX-DR13, UX-DR15–UX-DR16 |

I001–I009, I012, I067, and I072–I073 are existing Plane context and need no Agent-specific story.
Every one of the 65 change items has a requirement and proposed epic owner.

## Details added to the requirements inventory

- The Run card and panel identify the current action, work item, active CWD, sandbox mode, timing, and reopen path.
- The timeline groups active work with step count, supports disclosure, and keeps completed work available after collapse.
- The plan can show a reported estimate; the queue supports removal and uses a queue-specific send label.
- Stop reports discarded queued-message count, and the permission card identifies affected files and the active Worktree.
- The GitHub device flow includes the explicit completion action, and the detail view includes organization, installation, disconnect, and back actions.
- Harness details include the four-Harness selector, Mentionable switch, and back action.
- The project repository picker includes owner filters, selected state, and a missing-repository warning.

## Later decisions that replace prototype details

- I045 shows capacity refusal with no queue.
  The approved PRD and architecture require a durable waiting state and no extra container.
- I032–I033 show candidate local clone paths.
  The member selects an authorized remote; the Worker then creates a fresh CWD for that Run.
- I053 shows `agent/identifier` as a mock label.
  The architecture specifies two Run-unique branch formats and a default.
- I070 shows a shared Mirror clone during project creation.
  The new repository binding stores the remote; cloning starts separately for each mention.
- I071 says Agents cannot be mentioned without a repository CWD.
  The accepted PRD allows a mention to create an awaiting Run that asks for a repository before Harness launch.
- I074–I075 jump to a running scene when an Agent is selected in the prototype.
  In production, selection inserts a mention and saving the comment creates the Run.

## Delivery evidence still required

The inventory proves visible mockup states, not that all four CLI drivers can satisfy them.
The owning stories must verify Claude model reporting, Grok permission pause and resume, per-Harness interaction, and OS and Docker isolation before v1 release.
