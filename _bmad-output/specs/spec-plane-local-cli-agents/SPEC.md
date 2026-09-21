---
id: SPEC-plane-local-cli-agents
companions:
  - job-kinds.md
  - agent-run-ui.md
  - runner.md
  - diagrams.md
  - brownfield.md
  - failure-modes.md
sources:
  - ../../brainstorming/brainstorm-plane-local-cli-agents-2026-09-06/brainstorm-intent.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Self-hosted Plane @agent (local Claude Code / Codex)

## Why

**Pain + vision.** The team already runs Plane Community Edition, Claude Code, and Codex on one Mac Mini and reaches Plane over Tailscale. They need to hand a work item to those local CLIs from Plane (`@Claude` / `@Codex`) and see what the agent did, without a Plane paid Agents subscription, without an in-app LLM, and without sending work to a cloud coding agent. CE has no Agent Run product; the paid Plane/Linear model exists only as a pattern to follow (nouns and split of live trace vs comment), not as code to clone.

## Capabilities

- **CAP-1**
  - **intent:** A workspace member who can comment on a work item can @mention `@Claude` or `@Codex` in that comment and start an Agent Run.
  - **success:** Those two bots appear in the mention picker; a mention creates an Agent Run tied to that work item and comment; other bots (including Amp) are absent in v1.
- **CAP-2**
  - **intent:** After handoff, the team can see the Agent Run status and the full thought/tool/result timeline without leaving the work item, and can continue the same run by replying.
  - **success:** A card on the work item opens a panel with the complete durable activity history; conclusion types also appear as comments; tool calls never appear in the work-item Activity log. See `agent-run-ui.md`.
- **CAP-3**
  - **intent:** A mention is Q&A by default: the agent answers from the work item and, when the question is about code, from a read-only snapshot of the bound repo — and does not open a PR.
  - **success:** A question-only mention produces panel activity plus a conclusion comment, no branch, no draft PR. See `job-kinds.md`.
- **CAP-4**
  - **intent:** On the same Agent Run, the user can ask to implement or fix; the run becomes a code job and the timeline continues.
  - **success:** No second card/run is created; later Q&A on that run reads the code job's worktree, not GitHub `main`. See `job-kinds.md`.
- **CAP-5**
  - **intent:** A code job delivers reviewable code as a draft pull request on the bound GitHub repository; a human merges.
  - **success:** A draft PR exists on `agent/<issue-id>` (or the resumed same branch); the agent never merges to the default branch.
- **CAP-6**
  - **intent:** The agent does not write code until a single git remote is bound for that job.
  - **success:** Binding is project map, else comment override, else elicitation on the same run; 0 or >1 candidates block docker writes. Never Mini cwd or last-used repo. See `runner.md`.
- **CAP-7**
  - **intent:** A user can stop an in-progress Agent Run from Plane.
  - **success:** Stop transitions the run through stopping → stopped; the CLI/container is killed; the worktree is kept; a confirmation activity is recorded. Who may Stop is an open question.
- **CAP-8**
  - **intent:** More than one Agent Run can be in progress at once; the Mini must not boot additional Docker code jobs when it is at capacity.
  - **success:** A code job that would exceed capacity is refused with a visible failed/error on that run, not queued into another container. Exact N / mem_limit is an open question.
- **CAP-9**
  - **intent:** The Mini worker notices mentions and drives Agent Runs without exposing a public webhook.
  - **success:** Pickup works via the local Plane API on the Mini; Tailscale is not required for worker↔API; humans still use Tailscale to reach Plane. See `runner.md`.

## Constraints

- v1 is both Plane CE (mention, Agent Run, card+panel, comments) and the Mini worker; not Mini-first, not UI-only.
- No Plane paid Agents subscription; no native in-app LLM; do not clone Plane EE/OAuth-app product as the implementation.
- Plane, Claude Code, Codex, and the worker share one Mac Mini. One doorbell address. Humans reach Plane only over Tailscale.
- Agent Run uses Plane paid nouns and states: prompt, thought, action, response, elicitation, error; created / in_progress / awaiting / completed / stopping / stopped / failed / stale (5 minutes without update).
- Thought/action history is durable in the Agent Run UI (intentional fork of Plane's ephemeral replace). Comments hold response / elicitation / error only.
- Never use the Plane deploy checkout as an agent workspace.
- Code writes run in Docker with a named branch `agent/<issue-id>` and a worktree. Do not pull/rebase origin while that worktree is dirty/in progress.
- Sandbox types are pluggable; v1 implements Docker only for code writes. Q&A does not use Docker. Read-code Q&A uses the CLI OS sandbox (Seatbelt / Codex workspace-write).
- Git clone/pull uses SSH keys already on the Mini. Mirror root and worker settings are env vars, not Plane UI.
- CLI auth failure fails the run immediately (error activity + comment), no hanging container.
- Plane web reachable ⇒ Mini is up. Plane up and worker down ⇒ stale after 5 minutes. No separate worker-offline heartbeat.

## Non-goals

- Amp (or any third bot) in v1
- Sandbox providers other than Docker in v1
- Public webhook, tunnel, or Funnel for the worker
- Cloning Plane Enterprise / Cloud Agents as the codebase
- Agent merging to the default branch
- Using the live Plane deploy folder as a git workspace
- Wiping thought/tool history when the run completes
- Linear-style human-assignee + agent-delegate as the primary trigger (mention is the trigger)

## Success signal

A teammate on Tailscale comments `@Claude` on a work item, sees an Agent Run card within the stale window, opens the panel and can read thoughts and tool calls. A question-only mention ends in a comment and no PR. Saying implement on that same run yields a draft GitHub PR on the mapped repo; Stop kills the container and leaves the worktree. A second mention while Docker is at capacity is refused visibly.

## Assumptions

- Git hosting is GitHub.
- Plane CE can present bot users in the mention picker without adopting Plane EE's OAuth-app installation product.
- Claude Code and Codex CLIs are already installed on the Mini; the worker invokes them rather than embedding an LLM.

## Open Questions

- What is the hard cap N and per-container memory limit for Docker code jobs?
- Who is allowed to Stop a run (any commenter vs run starter vs project admin)?
- How does v1 decide issue-only Q&A vs read-code Q&A (when to clone/pull)?
- If mirror `pull --ff-only` cannot fast-forward, is the run failed (suggested) or answered from the stale tree?
- A second `@Claude` on a work item that already has an active Agent Run: resume that run vs refuse vs new run?
