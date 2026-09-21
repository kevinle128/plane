# Job kinds and trees

Supports CAP-3, CAP-4, CAP-5, CAP-6.

## Default

A mention is **Q&A**. No named branch, no worktree, no draft PR.

Escalate to **code** only when the user asks to implement or fix **in that run's panel**. One timeline on that session. A new `@` comment is a different session, not an escalate.

## Trees (the tree of that run)

| Situation | Tree / `cwd` |
|---|---|
| Q&A (default, any question) | Claude/Codex **always** get a `cwd`: the project's stored clone path. Pull latest first. OS sandbox, **no writes** on that clone. Never the Plane deploy folder. |
| Same run already implementing | Docker **worktree** on `agent/<issue-id>` (as planned). Later Q&A on this run uses that worktree, not the mirror. |

There is no “ticket-only, no git” path: the CLI always has a repo `cwd` when the project is mapped.

## Mirror hygiene (Q&A clone)

- Purpose: **read only**. Agent must not commit or edit this tree.
- Before answering: `git pull` latest (clone first if missing).
- If pull fails because of uncommitted local changes: `git reset` then `git pull` (safe because this tree is not a place of record).

## Code job

- Docker sandbox
- Named branch `agent/<issue-id>` + worktree
- Draft PR on the bound GitHub remote
- Humans merge; agent never merges to the default branch
- No origin pull/rebase mid-worktree while work is in progress
- Stop kills the process/container and **keeps** the worktree

## Repo bind

Standing config: Plane **project → one git remote + local clone `cwd`**.

1. Use that map
2. Else **comment override**
3. Else **elicitation** on the same run

Without a `cwd`, do not start the CLI. Zero or more than one candidate: no Docker writes. Never the Plane deploy checkout; never the worker process cwd.
