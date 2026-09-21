# Failure modes (v1)

| Failure | Required behavior |
|---|---|
| Wrong repo | No CLI / no Docker writes until project has one remote + stored `cwd`. Never deploy folder or worker process cwd. |
| CLI logged out | Preflight; `failed` + error comment; no hanging container. |
| Docker would OOM Plane | Refuse additional code jobs at capacity; Q&A without Docker still allowed. |
| Worker process down, Plane up | Run becomes `stale` after 5 minutes. |
| Mini / Plane down | Web unreachable; no separate "Mini asleep" state. |
| User Stop | Kill process/Docker immediately; keep worktree; `stopped`. |
| Mirror missing | `git clone` then answer. |
| Mirror dirty (uncommitted) | `git reset` then `git pull`, then answer. Mirror is not a place of record. |
| In-progress worktree Q&A | Read that worktree, not GitHub `main`. |
| Agent about to merge default branch | Out of scope; draft PR only. |
| Agent writing into Plane deploy folder | Forbidden. |
