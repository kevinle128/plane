# Job kinds and trees

Supports CAP-3, CAP-4, CAP-5, CAP-6.

## Default

A mention is **Q&A**. No named branch, no worktree, no draft PR.

Escalate to **code** only when the user asks to implement or fix, **on the same Agent Run**. One timeline. No second card.

## Trees (the tree of that run)

| Situation | Tree the agent reads/writes |
|---|---|
| Q&A, no code job yet | Dedicated **mirror** of the bound repo: clone if missing, else pull latest from GitHub before answering. Read-only (CLI OS sandbox). Path under env-configured `mirrors` root next to the worker. **Never** the Plane deploy checkout, **never** Mini host cwd. |
| Same run already implementing | That job's **Docker worktree** on `agent/<issue-id>`, including in-progress edits. Do not answer from GitHub `main` or the Mini host folder. |

Host Mini checkouts are not a Q&A source.

## Code job

- Docker sandbox
- Named branch `agent/<issue-id>` + worktree
- Draft PR on the bound GitHub remote
- Humans merge; agent never merges to the default branch
- No origin pull/rebase mid-worktree while work is in progress
- Stop kills the process/container and **keeps** the worktree

## Repo bind (before any code write)

1. Plane **project → one git remote** (standing config)
2. Else **comment override**
3. Else **elicitation** on the same run

Zero or more than one candidate: do not start Docker writes. Never default to Mini cwd or last-used repo.
