---
review: rubric
target: ../ARCHITECTURE-SPINE.md
status: partial
created: 2026-09-27
---

# Rubric Review — Architecture Spine

## Verdict

PARTIAL.
The spine has the right main shape: Plane owns the control plane, the Worker owns execution, each mention gets a fresh clone, Run state is durable, and permissions are Plane grants enforced by sandbox boundaries.
It is not ready for downstream epic split yet because several PRD architecture inputs are deferred or left as general intent.
Those gaps can let API, Worker, web, and Harness-driver epics choose incompatible contracts.

No critical gap found.
High gaps are listed below.

## Evidence Reviewed

- `plans/2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md`
- `plans/2026-09-27-local-cli-agents-prd/prd.md`
- `.agents/skills/bmad-architecture/references/reviewer-gate.md`
- `rg --files -g 'lint_spine.py' /Users/dale/orca/workspaces/plane/main /Users/dale/.agents/skills /Users/dale/.codex/skills` found no deterministic lint script.

## High Findings

### HIGH-1 — Per-Harness connection and model-reporting mechanisms are not resolved

The PRD says the design handoff does not define each Harness transport or model reporting, and that architecture must resolve those mechanisms per Harness.
It also requires each Harness connection check to record supported interaction actions, including continued conversation, progress, cancellation, permission requests, and delivery during an active turn.
See `prd.md:125`, `prd.md:127`, `prd.md:128`, `prd.md:274`, `prd.md:284`, `prd.md:285`, and `prd.md:300`.

The spine says each driver implements connection, capability check, model discovery, events, cancel, permission response, and shutdown where supported.
It does not define the verified interaction path for Claude Code, Codex CLI, Grok CLI, or Omp.
It then defers driver command flags and parser details to a future connection probe.
See `ARCHITECTURE-SPINE.md:69`, `ARCHITECTURE-SPINE.md:73`, `ARCHITECTURE-SPINE.md:77`, and `ARCHITECTURE-SPINE.md:179`.

This can make downstream epics incompatible.
The settings UI, Worker capability schema, and four driver implementations need the same contract for connection state, model discovery, event capture, mid-turn input, cancel, permission, and resume.
The spine should add one enforceable decision or a small table that names the v1 verified interaction method and minimum evidence for each Harness.
Parser internals can stay deferred, but the interaction contract cannot.

### HIGH-2 — Code job capacity waiting is not an enforceable architecture decision

The PRD makes capacity waiting a v1 correction and success criterion.
When Code job capacity is full, the Code job must stay visible in a waiting state and must not start another container.
See `prd.md:15`, `prd.md:64`, `prd.md:226`, `prd.md:228`, `prd.md:229`, and `prd.md:293`.

The spine covers Worker leases, stale recovery, durable events, and Docker code jobs.
It does not define the capacity owner, the capacity token or queue rule, the waiting state transition, or the invariant that a full Code-job pool must not refuse the Run or start another container.
See `ARCHITECTURE-SPINE.md:60`, `ARCHITECTURE-SPINE.md:64`, `ARCHITECTURE-SPINE.md:67`, `ARCHITECTURE-SPINE.md:127`, and `ARCHITECTURE-SPINE.md:158`.

This can make downstream Worker and API epics incompatible.
One unit could treat capacity as a Worker-local concern, another could model it as Run state, and another could fail fast.
Add an AD that makes Plane the durable owner of the waiting state and makes the Worker consume a bounded Code-job capacity slot before creating a code sandbox.

### HIGH-3 — Branch format and draft-pull-request behavior are deferred despite being shared product contracts

The PRD requires branch-format controls and draft pull requests by default.
It also lists available branch formats and the draft default as architecture inputs.
See `prd.md:97`, `prd.md:99`, `prd.md:100`, `prd.md:220`, `prd.md:222`, and `prd.md:299`.

The spine says pull request creation records the draft PR identity, but it does not require draft creation as the default.
It also defers GitHub branch format choices as configuration details.
See `ARCHITECTURE-SPINE.md:118`, `ARCHITECTURE-SPINE.md:124`, and `ARCHITECTURE-SPINE.md:181`.

This can make downstream settings UI, API configuration, Worker branch naming, and GitHub delivery epics incompatible.
The exact string template can be small, but the shared enum and default must be fixed in the spine.
At minimum, add an AD that says Agent pull requests are draft by default and branch format is selected from a Plane-owned finite set used by both UI and Worker.

## Architecture Dimension Check

| Dimension | Verdict | Evidence |
| --- | --- | --- |
| Design paradigm | PASS | Ports-and-adapters with Plane-owned control plane is named in frontmatter and explained in `ARCHITECTURE-SPINE.md:20` through `ARCHITECTURE-SPINE.md:25`. |
| Control and execution boundary | PASS | Plane API, PostgreSQL, Worker, drivers, GitHub, and local execution are split in `ARCHITECTURE-SPINE.md:22` through `ARCHITECTURE-SPINE.md:37`. |
| Run state and event ownership | PASS | AD-1 and AD-10 make Plane API the durable owner of Run state, commands, events, and browser cursors. |
| Run identity and context | PARTIAL | AD-2 fixes IDs, snapshot, deltas, omission count, and retrieval path, but the PRD prompt envelope input remains only partly resolved. |
| Worker ownership, lease, retry, stale recovery | PASS | AD-3 fences Worker mutations with lease generation and expiry. |
| Harness capabilities | PARTIAL | AD-4 defines the common driver shape, but does not resolve per-Harness verified interaction mechanisms. |
| Conversation, queue, Send now, Stop, resume | PASS | AD-5 and AD-6 fix message ordering, interrupt behavior, and Run identity across driver process restarts. |
| Repository isolation | PASS | AD-7 implements the accepted fresh clone per mention and excludes the Plane deployment checkout. |
| Permission and sandbox enforcement | PASS | AD-8 makes Plane grants necessary before writes or escalation and treats member content as task data. |
| GitHub and repository binding | PARTIAL | AD-9 assigns ownership, but branch formats and draft default are not fixed. |
| Local environment and operations | PARTIAL | Mac Mini, localhost Worker calls, Tailscale access, and no public Worker callback are stated, but capacity waiting lacks an AD. |
| UI activity and timeline | PASS | AD-10 keeps Activity concise and durable panel history available through event cursor reads. |
| Scope and non-goals | PASS | The spine does not introduce ACP, public Worker callbacks, remote execution, default-branch merge, shared Mirror, or Plane deployment checkout execution. |

## PRD Coverage Check

| PRD Area | Verdict | Notes |
| --- | --- | --- |
| FR-1 through FR-4, GitHub and repository setup | PARTIAL | Repository ownership and missing binding are covered, but branch format is deferred. |
| FR-5 through FR-7, Harness configuration and mentions | PARTIAL | Four Harnesses and capability checks are named, but per-Harness connection and model-reporting mechanisms are not resolved. |
| FR-8 through FR-15, Run activity, conversation, steering, and permission | PASS | The Run card, panel, timeline, queue, Send now, Stop, resume, permission, and state durability are governed by AD-1 through AD-6 and AD-8. |
| FR-16 through FR-18, local execution and pull request delivery | PARTIAL | Fresh clone, read-only Q&A, Worktree, sandbox, and human merge are covered, but draft-default pull request behavior should be explicit. |
| FR-19, capacity and stale work | PARTIAL | Stale work is covered by AD-3, but capacity waiting is not fixed. |
| FR-20 through FR-23, context delivery | PARTIAL | Anchored IDs, same-Run deltas, omission count, retrieval path, and trust boundary are covered, but the prompt envelope remains too implicit for an API and Worker split. |
| Cross-cutting safety, audit, access, interaction, accessibility, UI fidelity | PARTIAL | Safety, audit, and interaction are mostly covered; comment-permission access, accessibility, and UI fidelity are not architecture blockers if the design handoff owns them, but they should be cited in epics. |

## Deferred Items Check

`ARCHITECTURE-SPINE.md:177` is acceptable if AD-1 through AD-3 own the state and event invariants.
`ARCHITECTURE-SPINE.md:178` is acceptable because poll interval and retention limits can be operational settings.
`ARCHITECTURE-SPINE.md:179` is too broad because per-Harness interaction mechanisms are an accepted architecture input.
`ARCHITECTURE-SPINE.md:180` is acceptable and stays outside v1.
`ARCHITECTURE-SPINE.md:181` is too broad because branch format and draft pull request default are shared UI/API/Worker contracts.

## Enforceability Check

AD-1, AD-2, AD-3, AD-5, AD-6, AD-7, AD-8, and AD-10 have clear rules that can be tested by API, Worker, or UI behavior.
AD-4 is not fully enforceable until the v1 driver capability matrix states what each Harness must prove at connection time.
AD-9 is not fully enforceable until branch format and draft default are fixed as Plane-owned configuration.

## Gaps

- The deterministic `lint_spine.py` check from the reviewer gate could not run because no script exists at the installed skill path or nearby searched roots.
- This review did not verify named CLI technology versions or current CLI capabilities on the web.
- The review checked the PRD and spine only, not the design handoff screens.

## Stop Condition

Stop downstream epic generation until HIGH-1, HIGH-2, and HIGH-3 are resolved in the spine or explicitly moved to accepted open questions with owners and revisit conditions.
