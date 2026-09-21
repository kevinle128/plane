# Mini runner

Supports CAP-8, CAP-9, and execution constraints.

## Placement

Plane API, worker, Claude Code, and Codex share the Mac Mini. Worker talks to Plane on **localhost**. No public webhook, tunnel, or Funnel. Tailscale is human access to Plane only.

## Pickup

Worker **polls** the local Plane API for mentions / Agent Runs. CLI auth is preflighted before `in_progress`; failure → `failed` + error comment, no hanging container.

Plane web reachable ⇒ Mini is up. If Plane is up and the worker is not, the run goes **stale** after 5 minutes. No extra "worker offline" heartbeat.

## Sandbox registry

Pluggable by name. v1 ships **Docker** for code writes only. Q&A does not start Docker. Read-code Q&A uses CLI OS sandbox (Claude Seatbelt / Codex workspace-write) on the **mirror**, not on the deploy tree.

## Mirrors and git

- Env: e.g. `PLANE_AGENT_MIRRORS_ROOT` (default a directory next to the worker, not the Plane deploy path)
- Clone/pull with **SSH keys already on the Mini**; no git token in Plane
- Pull latest before Q&A that needs code; clone if the mirror is missing
- Fast-forward-only pull is the intended happy path; non-ff behavior is an open question

## Capacity

Concurrent Agent Runs allowed. Docker RAM is shared with the Plane stack. At capacity, **refuse** the new **code** job visibly — do not boot another container. Numeric N and mem_limit are open questions. Q&A without Docker does not count toward that Docker cap.
