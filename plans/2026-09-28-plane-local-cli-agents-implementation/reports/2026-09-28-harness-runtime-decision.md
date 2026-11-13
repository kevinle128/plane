# Harness runtime isolation decision

Status: proposed; no runtime write exception is enabled.

## Observed conflict

[AD-7](../../2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md#ad-7--each-mention-gets-one-fresh-repository-clone-adopted) denies all Q&A writes inside and outside the clone.
The installed CLI programs need local runtime state before they can execute a turn.
All checks used disposable files and stopped their owned process groups.

| CLI | Real check under the current OS boundary | Result |
| --- | --- | --- |
| Codex 0.157.1 | Ephemeral exec, no user config or rules, native read-only sandbox | Startup fails with `Operation not permitted` |
| Grok 1.0.41 | Single turn, native write tools excluded, permission mode `dontAsk`, no subagents | Session creation fails with `FS_PERMISSION_DENIED` |
| Omp 18.1.21 | JSON print, no session, read/grep/glob only, no extensions, skills, rules, LSP, or PTY | Startup fails with `SQLITE_READONLY` |

Codex was also checked with an exploratory writable temporary runtime directory.
The documented `sqlite_home` and `log_dir` settings moved its databases into that directory, but both exec and app-server still failed at startup.
These settings are described in the [official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
The test disabled shell snapshots, hooks, plugins, and multiple agents.
This test does not establish a working runtime exception.
The production profile still denies all writes.
The connection gates for these three Harnesses remain closed.

## Proposed contract

Permit disposable CLI runtime writes within an OS or container boundary owned by one Run and one turn.
Keep the clone, Worktree, credentials, and all other Host paths read-only for the Harness process.
Keep Plane as the authority for every protected source-file, network, and GitHub effect.
Use the existing Plane broker for those effects.

Prefer bounded private runtime storage, such as container tmpfs, over a shared writable Host cache.
Do not mount the Plane token, deployment checkout, Docker socket, or another Run.
Expose only the selected Harness authentication material through the smallest supported read-only route.
Stop the process tree and delete runtime state after each turn.
Recover from Plane's durable transcript; do not require a writable shared CLI session database.
Use one verified adapter per CLI version and fail connection checks when its behavior changes.

## Required evidence before connection

- A real authenticated turn completes under the final boundary.
- Writes to the clone, Worktree, Host, credentials, and another Run fail.
- Runtime storage, process count, memory, output, and execution time have enforced bounds.
- Tool escalation cannot bypass Plane grants.
- Follow-up, progress, interruption, and recovery pass for each Harness.
- Concurrent turns cannot share runtime state or credentials from another Harness.

## Decision needed

Accept the explicit disposable-runtime exception to AD-7, or retain the literal ban on every Q&A write and require another verified transport.
The exception changes an accepted security contract, so it needs the user's decision before implementation.
It does not reduce the requirement to deliver all four Harnesses.
