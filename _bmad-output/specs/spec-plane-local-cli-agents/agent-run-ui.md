# Agent Run UI

Supports CAP-1, CAP-2, CAP-7.

## Mechanism (Plane nouns)

`@mention` in a work-item comment creates an **Agent Run**.

Activity types: `prompt`, `thought`, `action` (tool + args + optional result), `response`, `elicitation`, `error`.

States: `created` → `in_progress` → `awaiting` / `completed` / `stopping` → `stopped` / `failed` / `stale`.

`stale`: no update for 5 minutes.

Reply on the thread continues the **same** run.

Trigger is **mention**, not assign-to-bot. v1 bots: `@Claude`, `@Codex` only. Anyone who can comment may mention.

## Display

Linear-shaped **card on the work item** (bot, status, elapsed). Click opens a **panel** on the same issue — not a separate site, not a dump into the work-item Activity log.

**Intentional fork of Plane paid ephemeral:** thought/action rows **stay** in the panel after the run completes so the team can audit tools and results. Plane paid docs replace ephemeral rows; we do not.

Comments receive only `response`, `elicitation`, and `error` (the conclusion).

## Stop

User Stop from Plane: halt immediately (no further tools), kill process/Docker, keep worktree, record confirmation, state `stopped`. Who may Stop is an open question in SPEC.md.
