---
title: Local CLI agents in Plane work items
status: final
created: 2026-09-27
updated: 2026-09-27
---

# PRD: Local CLI agents in Plane work items

## Document purpose

This PRD defines the behavior the internal team needs before architecture and implementation.
The [SPEC](../../_bmad-output/specs/spec-plane-local-cli-agents/SPEC.md) records the earlier contract, and the [design handoff](../../claude-design/design_handoff_local_cli_agents/README.md) records the approved v1 experience.
When the two sources differ, the design handoff defines v1 scope, as confirmed by the product owner on 2026-09-27.
In particular, v1 supports four Harnesses rather than two, waits at Code job capacity rather than refusing a Run, and requires permission before the first write.
Each new Agent mention also starts in a fresh clone and CWD for that Run, superseding the earlier shared Mirror design.

## Vision and users

A team member can hand a Plane work item to a local coding CLI by mentioning its Agent in a comment.
The member can follow the Run, answer questions, approve writes, steer work, and see the conclusion without leaving the work item.
A Code job delivers a draft pull request for human review and merge.
Plane and the Worker run on the team's Mac Mini; humans reach Plane through Tailscale.
This is an internal team tool.

Members who can comment need to ask Agents questions and request code changes.
Workspace administrators need to connect GitHub and Harnesses, choose models, and bind projects to repositories.

## User journeys

These journeys are extracted from the SPEC and the design handoff's 12 scenes.
The name Kevin comes from the handoff's example screens.

### UJ-1: Kevin configures a project and Agent

Kevin opens Workspace settings → Integrations and connects GitHub through the device flow.
He sees the granted personal and organization installations.
He connects a Harness, checks its connection state, and selects a model reported by that Harness.
When he creates a project, he searches the accessible repositories and binds one to the project.
The Agent appears in the work-item mention picker with its connection state.

### UJ-2: Kevin asks an Agent about a work item

Kevin mentions a connected Agent in a work-item comment.
Plane creates a new Agent Run card, and the local Worker picks up the Run.
The Worker clones the bound repository into a new CWD for this Run.
The Agent receives the project identity, current work-item content, earlier comments, and Kevin's triggering comment, then reads that clone without changing it.
Kevin opens the card to see the durable timeline and sends follow-up messages in its panel.
The conclusion appears on the work item; intermediate thoughts and tool calls remain in the panel.
A later comment with a new Agent mention starts a separate Run.

### UJ-3: Kevin asks the same Run to change code

Kevin asks the Agent to implement or fix something in the Run panel.
The Run becomes a Code job while keeping its card, timeline, and conversation.
Before its first write, Plane shows the action and scope and waits for Kevin's permission decision.
Kevin can queue a message, interrupt the current step with Send now, or stop the Run to steer it.
The Agent works in a Worktree owned by this Run's clone and delivers a draft pull request.
Kevin reviews and merges the pull request himself.

### UJ-4: Kevin recovers an interrupted Run

If the Agent needs a repository choice or permission, Kevin answers in the panel and the same Run continues.
If the Worker is at capacity, the Run stays visible while it waits for a slot.
If the Worker stops reporting progress, Kevin sees a stale warning and can retry pickup or mark the Run failed.
If Kevin stops the Run, its queue clears, its Worktree remains, and he can reply to resume the same sandbox.

## Glossary

- **Harness:** One supported local CLI: Claude Code, Codex CLI, Grok CLI, or Omp.
- **Agent:** A workspace identity for one Harness with a unique mention handle.
- **Agent Run:** One session created by a new Agent mention on a work item.
- **Run card:** The work-item Activity entry for one Agent Run.
- **Run panel:** The work-item side panel for a Run's timeline, plan, queue, and conversation.
- **Worker:** The local process that picks up Agent Runs and invokes Harnesses.
- **Q&A run:** The initial read-only work of an Agent Run.
- **Code job:** The same Run after a request to implement or fix.
- **Repository binding:** One repository selected for a Plane project.
- **Run clone:** A fresh clone of the bound repository with a CWD unique to one Agent Run.
- **Worktree:** The isolated working tree used for a Code job.
- **Permission request:** A decision required before the first write or an access escalation.
- **Context snapshot:** The project, work item, and earlier comment data assembled for one Agent Run at pickup.
- **Trigger comment:** The work-item comment whose Agent mention created that Run.

## Features and functional requirements

### 1. GitHub and project repository setup

This feature realizes UJ-1 and supports all code-related Runs.

#### FR-1: Connect GitHub

A workspace administrator can start, complete, cancel, and disconnect GitHub authentication from Workspace settings → Integrations.
The UI shows pending, connected, and failure states.
After connection, the administrator can see and manage granted personal and organization installations.

#### FR-2: Configure pull request behavior

The GitHub integration shows controls for draft pull requests, conclusion mirroring to pull request comments, and branch format.
Agent pull requests open as drafts by default.

#### FR-3: Bind a project repository

During project creation, a member can search repositories available through the GitHub integration and select one.
The picker groups repositories by installation and shows repositories already bound to another project as unavailable.
When GitHub is disconnected, the create-project flow explains the missing connection and links to Integrations.
The binding supplies the remote repository that the Worker clones separately for each Agent Run.

#### FR-4: Resolve a missing or ambiguous repository

A Run without one usable repository binding asks for a choice in its panel.
The Worker cannot start a Harness or permit a Code job write until the Run has one repository and its own safe CWD.
The Run never uses the Plane deployment checkout or the Worker's incidental current directory.

### 2. Harness configuration and mentions

This feature realizes UJ-1 and UJ-2.

#### FR-5: Configure four Harnesses

Integrations shows Claude Code, Codex CLI, Grok CLI, and Omp.
Each Harness has a detail page with an enable switch, connection control, name, unique workspace handle, instructions, and model selection.
The page distinguishes not connected, connecting, connected, and connection failed states and gives an actionable error.

#### FR-6: Verify a Harness and choose a model

Connecting a Harness verifies that the Worker can use it and obtains the models it reports.
The connection check records which interaction actions that Harness can perform, including continued conversation, progress reporting, cancellation, permission requests, and delivery during an active turn.
Model selection is available only after a successful connection.
The selected model persists for that workspace Agent.
A failed authentication attempt produces a visible error and can be retried.

#### FR-7: Mention an Agent

The existing work-item comment editor lists people and Agents when a member types @.
An Agent row shows its connection state.
An Agent that is not connected remains visible but cannot be selected for a new Run.
Any member who can comment on the work item can mention a connected Agent.

### 3. Agent Run and activity

This feature realizes UJ-2 through UJ-4.

#### FR-8: Create a Run from a mention

Each new comment that mentions a connected Agent creates a separate Agent Run and card.
The card shows the requester, original request, Agent, Run kind, state, elapsed time, and Open run action.
A later mention in another comment creates another Run, even on the same work item.

#### FR-9: Show a durable timeline

The Run panel shows the full ordered history of prompts, thoughts, actions, results, elicitation, permission decisions, errors, and pull request details.
Thoughts and tool actions may start collapsed but remain available after the Run concludes.
The panel shows the Run's plan and message queue when they exist.
Members can resize the panel; width and collapse choices persist per member.

#### FR-10: Keep work-item Activity concise

The work-item Activity feed shows the Run card and conclusion.
Intermediate thoughts, tool calls, and tool results stay in the Run panel.
The Run card links to a draft pull request when the Code job produces one.

#### FR-11: Show state and progress

The card and panel distinguish waiting for pickup, in progress, awaiting a person, permission needed, completed, failed, stale, and stopped.
The panel shows current live state and elapsed time during work.
An authentication failure creates an error in the panel and a concise failure conclusion on the work item.

### 4. Conversation, steering, and permission

This feature realizes UJ-2 through UJ-4.

#### FR-12: Continue a Run in its panel

The Run panel accepts follow-up messages in the same session.
While the Agent is working, new messages enter a visible queue and are delivered between steps.
Send now uses that Harness's supported control path.
If the Harness accepts input during an active turn, the Worker sends the selected message into that turn.
Otherwise, the Worker cancels the active turn, waits for cancellation to settle, and sends the selected message as the next turn in the same Run.
The panel shows when cancellation or delivery is pending and never marks a message delivered before the Harness accepts it.

#### FR-13: Escalate to a Code job

A request to implement or fix in the Run panel changes that Run from Q&A to a Code job.
The Run keeps its existing card, timeline, and conversation.
A new Agent mention in a work-item comment never appends to that Run.

#### FR-14: Request and record permission

Before the first Code job write, and again for a network or path escalation, the Run presents the proposed command, scope, and risk.
The member can allow once, allow for this Run, or deny.
The decision, person, and time remain visible in the durable timeline.
The Worker cannot perform the proposed write or escalation before a sufficient grant.

#### FR-15: Stop and resume

Any member who can comment on the work item can stop an active Run after confirmation.
Stopping interrupts the current action, clears queued messages, and retains the Run clone, sandbox, and Worktree.
The panel records who stopped the Run and accepts a reply to continue the same session.
The Worker must preserve the Run's conversation when a Harness needs a new process to continue it.

### 5. Local execution and code delivery

This feature realizes UJ-2 through UJ-4.

#### FR-16: Execute read-only Q&A

At pickup, the Worker clones the bound repository into a new CWD used only by this Run.
Q&A uses that Run clone as the Harness working directory and cannot write to it.
Two mentions on the same work item produce separate Run clones and separate CWDs.
Q&A does not create a Worktree, branch, or pull request.

#### FR-17: Execute an isolated Code job

A Code job uses an isolated Worktree and named Agent branch inside its own Run clone.
Later messages in that Run read the Worktree state.
The Agent cannot merge to the default branch.
The Worker retains the Run clone and Worktree when the Run stops.

#### FR-18: Deliver a draft pull request

When a Code job completes, the Run links to a draft GitHub pull request with branch and change summary.
A human reviews and merges the pull request.
The Run shows a clear failure if pull request creation fails.

#### FR-19: Handle capacity and stale work

The Worker supports concurrent Agent Runs.
When Code job capacity is full, the new Code job remains visible in a waiting state until a slot is available and does not start another container.
If the Worker stops updating a Run while Plane remains available, the Run becomes stale.
The panel offers Retry pickup and Mark failed for a stale Run.

### 6. Context delivery

This feature realizes UJ-2 through UJ-4.
It lets the Harness know exactly which Plane work item and conversation caused the Run.

#### FR-20: Anchor context to the Trigger comment

When an Agent mention creates a Run, Plane records the workspace ID, project ID, work-item ID, Agent ID, Trigger comment ID, and requester.
The Worker resolves those IDs through Plane before invoking the Harness; it does not infer context from the browser's current page, a last-used project, or its own CWD.
The Context snapshot and Run clone must refer to the same bound project repository.

#### FR-21: Include work-item and conversation content

The first prompt identifies the workspace, project, repository, work item identifier and link, current title, description, status, and other visible work-item fields relevant to the request.
It includes the Trigger comment as the current request, with its author and time.
It includes earlier comments on that work item in chronological order, with author, time, and stable comment ID.
Earlier Agent conclusion comments can appear as work-item comments; tool traces and private panel messages from other Runs do not become this Run's conversation.
For example, a mention on PLAN-214 must identify PLAN-214 and its project and must not import comments from another work item.

#### FR-22: Keep same-Run context current

Panel follow-ups keep the same Agent Run, Run clone, and conversation.
The Agent receives each new panel message with the prior messages and decisions from that Run.
When work-item content or comments changed since the previous turn, the Worker supplies the relevant update without silently switching the Run to another work item.
After a Worker or Harness restart, the Run can reconstruct its context from durable Plane records and continue in the same Run clone.
The user-facing Run identity does not depend on one Harness process or one vendor session ID.

#### FR-23: Make context limits and trust explicit

The work-item identity, current request, and enough issue content to understand the task remain available even when conversation history exceeds the Harness context budget.
If earlier comments are omitted, the Agent receives an omission count and a way to retrieve the full authorized work-item history.
Work-item descriptions, comments, titles, and other member-authored fields are treated as task data, not higher-priority instructions.
The Worker cannot include comments from a different work item or a workspace the requester cannot access.

## Cross-cutting requirements

- **Safety:** A Run cannot execute in the Plane deployment checkout, a shared Mirror, or an unbound repository.
- **Safety:** Q&A cannot write to the Run clone, and a Code job cannot write before a sufficient permission grant.
- **Audit:** Run thoughts, actions, results, errors, and permission decisions remain available after completion.
- **Access:** Comment permission governs who can mention an Agent or stop a Run.
- **Availability:** Failed Harness connection or CLI authentication must produce a visible error instead of an indefinitely active Run.
- **Interaction:** Each Harness must support the Run's conversation, progress, permission, cancellation, and recovery behavior through its own verified control path; Plane must not claim support for an action the connected Harness cannot perform.
- **Accessibility:** New controls, dialogs, status labels, queue actions, and panel interactions support keyboard operation and readable status text.
- **UI fidelity:** Production UI follows the design handoff's semantic tokens, components, layout, and interaction states.

## V1 scope and non-goals

V1 includes the complete design handoff: four Harnesses, GitHub connection, repository selection during project creation, Run cards and panels, follow-up conversation, queue and steering, permission decisions, local execution, and draft pull requests.
It includes the Plane CE and local Worker changes required for those behaviors.

V1 excludes Plane Enterprise or paid Agents code, an in-app LLM, a public Worker webhook, an Agent merge to the default branch, and use of the Plane deployment checkout as an Agent workspace.
The design handoff does not define the transport for each Harness or how it reports its models.
Architecture must resolve those mechanisms per Harness while preserving the product behavior here.
ACP is not part of this architecture direction, as decided by the product owner on 2026-09-27.

## Success criteria

- **SC-1:** A member can connect and select each of the four Harnesses, bind a project repository, and mention a connected Agent on a work item.
- **SC-2:** A Q&A Run answers from its own fresh Run clone without changing it; the member can inspect its complete timeline and ask a follow-up in the same panel.
- **SC-3:** An in-panel request to change code obtains permission before a write and ends with a reviewable draft pull request.
- **SC-4:** Stop, queued messages, capacity waiting, stale recovery, authentication failure, and missing repository states behave as described above.
- **SC-5:** A tagged Agent can identify the exact project, work item, issue content, Trigger comment, and prior comments; two Runs on one work item receive separate CWDs without mixing their private conversations.
- **Counter-metric:** Faster Agent output does not justify bypassing permission, repository binding, or human merge.

## Architecture inputs

- Define the available branch formats and preserve draft pull requests as the default.
- Define how each Harness connects and reports its available models.
- Define how the local Worker keeps permission decisions, queued messages, and Run history durable across interruption and recovery.
- Define the prompt envelope and authorized older-comment retrieval using the Context snapshot contract in FR-20 through FR-23.

## Open questions

None block architecture.
