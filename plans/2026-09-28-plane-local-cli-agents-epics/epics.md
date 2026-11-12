---
status: final
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
targetSpec: spec-plane-local-cli-agents
inputDocuments:
  - _bmad-output/specs/spec-plane-local-cli-agents/SPEC.md
  - _bmad-output/specs/spec-plane-local-cli-agents/job-kinds.md
  - _bmad-output/specs/spec-plane-local-cli-agents/agent-run-ui.md
  - _bmad-output/specs/spec-plane-local-cli-agents/runner.md
  - _bmad-output/specs/spec-plane-local-cli-agents/diagrams.md
  - _bmad-output/specs/spec-plane-local-cli-agents/brownfield.md
  - _bmad-output/specs/spec-plane-local-cli-agents/failure-modes.md
  - plans/2026-09-27-local-cli-agents-prd/prd.md
  - plans/2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md
  - claude-design/design_handoff_local_cli_agents/README.md
  - plans/reports/mockup-inventory-260928-0020-local-cli-agents.json
---

# Plane Local CLI Agents - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Plane Local CLI Agents, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.
Where the older SPEC or prototype differs, the approved PRD and final Architecture Spine govern v1: four Harnesses, a fresh clone per mention, Code-capacity waiting, permission before writes, and no ACP.

## Requirements Inventory

### Functional Requirements

**FR1: Connect GitHub.**
A workspace administrator can start, complete, cancel, and disconnect GitHub authentication from Workspace settings → Integrations.
The UI shows pending, connected, and failure states.
After connection, the administrator can see and manage granted personal and organization installations.

**FR2: Configure pull request behavior.**
The GitHub integration shows controls for draft pull requests, conclusion mirroring to pull request comments, and branch format.
Agent pull requests open as drafts by default.

**FR3: Bind a project repository.**
During project creation, a member can search repositories available through the GitHub integration and select one.
The picker groups repositories by installation and shows repositories already bound to another project as unavailable.
When GitHub is disconnected, the create-project flow explains the missing connection and links to Integrations.
The binding supplies the remote repository that the Worker clones separately for each Agent Run.

**FR4: Resolve a missing or ambiguous repository.**
A Run without one usable repository binding asks for a choice in its panel.
The Worker cannot start a Harness or permit a Code job write until the Run has one repository and its own safe CWD.
The Run never uses the Plane deployment checkout or the Worker's incidental current directory.

**FR5: Configure four Harnesses.**
Integrations shows Claude Code, Codex CLI, Grok CLI, and Omp.
Each Harness has a detail page with an enable switch, connection control, name, unique workspace handle, instructions, and model selection.
The page distinguishes not connected, connecting, connected, and connection failed states and gives an actionable error.

**FR6: Verify a Harness and choose a model.**
Connecting a Harness verifies that the Worker can use it and obtains the models it reports.
The connection check records which interaction actions that Harness can perform, including continued conversation, progress reporting, cancellation, permission requests, and delivery during an active turn.
Model selection is available only after a successful connection.
The selected model persists for that workspace Agent.
A failed authentication attempt produces a visible error and can be retried.

**FR7: Mention an Agent.**
The existing work-item comment editor lists people and Agents when a member types @.
An Agent row shows its connection state.
An Agent that is not connected remains visible but cannot be selected for a new Run.
Any member who can comment on the work item can mention a connected Agent.

**FR8: Create a Run from a mention.**
Each new comment that mentions a connected Agent creates a separate Agent Run and card.
The card shows the requester, original request, Agent, Run kind, state, elapsed time, and Open run action.
A later mention in another comment creates another Run, even on the same work item.

**FR9: Show a durable timeline.**
The Run panel shows the full ordered history of prompts, thoughts, actions, results, elicitation, permission decisions, errors, and pull request details.
Thoughts and tool actions may start collapsed but remain available after the Run concludes.
The panel shows the Run's plan and message queue when they exist.
Members can resize the panel; width and collapse choices persist per member.

**FR10: Keep work-item Activity concise.**
The work-item Activity feed shows the Run card and conclusion.
Intermediate thoughts, tool calls, and tool results stay in the Run panel.
The Run card links to a draft pull request when the Code job produces one.

**FR11: Show state and progress.**
The card and panel distinguish waiting for pickup, in progress, awaiting a person, permission needed, completed, failed, stale, and stopped.
The panel shows current live state and elapsed time during work.
An authentication failure creates an error in the panel and a concise failure conclusion on the work item.

**FR12: Continue a Run in its panel.**
The Run panel accepts follow-up messages in the same session.
While the Agent is working, new messages enter a visible queue and are delivered between steps.
Send now uses that Harness's supported control path.
If the Harness accepts input during an active turn, the Worker sends the selected message into that turn.
Otherwise, the Worker cancels the active turn, waits for cancellation to settle, and sends the selected message as the next turn in the same Run.
The panel shows when cancellation or delivery is pending and never marks a message delivered before the Harness accepts it.

**FR13: Escalate to a Code job.**
A request to implement or fix in the Run panel changes that Run from Q&A to a Code job.
The Run keeps its existing card, timeline, and conversation.
A new Agent mention in a work-item comment never appends to that Run.

**FR14: Request and record permission.**
Before the first Code job write, and again for a network or path escalation, the Run presents the proposed command, scope, and risk.
The member can allow once, allow for this Run, or deny.
The decision, person, and time remain visible in the durable timeline.
The Worker cannot perform the proposed write or escalation before a sufficient grant.

**FR15: Stop and resume.**
Any member who can comment on the work item can stop an active Run after confirmation.
Stopping interrupts the current action, clears queued messages, and retains the Run clone, sandbox, and Worktree.
The panel records who stopped the Run and accepts a reply to continue the same session.
The Worker must preserve the Run's conversation when a Harness needs a new process to continue it.

**FR16: Execute read-only Q&A.**
At pickup, the Worker clones the bound repository into a new CWD used only by this Run.
Q&A uses that Run clone as the Harness working directory and cannot write to it.
Two mentions on the same work item produce separate Run clones and separate CWDs.
Q&A does not create a Worktree, branch, or pull request.

**FR17: Execute an isolated Code job.**
A Code job uses an isolated Worktree and named Agent branch inside its own Run clone.
Later messages in that Run read the Worktree state.
The Agent cannot merge to the default branch.
The Worker retains the Run clone and Worktree when the Run stops.

**FR18: Deliver a draft pull request.**
When a Code job completes, the Run links to a draft GitHub pull request with branch and change summary.
A human reviews and merges the pull request.
The Run shows a clear failure if pull request creation fails.

**FR19: Handle capacity and stale work.**
The Worker supports concurrent Agent Runs.
When Code job capacity is full, the new Code job remains visible in a waiting state until a slot is available and does not start another container.
If the Worker stops updating a Run while Plane remains available, the Run becomes stale.
The panel offers Retry pickup and Mark failed for a stale Run.

**FR20: Anchor context to the Trigger comment.**
When an Agent mention creates a Run, Plane records the workspace ID, project ID, work-item ID, Agent ID, Trigger comment ID, and requester.
The Worker resolves those IDs through Plane before invoking the Harness; it does not infer context from the browser's current page, a last-used project, or its own CWD.
The Context snapshot and Run clone must refer to the same bound project repository.

**FR21: Include work-item and conversation content.**
The first prompt identifies the workspace, project, repository, work item identifier and link, current title, description, status, and other visible work-item fields relevant to the request.
It includes the Trigger comment as the current request, with its author and time.
It includes earlier comments on that work item in chronological order, with author, time, and stable comment ID.
Earlier Agent conclusion comments can appear as work-item comments; tool traces and private panel messages from other Runs do not become this Run's conversation.
For example, a mention on PLAN-214 must identify PLAN-214 and its project and must not import comments from another work item.

**FR22: Keep same-Run context current.**
Panel follow-ups keep the same Agent Run, Run clone, and conversation.
The Agent receives each new panel message with the prior messages and decisions from that Run.
When work-item content or comments changed since the previous turn, the Worker supplies the relevant update without silently switching the Run to another work item.
After a Worker or Harness restart, the Run can reconstruct its context from durable Plane records and continue in the same Run clone.
The user-facing Run identity does not depend on one Harness process or one vendor session ID.

**FR23: Make context limits and trust explicit.**
The work-item identity, current request, and enough issue content to understand the task remain available even when conversation history exceeds the Harness context budget.
If earlier comments are omitted, the Agent receives an omission count and a way to retrieve the full authorized work-item history.
Work-item descriptions, comments, titles, and other member-authored fields are treated as task data, not higher-priority instructions.
The Worker cannot include comments from a different work item or a workspace the requester cannot access.

### NonFunctional Requirements

**NFR1: Authorization and data isolation.**
Only members with work-item comment permission can mention or stop an Agent.
A context snapshot includes only records the requester can access and never includes another Run's private panel transcript.

**NFR2: Execution safety.**
A Run never executes in the Plane deployment checkout, a shared Mirror, an unbound repository, or the Worker's incidental CWD.
Q&A cannot write to its Run clone, and Code work cannot write or escalate access before a matching Plane grant.

**NFR3: Durable audit.**
Run prompts, thoughts, actions, results, errors, permission requests and decisions remain available after completion, refresh, or Worker restart.

**NFR4: Honest interaction and failure states.**
The UI never claims a message was delivered before Harness acceptance and never exposes a control that the connected Harness and Run control plane cannot honor.
CLI authentication, GitHub, repository, permission, cancellation, and PR failures produce visible actionable states.

**NFR5: Local availability and recovery.**
The Worker uses Plane API on localhost and requires no public callback.
Plane detects stale Runs when the Worker stops updating them and lets a member recover or fail them without losing the record.

**NFR6: Bounded resource use.**
Code jobs use a configured concurrent Docker limit and remain durably waiting when capacity is full.
A full pool does not start another container.

**NFR7: Accessibility.**
New controls, dialogs, status labels, queue actions, and panel interactions work with a keyboard and expose readable status text.

**NFR8: UI fidelity.**
Production UI follows the approved handoff's semantic tokens, components, layout, and interaction states in the work-item and settings surfaces.

**NFR9: Human delivery control.**
Agent pull requests are drafts by default, and an Agent never merges or pushes to the default branch.

### Additional Requirements

- **AR1 — Plane authority:** Plane API and PostgreSQL are the only writers of Run state, ordered events, queued commands, and permission decisions.
  Worker observations use authenticated API commands, idempotency keys, and Run-local event sequence numbers.
- **AR2 — Context envelope:** Plane creates a versioned snapshot with workspace, project, issue, requester, trigger comment, authorized earlier comments, bound repository, and base ref.
  The Worker formats the prompt with record IDs, authors, timestamps, source boundaries, omission count, and an authorized history retrieval path.
- **AR3 — Worker lease:** Claims carry a generation and expiry; stale generations cannot mutate the Run.
  Retry reconciles or stops the old process and must not replay an effect with possible side effects without a new user command.
- **AR4 — Driver contract:** One local Worker has Claude Code, Codex CLI, Grok CLI, and Omp adapters.
  Each adapter reports verified capabilities and must pass connection, model, follow-up, progress, interruption, permission, and recovery probes before it appears Connected.
  ACP is outside this architecture.
- **AR5 — Ordered interaction:** Plane stores queued, dispatching, accepted, and cancelled message states.
  Send now uses verified native midturn delivery or cancels the current turn and delivers the selected message in the next turn on the same Run.
- **AR6 — Stable Run identity:** The Plane Run ID survives Harness process or vendor session changes.
  The Run stores clone path, optional Worktree path, and active workspace kind; Code escalation changes the active CWD to the Worktree for every later turn.
- **AR7 — Fresh clone:** Every new mention receives its own clone path derived from the Run ID outside the Plane checkout.
  Q&A runs read that clone under an OS write boundary; Code jobs use a Worktree in a bounded Docker sandbox.
- **AR8 — Request-bound grants:** Every proposed effect creates a durable permission request linked to Run, turn, lease generation, action, normalized scope, and effect hash.
  Allow once applies only to that request; allow for Run applies only to later matching requests.
  OS and Docker boundaries enforce the grant even when a CLI has an approval mode.
- **AR9 — GitHub integration:** Plane API must own the Agent GitHub connection and project repository binding; the new Agent integration must create and record draft PRs.
  The branch-format choices are `agent/<issue-identifier>-<run-short-id>` and `agent/<project-identifier>/<issue-identifier>-<run-short-id>`, with the first as default.
  A resumed Run keeps its branch.
- **AR10 — Event transport:** The browser reads a durable Run-local event cursor and reconciles by event ID.
  V1 uses short cursor polling while active; Activity shows the card and conclusion while the panel keeps intermediate events.
- **AR11 — Capacity:** Plane owns a durable Code-capacity waiting state ordered by enqueue time and Run ID.
  The Worker takes a bounded Code slot before starting Docker and releases it after the container stops.
- **AR12 — Local deployment:** Plane API, PostgreSQL, Worker, Harness processes, and Docker code jobs run on the Mac Mini.
  People reach Plane through Tailscale; Worker calls Plane over localhost.
- **AR13 — Delivery probes:** The Claude model-reporting path, Grok permission pause/resume, and Q&A/Docker isolation across all four Harnesses remain required proof before v1 delivery.
  A failed probe keeps that Harness in Connection failed with the missing action named.

### UX Design Requirements

**UX-DR1: Run card.**
Show one card per mention in chronological Activity position with requester, verbatim request, Agent, kind, status, current action when active, elapsed time, and Open run action.
On conclusion, show comment markdown and, for Code jobs, draft PR number, title, Draft label, branch, diff summary, and human-merge note.

**UX-DR2: Mention picker.**
Add Agent rows beside people in the existing comment editor with icon, name, handle, and live connection tag.
Show disconnected Agents as disabled with a clear reason.
Selecting an Agent inserts its mention; saving the comment creates the Run.

**UX-DR3: Run panel layout.**
Open a right-side panel on the work item with header, scrolling timeline, and fixed composer.
Allow width from 380 to 960 px, default 540 px, and remember width per member.
The header identifies the Agent, work item, Run kind, status, start time, active CWD and sandbox mode, elapsed time, and activity count.
Closing the panel leaves the Run card available to reopen the same panel.

**UX-DR4: Run status presentation.**
Use distinct icon, text, and semantic status color for waiting, in progress, awaiting a person, permission needed, completed, failed, stale, and stopped.
Show active elapsed time and a status-specific banner or live line when relevant.

**UX-DR5: Durable timeline rows.**
Render user messages, thoughts, tool calls, results, elicitation, permissions, errors, PR details, and streaming progress with the handoff's row types.
Collapse thought and tool detail by default while leaving it expandable after completion.
Group active thoughts and actions under a Working batch with a step count and allow batch disclosure.
After completion, show the duration and start the completed work batch collapsed while keeping its actions and results available.

**UX-DR6: Plan display.**
Show a collapsible plan only when a Run has one, with done, doing, and todo row states and progress count.
Show an estimated time only when the Harness reports one.
Remember collapse choice per member.

**UX-DR7: Queue display.**
Show a collapsible ordered queue only when it has messages.
Each item shows its number and text and offers Send now and remove actions.
Remember collapse choice per member.

**UX-DR8: Run composer and steering.**
Show an input and send action whose labels change between reply and queue modes, conditional Stop, and current delivery or cancellation state.
Send now and Stop must match the selected Harness's verified behavior and remain usable by keyboard.

**UX-DR9: Stop confirmation and recovery.**
Confirm Stop, clear undelivered messages, retain sandbox and Worktree, and show the stopping actor and time.
Show how many queued messages were discarded.
Keep the composer enabled so a member can continue the same Run.

**UX-DR10: Permission card.**
Before first write or escalation, show the action, proposed command, affected files or paths, active Worktree, scope, risk, and Allow for this Run, Allow once, and Deny controls.
Keep the resolved card in the timeline with actor and timestamp.

**UX-DR11: Elicitation, stale, capacity, and failure states.**
Show selectable answers for a missing repository, Retry pickup and Mark failed for stale work, a waiting message at capacity, and an actionable failure reason for authentication or execution errors.
Show the five-minute stale threshold and a login hint for failed CLI preflight, with no Code container started on that failure.
Repository choices identify the remote; the Worker creates this Run's clone only after a choice is confirmed.

**UX-DR12: Integrations index.**
Use Plane's existing settings chrome with GitHub under Essentials and the four Harness cards under Harnesses.
Each card shows live connection state, name, version or location metadata, and its configure action.

**UX-DR13: GitHub device flow.**
Show disconnected, waiting with device URL, code, expiry, I entered the code, Cancel, connected installations, and failure states.
The connected detail page shows identity, grants, installations, and connection management.
Provide Connect organisation, Remove installation, Disconnect GitHub, and a back action to the Integrations list.

**UX-DR14: GitHub PR settings.**
Show draft PR, conclusion mirroring, and branch-format controls on the GitHub detail page.
Draft PR is on and conclusion mirroring is off by default.
The branch selector presents the two Run-unique formats from AR9 instead of the prototype's shorter example label.

**UX-DR15: Harness detail page.**
For each Harness, show the four-Harness selector with connection tags, a Mentionable switch, connect/retry/disconnect state, name, unique handle, instructions, and model selector.
Only show selectable models after connection, and give an actionable connection error.
Provide a back action to the Integrations list.

**UX-DR16: Project repository picker.**
Add a searchable repository section to the existing project creation modal, grouped by installation and filterable by owner.
Mark the selected repository and repositories bound to another project, show a warning when no repository is bound, and show a link to Integrations when GitHub is disconnected.
Do not show a shared Mirror clone progress state at project creation; the fresh clone starts for each Agent Run after a mention.

**UX-DR17: Semantic visual system.**
Reuse real Plane settings, work-item, Activity, comment-editor, `@plane/propel`, and `@plane/ui` components.
Use the handoff's semantic surface, text, border, spacing, typography, icon, and motion tokens without literal hex colors or copied prototype code.

**UX-DR18: Accessible responsive interaction.**
Preserve keyboard access and readable labels for picker rows, panel resizing, timeline disclosure, queue actions, permission decisions, and dialogs.
Keep the panel and settings layout usable at supported viewport widths.

### FR Coverage Map

FR1: Epic 1 — Connect, cancel, disconnect, and manage GitHub installations.
FR2: Epic 1 — Configure draft PR, conclusion mirroring, and branch format before delivery.
FR3: Epic 1 — Select one accessible repository during project creation.
FR4: Epic 2 — Resolve a missing or ambiguous repository before launching a Run.
FR5: Epic 2 — Configure four Harness identities and connection states.
FR6: Epic 2 — Verify each Harness interaction path and reported models.
FR7: Epic 2 — Mention a connected Agent from the work-item editor.
FR8: Epic 2 — Create a separate Run and card for every new mention comment.
FR9: Epic 2 — Keep the complete ordered Run timeline and panel preferences.
FR10: Epic 2 — Keep Activity concise and the complete history in the panel; Epic 3 adds the PR link.
FR11: Epic 2 — Show Q&A state, progress, and failure; Epic 3 adds Code waiting and permission states.
FR12: Epic 2 — Queue, deliver, and steer follow-up messages on the same Run.
FR13: Epic 3 — Escalate an existing Run to a Code job.
FR14: Epic 3 — Request, enforce, and audit permission before write or access escalation.
FR15: Epic 2 — Stop and resume the same Run while retaining its clone; Epic 3 retains its Worktree.
FR16: Epic 2 — Answer from a fresh read-only Run clone without branch or PR.
FR17: Epic 3 — Work in an isolated Run Worktree and branch without default-branch merge.
FR18: Epic 3 — Deliver and report a draft GitHub pull request.
FR19: Epic 2 — Detect and recover stale Q&A work; Epic 3 owns bounded Code capacity and its durable waiting state.
FR20: Epic 2 — Anchor the Run to the exact trigger comment, issue, project, and repository.
FR21: Epic 2 — Include authorized issue and prior-comment content in the first prompt.
FR22: Epic 2 — Continue the Run with current context across turns and process restarts; Epic 3 retains the active Worktree CWD.
FR23: Epic 2 — Preserve context limits, authorized retrieval, and member-content trust boundaries.

## Epic List

### Epic 1: Connect GitHub and bind a project repository
A workspace administrator can connect and manage GitHub, set the Agent pull-request defaults, and bind one accessible repository while creating a project.
This setup is usable before any Agent Run exists and gives later Runs an unambiguous repository.
**FRs covered:** FR1, FR2, FR3.
**Implementation notes:** Use Plane-owned GitHub identity and project binding; do not assume current CE code already creates Agent pull requests.

### Epic 2: Ask and interact with a local Agent on a work item
A member can mention any of the four connected CLI Agents, see a separate durable Q&A Run, inspect its context and progress, ask follow-ups, steer or stop it, and recover stale work.
Each mention uses a fresh read-only clone and receives only authorized issue and conversation context.
**FRs covered:** FR4–FR12, FR15, FR16, FR19 (stale recovery), FR20–FR23.
**Implementation notes:** Deliver the Plane Run, event, queue, context, Worker lease, and four-driver interaction contract as complete vertical slices.
Do not mark a Harness Connected until its local conformance probe proves the required Run interaction and model behavior.

### Epic 3: Turn a Run into a safe Code job and deliver a draft PR
A member can ask an existing Run to implement or fix, approve each proposed effect, see a capacity wait when Docker is full, and receive a draft pull request for human review.
The Run keeps its conversation and uses its own Worktree as the active CWD after escalation.
**FRs covered:** FR13, FR14, FR17–FR19; extends FR10, FR11, FR15, and FR22 for Code work.
**Implementation notes:** Prove the OS and Docker boundaries, request-bound grants, slot accounting, branch uniqueness, and GitHub draft-PR path before release.

## Epic 1: Connect GitHub and bind a project repository

A workspace administrator can connect and manage GitHub, set Agent pull-request defaults, and bind one accessible repository while creating a project.

### Story 1.1: Connect a GitHub account with device flow

As a workspace administrator,
I want to connect my GitHub account from Integrations,
So that Plane can list repositories granted to this workspace.

**Covers:** FR1, UX-DR12, UX-DR13, UX-DR18.

**Acceptance Criteria:**

**Given** GitHub is disconnected
**When** I open Integrations
**Then** I see the GitHub setup state and an Authenticate action.

**Given** I use only a keyboard or screen reader
**When** I move through the device-flow controls
**Then** each state, code, expiry, and action has a readable label and focus order.

**Given** I start authentication
**When** GitHub issues a device code
**Then** Plane shows the verification URL, code, expiry, I entered the code, and Cancel actions.

**Given** I authorize before expiry
**When** Plane verifies the device flow
**Then** it stores the workspace connection and shows my identity, granted installations, and connected state after refresh.

**Given** I open the connected GitHub detail page
**When** I select its Integrations back action
**Then** I return to the existing settings list with the correct Connected tag.

**Given** I cancel, the code expires, or GitHub rejects authorization
**When** the flow settles
**Then** Plane shows the correct disconnected or actionable error state and does not create a connection.

**Given** the connection is active
**When** Plane displays or logs the flow
**Then** no access token appears in the UI, Run context, or logs.

### Story 1.2: Connect a GitHub organization

As a workspace administrator,
I want to connect an organization from the GitHub detail page,
So that project members can choose repositories that organization grants.

**Covers:** FR1, UX-DR13.

**Acceptance Criteria:**

**Given** my workspace has a GitHub connection
**When** I open its detail page
**Then** I see the existing installations and a Connect organisation action.

**Given** I start that action
**When** GitHub grants access to an organization
**Then** Plane shows the organization and its granted repositories without a duplicate installation.

**Given** I cancel or GitHub denies the request
**When** the connection flow ends
**Then** the existing installations remain unchanged and I see an actionable error or cancellation state.

**Given** the organization is connected
**When** a project member opens the repository picker
**Then** the picker includes only repositories granted to this workspace and available to that member.

### Story 1.3: Remove one GitHub installation

As a workspace administrator,
I want to remove one GitHub installation from Plane,
So that its repositories are no longer offered for new Agent work.

**Covers:** FR1, UX-DR13.

**Acceptance Criteria:**

**Given** the workspace has multiple installations
**When** I remove one installation and confirm
**Then** only that installation disappears from the GitHub detail page and new project repository picker.

**Given** an existing project is bound to a repository from the removed installation
**When** the grant is removed
**Then** Plane keeps the project binding for audit but marks it unavailable for new Runs instead of silently choosing another repository.

**Given** the removal request fails
**When** Plane receives the failure
**Then** it keeps the installation visible and shows an actionable error.

### Story 1.4: Disconnect the workspace GitHub account

As a workspace administrator,
I want to disconnect GitHub from the workspace,
So that Plane stops using that connection for Agent work.

**Covers:** FR1, UX-DR13.

**Acceptance Criteria:**

**Given** GitHub is connected
**When** I select Disconnect and confirm
**Then** Integrations returns to the disconnected setup state and the saved connection can no longer list repositories or create Agent pull requests.

**Given** existing projects or Runs reference that connection
**When** I disconnect it
**Then** their historical records remain visible, while new Agent launches or pending pull-request delivery fail with a clear missing-connection reason.

**Given** disconnection fails
**When** Plane receives the failure
**Then** it does not claim the connection is removed and shows an actionable error.

### Story 1.5: Bind one repository while creating a project

As a project creator,
I want to select one GitHub repository during project creation,
So that Agent Runs know which repository belongs to the project.

**Covers:** FR3, UX-DR16, UX-DR17, UX-DR18.

**Acceptance Criteria:**

**Given** GitHub is connected
**When** I open the new-project form
**Then** I can search granted repositories, filter by owner, and view them grouped by installation.

**Given** I use a keyboard to select a repository
**When** I move through owners, search results, and selection
**Then** each repository's name, availability, and selected state are announced without relying on color alone.

**Given** Plane uses a different theme or viewport width
**When** the repository section renders
**Then** it uses the handoff's semantic tokens and existing project form components without hiding search, filters, warnings, or selection.

**Given** another project already owns a repository
**When** I view that repository
**Then** it is marked unavailable and cannot be bound again.

**Given** I select an available repository and create the project
**When** the project is saved
**Then** Plane stores exactly one repository identity and base ref for that project and shows the selected state.

**Given** I create a project without selecting a repository
**When** I review the form
**Then** I see that an Agent Run will ask for a repository and cannot launch its Harness until that choice is resolved.

**Given** GitHub is disconnected
**When** I open the repository section
**Then** I see the missing-connection state and a link to Workspace settings → Integrations.

**Given** the project is saved with a repository
**When** no Agent Run exists yet
**Then** Plane does not create a shared Mirror; each later mention will request its own clone.

### Story 1.6: Set the draft pull-request default

As a workspace administrator,
I want to choose whether Agent pull requests open as drafts,
So that the workspace has an explicit review policy.

**Covers:** FR2, UX-DR14.

**Acceptance Criteria:**

**Given** the GitHub detail page is available
**When** I view its pull-request settings for the first time
**Then** Open pull requests as drafts is on by default.

**Given** I change the draft setting
**When** I return to the page or refresh it
**Then** the saved setting remains visible and the Agent delivery policy reads the same value.

**Given** I lack workspace administration rights
**When** I view the setting
**Then** I cannot change it.

### Story 1.7: Set conclusion mirroring to pull requests

As a workspace administrator,
I want to control whether Run conclusions are also posted to Agent pull requests,
So that GitHub comments follow the team's preference.

**Covers:** FR2, UX-DR14.

**Acceptance Criteria:**

**Given** the GitHub detail page is available
**When** I view its pull-request settings for the first time
**Then** Post run conclusions as PR comments is off by default.

**Given** I change the mirroring setting
**When** I return to the page or refresh it
**Then** the saved setting remains visible and the Agent delivery policy reads the same value.

**Given** I lack workspace administration rights
**When** I view the setting
**Then** I cannot change it.

### Story 1.8: Choose the Agent branch format

As a workspace administrator,
I want to select the format for Agent branches,
So that draft pull requests use a consistent Run-unique name.

**Covers:** FR2, UX-DR14.

**Acceptance Criteria:**

**Given** the branch-format selector is new
**When** I open GitHub pull-request settings
**Then** `agent/<issue-identifier>-<run-short-id>` is selected by default.

**Given** I open the selector
**When** I choose a format
**Then** I can select either the default format or `agent/<project-identifier>/<issue-identifier>-<run-short-id>` and the choice persists after refresh.

**Given** two separate Runs mention the same issue
**When** branch names are generated from either format
**Then** their Run suffixes keep the branch names distinct.

**Given** a Run already owns a branch
**When** the workspace format later changes
**Then** that Run keeps its existing branch name.

## Epic 2: Ask and interact with a local Agent on a work item

A member can mention any of the four connected CLI Agents, inspect an accurate Q&A Run, converse and steer within that Run, and recover interrupted work.
Each mention receives a fresh read-only clone and authorized issue context.

### Story 2.1: Connect Claude Code as a local Harness

As a workspace administrator,
I want to connect the installed Claude Code CLI,
So that members can use a verified local Agent instead of a guessed connection.

**Covers:** FR5, FR6, UX-DR12, UX-DR15, UX-DR17, UX-DR18.

**Acceptance Criteria:**

**Given** I open Integrations
**When** I select Claude Code
**Then** I see four Harness cards and a detail-page selector with live connection tags, plus Claude's Not connected, Connecting, Connected, or Connection failed state.

**Given** a Harness detail page is open
**When** I select its Integrations back action
**Then** I return to the settings list without changing its connection state.

**Given** I use another Plane theme or a supported viewport width
**When** Integrations and Harness details render
**Then** they reuse Plane settings chrome and Propel components with semantic tokens and keep all controls readable and keyboard accessible.

**Given** I select Connect or Retry
**When** the Worker probes the installed CLI
**Then** Plane records its usable model report and verified conversation, progress, native midturn delivery, cancellation, permission, and recovery capabilities before showing Connected.

**Given** a required capability, authentication, or model report cannot be verified
**When** the probe ends
**Then** the page shows Connection failed with the missing action and a retry path rather than a hard-coded model list.

**Given** the Harness is Connected
**When** I select Disconnect
**Then** new mentions become unavailable while existing Run records remain readable.

### Story 2.2: Rename a workspace Agent

As a workspace administrator,
I want to edit an Agent's display name,
So that members recognize it in settings and the mention picker.

**Covers:** FR5, UX-DR15.

**Acceptance Criteria:**

**Given** an Agent detail page is open
**When** I save a valid new name
**Then** Integrations and future mention suggestions show that name after refresh.

**Given** I submit an empty or invalid name
**When** Plane validates it
**Then** the field shows a useful error and the previous name remains saved.

**Given** a Run was created before the rename
**When** I open it
**Then** the Run keeps its stable Agent and Run identities and historical events.

### Story 2.3: Set a unique Agent mention handle

As a workspace administrator,
I want to set an Agent's workspace-unique mention handle,
So that a comment targets the intended Harness.

**Covers:** FR5, UX-DR15.

**Acceptance Criteria:**

**Given** an Agent detail page is open
**When** I save an unused valid handle
**Then** future mention suggestions and saved comments resolve that handle to this Agent.

**Given** another Agent already owns the handle
**When** I try to save it
**Then** Plane rejects the collision with an inline error and leaves both existing handles unchanged.

**Given** a Run was created with the old handle
**When** the handle changes
**Then** that Run still refers to the same Agent ID and its conversation remains intact.

### Story 2.4: Set an Agent's workspace instructions

As a workspace administrator,
I want to edit an Agent's instructions,
So that new Runs follow the team's approved guidance.

**Covers:** FR5, FR23, UX-DR15.

**Acceptance Criteria:**

**Given** an Agent detail page is open
**When** I save new instructions
**Then** the text remains after refresh and future Runs receive it as Agent configuration.

**Given** issue descriptions or comments contain instruction-like text
**When** the Worker builds the prompt
**Then** it separates that member content from the saved Agent instructions and does not promote the member content to system policy.

**Given** a Run already exists
**When** I change the Agent instructions
**Then** its existing events remain unchanged and new Runs use the new instructions.

### Story 2.5: Toggle whether an Agent is mentionable

As a workspace administrator,
I want to enable or disable new mentions of an Agent,
So that I can control which local Harnesses members may invoke.

**Covers:** FR5, FR7, UX-DR2, UX-DR15.

**Acceptance Criteria:**

**Given** an Agent detail page is open
**When** I change its Mentionable switch
**Then** the saved state remains after refresh and the mention picker reflects it.

**Given** the Agent is disabled or disconnected
**When** a member types its handle
**Then** the picker may show it with a reason but cannot start a new Run from it.

**Given** that Agent already has an active Run
**When** I disable new mentions
**Then** the existing Run and its audit history remain available.

### Story 2.6: Select a model reported by a connected Harness

As a workspace administrator,
I want to choose from the models the connected Harness reports,
So that new Runs use the team's selected model.

**Covers:** FR6, UX-DR15.

**Acceptance Criteria:**

**Given** a Harness is Connected and reports models
**When** I open its model selector
**Then** I see those reported choices and can save one per workspace Agent.

**Given** I refresh the page
**When** the settings load
**Then** the selected model remains visible and new Runs use it.

**Given** the Harness is disconnected or its model report fails
**When** I view the model row
**Then** selection is unavailable and no mock model is presented as verified.

**Given** an existing Run has already started
**When** I change the workspace Agent model
**Then** that Run keeps its chosen model unless a later explicit Run control changes it.

### Story 2.7: Ask Claude Code about a work item

As a member who can comment on a work item,
I want to mention Claude and receive an answer grounded in that item and its repository,
So that I can ask for help without leaving Plane.

**Covers:** FR7, FR8, FR10, FR11, FR16, FR20, FR21, FR23, UX-DR1, UX-DR2, UX-DR4, UX-DR11.

**Acceptance Criteria:**

**Given** Claude is Connected and Mentionable and the project has one usable repository
**When** I save a comment that mentions Claude
**Then** the comment and a new Run commit together, and Activity shows one Q&A card with my request and an Open run action.

**Given** I type @ in the existing comment editor
**When** mention suggestions open
**Then** people and Agents appear together, and an unavailable Agent stays visible with a reason but cannot be selected.

**Given** the Worker claims that Run
**When** it prepares Claude
**Then** it creates a fresh Run-ID clone outside the Plane checkout and starts Claude in that clone under an OS boundary that denies writes.

**Given** Plane and the Worker run on the Mac Mini
**When** the Worker picks up a Run
**Then** it polls the authenticated Plane API over localhost without a public Worker callback, while members continue to reach Plane through Tailscale.

**Given** the Run starts
**When** Plane builds its first context snapshot
**Then** the prompt identifies the exact workspace, project, issue identifier and link, current title, description, status, repository, requester, trigger comment, and authorized earlier comments in order with source IDs, authors, and times.

**Given** the issue title, description, or comments contain instructions
**When** the Worker formats the prompt
**Then** that content remains task data below Agent policy and cannot import another Run's private panel messages.

**Given** Claude completes a Q&A turn
**When** the result reaches Plane
**Then** the answer appears in the Run and as one conclusion comment, while no branch, Worktree, Docker code job, or PR is created.

**Given** a Worker delivery is retried
**When** Plane receives a repeated command or event
**Then** its idempotency key and Run-local event sequence prevent a duplicate Run, conclusion, or timeline event.

**Given** I save another Agent mention comment on the same issue
**When** Plane creates that Run
**Then** it has a different Run ID, clone, CWD, card, and private conversation.

**Given** two valid Q&A Runs exist
**When** the Worker has capacity for both
**Then** they may progress concurrently without sharing CWD, process state, or timeline events.

**Given** the CLI cannot authenticate or the read-only boundary rejects a write
**When** the Worker handles the failure
**Then** the Run fails visibly with a useful reason and a concise failure conclusion, with no write to the clone or Plane checkout.

### Story 2.8: Inspect a durable Run timeline

As a work-item member,
I want to inspect the Run's complete ordered activity in a panel,
So that I can see what the Agent did after the live turn ends.

**Covers:** FR9, FR10, FR11, UX-DR1, UX-DR3, UX-DR4, UX-DR5, UX-DR17, UX-DR18.

**Acceptance Criteria:**

**Given** a Run card is visible
**When** I open it
**Then** its right-side panel has a header, scrolling timeline, fixed composer, and ordered prompts, thoughts, actions, results, elicitation, errors, and conclusion with readable status and elapsed time.

**Given** a Run panel is open
**When** its header renders
**Then** it identifies the Agent, work item, Run kind, status, start time, active CWD and sandbox mode, elapsed time, and activity count.

**Given** I inspect a Run state
**When** it is waiting, working, awaiting me, needs permission, completed, failed, stale, or stopped
**Then** the panel and card use the handoff's distinct icon, label, and semantic status color without relying on color alone.

**Given** an action or thought has detail
**When** I expand or collapse its Working group or row
**Then** the full detail remains available after completion, with a step count while active and duration when done.

**Given** new events arrive or I refresh
**When** the panel reads its Run-local cursor
**Then** it reconciles by event ID without missing or duplicating entries.

**Given** I close the panel
**When** I select Open run again
**Then** I return to the same Run and its durable history.

**Given** I use a keyboard or screen reader
**When** I navigate timeline groups and close or reopen the panel
**Then** disclosure state, event labels, current status, and focus remain understandable.

**Given** I switch Plane's theme
**When** the Run card and panel render
**Then** they use Plane and Propel semantic surface, text, border, spacing, icon, and motion tokens rather than literal prototype colors or copied HTML.

**Given** the Run is active
**When** the Agent emits progress
**Then** the panel shows streaming activity and the current state, while the work-item Activity feed shows only the card and conclusion.

### Story 2.9: Resize the Run panel

As a work-item member,
I want to resize the Run panel,
So that I can read the issue and Agent activity side by side.

**Covers:** FR9, UX-DR3, UX-DR18.

**Acceptance Criteria:**

**Given** the Run panel is open
**When** I drag or use the keyboard on its resize boundary
**Then** the panel width changes within 380–960 px without hiding its controls.

**Given** I choose a width
**When** I close and reopen the panel or refresh
**Then** that width is restored for me without changing another member's preference.

### Story 2.10: Follow an Agent's plan

As a work-item member,
I want to view the Agent's plan when it reports one,
So that I know which steps are done and what remains.

**Covers:** FR9, UX-DR6.

**Acceptance Criteria:**

**Given** the Harness reports a plan
**When** I open the Run panel
**Then** I see its done, doing, and todo steps, progress count, and an estimate only if one was reported.

**Given** I collapse or expand the plan
**When** I reopen the Run
**Then** my disclosure choice remains and the plan's latest state is still available.

**Given** the Harness reports no plan
**When** I open the Run panel
**Then** no empty plan section appears.

### Story 2.11: Choose a repository for an unbound Run

As a work-item member,
I want to choose the repository when a Run cannot identify one,
So that the Agent reads the intended project code.

**Covers:** FR4, UX-DR11.

**Acceptance Criteria:**

**Given** a mention creates a Run with no usable repository binding
**When** the Run opens
**Then** it asks me to choose an authorized repository and does not launch a Harness or create a clone yet.

**Given** several authorized candidates exist
**When** I choose one in the panel
**Then** Plane records that choice for this Run and the Worker creates a fresh Run-specific clone of that remote before launching the Harness.

**Given** no usable candidate exists or the chosen grant is revoked
**When** I try to continue
**Then** the Run remains awaiting a repository with a useful path to resolve the binding and no write occurs.

**Given** a repository is selected
**When** the Worker launches the Harness
**Then** its CWD and context snapshot refer to that exact repository, never the Plane deployment checkout or the Worker's incidental CWD.

### Story 2.12: Retrieve older authorized issue comments

As a member asking an Agent about a long work item,
I want the Agent to access omitted older comments when needed,
So that context limits do not silently remove important history.

**Covers:** FR23, UX-DR11.

**Acceptance Criteria:**

**Given** issue history exceeds the Harness context budget
**When** Plane builds the first prompt
**Then** it preserves issue identity, current request, essential issue content, and an exact omission count with an authorized retrieval path.

**Given** the Agent requests older comments through that path
**When** Plane returns a page
**Then** it includes only comments visible to the requester from the Run's issue, ordered with stable IDs, authors, and times.

**Given** a comment belongs to another issue, another workspace, or another Run's private panel
**When** the Agent uses the retrieval path
**Then** Plane does not return it.

### Story 2.13: Send a follow-up in the same Run

As a work-item member,
I want to reply in a Run panel,
So that the Agent continues the same conversation and repository context.

**Covers:** FR12, FR22, UX-DR8.

**Acceptance Criteria:**

**Given** a Q&A Run has finished a turn
**When** I send a panel reply
**Then** Plane stores the message on that Run and the Worker starts its next turn in the same Run clone.

**Given** the issue or its comments changed since the previous turn
**When** the Worker builds the follow-up prompt
**Then** it supplies relevant ordered deltas and the prior same-Run messages and decisions without importing another Run's private history.

**Given** the Harness process exited after the previous turn
**When** a follow-up starts
**Then** the Worker resumes its native session or reconstructs from durable Plane context and transcript while keeping the same Plane Run ID.

**Given** the follow-up finishes
**When** I reopen the panel
**Then** both turns and their conclusion remain in order on one Run card.

### Story 2.14: Queue a message during active work

As a work-item member,
I want to queue a message while the Agent works,
So that I can add direction without losing the current turn.

**Covers:** FR12, UX-DR7, UX-DR8, UX-DR18.

**Acceptance Criteria:**

**Given** a Run is in progress
**When** I send from its queue-mode composer
**Then** Plane stores the message as queued with a visible ordered position and does not claim Harness acceptance.

**Given** the composer switches between idle and active work
**When** I view its input and send action
**Then** their labels distinguish Reply from Queue so I know whether the message will be delivered now or later.

**Given** the Harness reaches a safe delivery point
**When** the Worker drains the queue
**Then** it sends messages in Plane order and marks each accepted only after the Harness acknowledges it.

**Given** I collapse or expand the Queue section
**When** I reopen the Run
**Then** my disclosure preference and the durable queue state remain visible.

**Given** I use only a keyboard or screen reader
**When** I inspect or act on the queue
**Then** its order, waiting count, disclosure, Send now, and remove actions are operable and named.

**Given** a Worker restarts with queued messages
**When** it reclaims the Run
**Then** it does not deliver an already accepted message twice.

### Story 2.15: Send a queued message now

As a work-item member,
I want to send a selected queued message immediately,
So that I can redirect active work without starting a new Run.

**Covers:** FR12, UX-DR7, UX-DR8.

**Acceptance Criteria:**

**Given** the Harness has verified native midturn input
**When** I select Send now
**Then** the Worker sends the selected message into the active turn and marks it accepted only after acknowledgment.

**Given** the Harness lacks verified midturn input
**When** I select Send now
**Then** the Worker cancels the current turn, waits for its terminal state or timeout, and sends that message as the next turn in the same Run.

**Given** cancellation or delivery is pending
**When** I view the queue and timeline
**Then** they show the pending state, preserve event order, and do not report the message as delivered early.

**Given** the active process does not settle safely
**When** the timeout is reached
**Then** the Run shows an actionable error and does not start a competing turn in the same CWD.

### Story 2.16: Remove an undelivered queued message

As a work-item member,
I want to remove a queued message before delivery,
So that the Agent does not follow an instruction I withdrew.

**Covers:** FR12, UX-DR7.

**Acceptance Criteria:**

**Given** a message is still queued
**When** I select its remove action
**Then** Plane marks that message cancelled and the Worker never delivers it.

**Given** a message is already dispatching or accepted
**When** I try to remove it
**Then** Plane does not pretend to retract it and shows the actual state.

**Given** I refresh the panel
**When** the queue reloads
**Then** the cancelled message is absent from the waiting count while its audit event remains available.

### Story 2.17: Stop an active Run

As a member who can comment on the work item,
I want to stop an active Run after confirmation,
So that the Agent stops taking further actions under my request.

**Covers:** FR15, UX-DR8, UX-DR9.

**Acceptance Criteria:**

**Given** a Run is active
**When** I select Stop
**Then** Plane asks for confirmation and explains that the current action is interrupted, the queue clears, and the Run clone is kept.

**Given** I confirm Stop
**When** the Worker receives the fenced command
**Then** it interrupts the Harness, prevents later tool actions in that turn, and records Stopped with my identity, time, and number of discarded queued messages.

**Given** I cancel the confirmation
**When** I return to the panel
**Then** the Run continues without a Stop command.

**Given** I lack comment permission
**When** I try to stop the Run
**Then** Plane rejects the command without changing Run state.

### Story 2.18: Resume a stopped Run

As a work-item member,
I want to reply to a stopped Run,
So that the Agent continues in its existing conversation and clone.

**Covers:** FR15, FR22, UX-DR9.

**Acceptance Criteria:**

**Given** the Run is Stopped
**When** I send a new panel message
**Then** Plane starts a new turn on the same Run ID, keeps the clone, and shows the previous history.

**Given** the old Harness process is gone
**When** the Worker resumes
**Then** it uses a native session when valid or reconstructs from Plane's durable context and transcript without silently switching the work item.

**Given** the Run clone cannot be verified
**When** resume is requested
**Then** the Run shows a recoverable error and does not launch in another CWD.

### Story 2.19: Retry a stale Run safely

As a work-item member,
I want to retry pickup of a stale Run,
So that work can continue after the Worker reconnects.

**Covers:** FR19, UX-DR11.

**Acceptance Criteria:**

**Given** Plane remains available and a Run has no Worker update for five minutes
**When** I view the Run
**Then** it shows Stale, last progress time, and Retry pickup without deleting its history.

**Given** I select Retry pickup
**When** a Worker claims the Run
**Then** Plane issues a new lease generation, rejects old-generation writes, and the Worker reconciles or stops the prior process before resuming.

**Given** the prior turn may have caused an external effect
**When** recovery reaches that effect
**Then** the Worker does not replay it without a new user command.

**Given** the Worker remains unavailable
**When** I retry
**Then** the Run stays visibly stale or waiting rather than claiming completion.

### Story 2.20: Mark a stale Run failed

As a work-item member,
I want to mark an unrecoverable stale Run failed,
So that the issue shows an honest final state.

**Covers:** FR19, UX-DR11.

**Acceptance Criteria:**

**Given** a Run is Stale and I may comment on its work item
**When** I select Mark failed and confirm
**Then** Plane records Failed with my identity, time, and reason, while retaining the timeline and clone for review.

**Given** an old Worker later sends an event
**When** Plane checks its lease generation
**Then** it rejects the stale update and does not change the failed conclusion.

**Given** I lack comment permission
**When** I try to mark the Run failed
**Then** Plane rejects the action.

### Story 2.21: Connect Codex CLI as a local Harness

As a workspace administrator,
I want to connect the installed Codex CLI,
So that members can choose a verified Codex Agent.

**Covers:** FR5, FR6, UX-DR15.

**Acceptance Criteria:**

**Given** I open the Codex detail page
**When** I select Connect or Retry
**Then** the Worker checks the local app-server transport, authentication, reported models, events, follow-up, steering, cancellation, approval, and recovery behavior.

**Given** the probe succeeds
**When** Plane receives its result
**Then** Codex shows Connected with models reported by `model/list` and its verified interaction capabilities.

**Given** authentication or a required control fails
**When** the probe ends
**Then** Codex shows Connection failed with a specific recovery hint and remains unavailable for new mentions.

### Story 2.22: Ask and converse with Codex on a work item

As a work-item member,
I want to mention Codex and continue talking with it in the Run panel,
So that I can use Codex for read-only issue questions.

**Covers:** FR7, FR8, FR12, FR16, UX-DR2, UX-DR8.

**Acceptance Criteria:**

**Given** Codex is Connected and Mentionable
**When** I save a Codex mention comment
**Then** Plane creates a separate Q&A Run with a fresh read-only clone, anchored issue context, card, panel, and conclusion comment.

**Given** that Codex Run is active or has finished a turn
**When** I queue, send now, follow up, stop, or resume
**Then** the Worker uses the verified Codex control path and Plane preserves one ordered Run conversation.

**Given** the Codex process fails or restarts
**When** the Run continues
**Then** Plane shows the real state and retains its transcript, clone, and event cursor without claiming lost work completed.

### Story 2.23: Connect Grok CLI as a local Harness

As a workspace administrator,
I want to connect the installed Grok CLI,
So that members can choose Grok only when its full Run interaction is safe.

**Covers:** FR5, FR6, UX-DR15.

**Acceptance Criteria:**

**Given** I select Connect or Retry for Grok
**When** the Worker probes the local headless CLI
**Then** it verifies authentication, reported models, streaming events, resumed follow-up turns, cancellation, and a safe permission pause and response path.

**Given** Grok has no verified native midturn input
**When** the probe records its capabilities
**Then** Plane uses the queue and cancel-then-next-turn behavior and does not claim native midturn delivery.

**Given** permission pause and resume, isolation, or another required control cannot be proven
**When** the probe ends
**Then** Grok stays Connection failed with the missing behavior named, and Plane does not enable new Grok Runs.

**Given** all required controls pass
**When** Plane marks Grok Connected
**Then** its model selector uses the live CLI report, not the mockup's model names.

### Story 2.24: Ask and converse with Grok on a work item

As a work-item member,
I want to mention Grok and continue its Run conversation,
So that Grok can answer read-only issue questions with visible control.

**Covers:** FR7, FR8, FR12, FR16, UX-DR2, UX-DR8.

**Acceptance Criteria:**

**Given** Grok is Connected and Mentionable
**When** I save a Grok mention comment
**Then** Plane creates a separate Q&A Run in a fresh read-only clone with anchored issue context, progress, and a conclusion comment.

**Given** Grok completes a headless turn
**When** I send a panel follow-up
**Then** the Worker resumes or reconstructs the Grok session from that Run's durable context and transcript.

**Given** I select Send now while Grok has no midturn input
**When** the Worker applies the command
**Then** it cancels and settles the active turn before delivering the selected message as the next turn on the same Run.

**Given** Grok requests an effect outside the read-only boundary
**When** the request is checked
**Then** it is blocked or routed through a visible Plane permission request before any effect occurs.

### Story 2.25: Connect Omp as a local Harness

As a workspace administrator,
I want to connect the installed Omp CLI,
So that members can choose an Omp Agent with verified interaction controls.

**Covers:** FR5, FR6, UX-DR15.

**Acceptance Criteria:**

**Given** I select Connect or Retry for Omp
**When** the Worker probes its local stdio RPC transport
**Then** it verifies authentication, `get_available_models`, prompt, steer, follow-up, abort, UI-response, event, and session-recovery behavior.

**Given** the probe succeeds
**When** Plane records the result
**Then** Omp shows Connected with reported models and only the native controls that were verified.

**Given** a required control or model report fails
**When** the probe ends
**Then** Omp shows Connection failed with the missing action and remains unavailable for new mentions.

### Story 2.26: Ask and converse with Omp on a work item

As a work-item member,
I want to mention Omp and continue its Run conversation,
So that I can use Omp for read-only issue questions.

**Covers:** FR7, FR8, FR12, FR16, UX-DR2, UX-DR8.

**Acceptance Criteria:**

**Given** Omp is Connected and Mentionable
**When** I save an Omp mention comment
**Then** Plane creates a separate Q&A Run with a fresh read-only clone, anchored issue context, durable timeline, and conclusion comment.

**Given** that Omp Run is active
**When** I queue, send now, answer a question, or stop
**Then** the Worker maps the verified Omp RPC commands and events into the same Plane Run states without losing message order.

**Given** the Omp process restarts
**When** I continue the Run
**Then** Plane keeps its Run ID, clone, prior messages, and event cursor, and shows any unrecoverable turn as an error.

## Epic 3: Turn a Run into a safe Code job and deliver a draft PR

A member can request a code change in an existing Run, decide whether proposed effects may execute, and receive a reviewable GitHub pull request without giving the Agent merge rights.
The Code job retains the conversation, uses its own Worktree, and waits for a bounded Docker slot when needed.

### Story 3.1: Deliver a code change after one-time approval

As a work-item member,
I want to ask an existing Agent Run to implement a change and receive a pull request,
So that a human can review the result before merge.

**Covers:** FR10, FR11, FR13, FR14, FR17, FR18, FR22, UX-DR1, UX-DR4, UX-DR10, UX-DR17, UX-DR18.

**Acceptance Criteria:**

**Given** a Q&A Run has a usable bound repository
**When** I ask it in the panel to implement or fix the work item
**Then** that same Run becomes a Code job, keeps its card and conversation, and creates a Run-owned Worktree and Run-unique branch inside its clone.

**Given** the Agent proposes its first write
**When** Plane creates a permission request
**Then** the panel shows the exact proposed effect, affected paths, Worktree, scope, risk, and Allow once, Allow for this Run, and Deny actions before any write.

**Given** I use only a keyboard or screen reader
**When** a permission request appears
**Then** its command, scope, risk, and three decisions are readable and operable without losing focus.

**Given** I choose Allow once for the current request
**When** the Worker checks the grant
**Then** it executes only the effect with that request ID, Run, turn, lease generation, action, normalized scope, and effect hash inside the bounded Docker sandbox.
For an additional-file write, Docker produces the exact bounded content and the trusted Worker publishes it through pinned descriptors under the same current grant, as accepted in AD-8.

**Given** the Agent proposes another write outside that one-time request
**When** the Worker checks its grant
**Then** Plane asks for a new decision before that write unless an applicable Run-scope grant exists.

**Given** a permission request is still pending
**When** a CLI tries to write through its own approval mode or a direct tool call
**Then** the OS and Docker boundary denies the effect until Plane supplies the matching grant.

**Given** the Code container starts
**When** the Agent inspects its environment
**Then** only the active Worktree is writable, the Plane checkout and default-branch push credential are absent, and configured memory, process, path, and network limits apply.

**Given** CLI authentication fails before Code launch
**When** the Worker preflights the Harness
**Then** the Run shows a failure conclusion and no Code container starts.

**Given** the Code job continues after the first write
**When** later turns or a restart occur
**Then** the Worktree stays the active CWD and the Run retains its transcript, branch, tests, permission events, and change summary.

**Given** the Worktree contains uncommitted work
**When** the Worker continues the Code job
**Then** it does not pull or rebase the origin into that Worktree while work is in progress.

**Given** the Agent completes code work
**When** the Worker pushes the Run branch and creates a pull request
**Then** the Run and Activity card show the PR number, title, Draft state by default, branch, diff summary, test result, and a human-merge note.

**Given** the Agent proposes a push or pull-request creation
**When** the Worker prepares that external effect
**Then** Plane requests the matching GitHub action grant and does not use a prior file-write grant as permission to publish.

**Given** the workspace draft setting is off
**When** a new Agent pull request is created
**Then** the Worker follows that saved setting without granting the Agent merge or default-branch push rights.

**Given** push or pull-request creation fails
**When** the Worker reports delivery
**Then** the Run shows a clear error, keeps the Worktree and branch for retry, and does not claim that a PR exists.

**Given** another mention targets the same issue
**When** its Code job starts
**Then** its separate clone and Run suffix prevent branch or file-state collision.

### Story 3.2: Grant a matching effect for the rest of a Run

As a work-item member,
I want to allow a proposed action and scope for this Run,
So that later matching effects do not require identical approvals.

**Covers:** FR14, UX-DR10.

**Acceptance Criteria:**

**Given** a durable permission request names an action and normalized scope
**When** I select Allow for this Run
**Then** Plane records my decision, time, request ID, action, scope, and effect hash in the Run timeline.

**Given** a later request in the same Run stays within the approved action and scope
**When** the Worker checks it
**Then** it may proceed under the Run grant while preserving a request-linked audit record.

**Given** a later request broadens the path, network access, action, or Run identity
**When** the Worker checks it
**Then** the old grant does not apply and Plane asks again before the effect.

### Story 3.3: Deny a proposed Agent effect

As a work-item member,
I want to deny a proposed write or escalation,
So that the Agent cannot perform an effect I did not approve.

**Covers:** FR14, UX-DR10.

**Acceptance Criteria:**

**Given** a permission request is pending
**When** I select Deny
**Then** Plane records my decision, time, request ID, action, and scope in the durable timeline.

**Given** the request was denied
**When** the Worker or Harness tries that effect
**Then** the OS or Docker boundary blocks it and the Run receives the denial as an interaction event.

**Given** the Agent proposes a materially different effect afterward
**When** it needs access
**Then** Plane creates a new permission request instead of reusing the denied one.

### Story 3.4: Decide a Code job's network escalation

As a work-item member,
I want to decide a Code job's request for network access,
So that the sandbox only reaches approved destinations when needed.

**Covers:** FR14, UX-DR10.

**Acceptance Criteria:**

**Given** a Code job has no network grant for a proposed action
**When** the Agent requests network access
**Then** Plane pauses the effect and shows the command, destination scope, risk, and decision actions.

**Given** I allow the request once or for this Run
**When** the Worker configures the sandbox
**Then** it opens only the approved scope for the matching request or later in-scope requests and records the grant.

**Given** I deny or the request scope changes
**When** the Agent attempts network access
**Then** the sandbox blocks unapproved access and the Run reports the denial without silently widening the grant.

### Story 3.5: Decide a Code job's path escalation

As a work-item member,
I want to decide whether a Code job can access an additional path,
So that its writable area remains limited to approved files.

**Covers:** FR14, UX-DR10.

**Acceptance Criteria:**

**Given** the Agent proposes access outside the active Worktree allow-list
**When** it asks for that path
**Then** Plane shows the normalized path, operation, command, and risk before changing sandbox access.

**Given** I allow that request once or for this Run
**When** the Worker updates the sandbox
**Then** only the approved path and operation become available within the grant's lifetime and scope.

**Given** the path is denied, uses a symlink escape, or targets the Plane checkout
**When** the Agent attempts access
**Then** the sandbox blocks it and records the attempted effect without writing outside the approved area.

### Story 3.6: Wait for a Code-job capacity slot

As a work-item member,
I want a Code job to wait visibly when the Mini is full,
So that Plane does not overload the host or lose my request.

**Covers:** FR19, UX-DR11.

**Acceptance Criteria:**

**Given** all configured Code slots are occupied
**When** another Run escalates to Code
**Then** Plane stores a visible waiting state ordered by enqueue time and Run ID and the Worker starts no additional container.

**Given** a slot becomes free
**When** the Worker starts the next waiting Code job
**Then** it claims one bounded slot before Docker launch and the Run moves to in progress without a second container for the same claim.

**Given** a Worker lease or container becomes stale
**When** slot recovery runs
**Then** it reconciles the actual container before releasing or reassigning capacity.

**Given** Q&A Runs continue while Code slots are full
**When** they are claimed
**Then** they do not consume a Docker Code slot.

### Story 3.7: Stop a Code job and retain its Worktree

As a member who can comment on the work item,
I want to stop an active Code job,
So that no more code effects occur while its work remains available for review.

**Covers:** FR15, FR17, UX-DR9.

**Acceptance Criteria:**

**Given** a Code job is active
**When** I confirm Stop
**Then** the Worker interrupts the Harness and container, clears undelivered messages, and records the actor, time, and stopped state.

**Given** the Code job stops
**When** I inspect its Run
**Then** the Run clone, Worktree, branch, timeline, and any existing PR remain available and no default-branch merge occurs.

**Given** the container has stopped
**When** the Worker releases its capacity slot
**Then** a waiting Code job may take that slot without exceeding the configured limit.

### Story 3.8: Resume a stopped Code job in its Worktree

As a work-item member,
I want to resume a stopped Code job by replying in its panel,
So that the Agent continues the same change instead of starting over.

**Covers:** FR15, FR17, FR22, UX-DR9.

**Acceptance Criteria:**

**Given** a stopped Code job has a verified retained Worktree
**When** I send a reply
**Then** Plane starts a new turn on the same Run and the Worker launches in that Worktree after it obtains a Code slot.

**Given** the old Harness process or vendor session is gone
**When** the Worker resumes
**Then** it reconstructs from Plane's durable transcript and context without changing Run ID, branch, or active CWD.

**Given** the Worktree, repository remote, or grant cannot be verified
**When** resume is requested
**Then** the Run shows a visible recovery error and does not launch in the clone, Plane checkout, or another repository.

### Story 3.9: Mirror a Run conclusion to its pull request

As a workspace administrator,
I want a finished Code Run's conclusion posted to its PR when mirroring is enabled,
So that reviewers can read the outcome in GitHub.

**Covers:** FR2, FR18, UX-DR14.

**Acceptance Criteria:**

**Given** conclusion mirroring is off
**When** a Code Run finishes
**Then** Plane posts its normal work-item conclusion and no new PR comment.

**Given** conclusion mirroring is on and the Run has a PR
**When** the Run conclusion is committed
**Then** the GitHub integration posts that conclusion once to the Run's PR and records the comment identity.

**Given** GitHub rejects the comment or the Worker retries delivery
**When** Plane reconciles the result
**Then** the Run shows the mirroring failure or existing comment without posting a duplicate or changing the work-item conclusion.
