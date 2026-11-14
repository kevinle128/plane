# Research: how Multica integrates Claude Code and Codex, and what we can simplify

Date: 2026-11-14 (Asia/Saigon). Author: researcher agent. Status: research only, no code changed.

## Sources and method

- Multica code: local clone `/Users/dale/Desktop/workspace/opensources/multica` at commit `43b0571f99` (2026-09-29). All Multica `file:line` citations below refer to this clone. Paths are relative to the clone root.
- Cross-check: a shallow clone of upstream HEAD `dfcc633dda2e` (2026-11-14) showed the same behavior for every point below. Line numbers differ by up to about 120 lines in `claude.go` and `daemon.go`; the behavior is the same.
- Our side: `plan.md`, `architecture-contracts.md`, phases 2-7, `ARCHITECTURE-SPINE.md` AD-4..AD-8, `epics.md`, and `apps/agent-worker/` in this worktree (HEAD `c5278d9548`).
- Not used: GitNexus query tools (not available in this session) and DeepWiki. All claims come from direct file reads.

## Bottom line

Multica is much simpler because it makes one choice that we do not: **the isolation boundary is the OS user (or VM/container) that runs the daemon, not the agent process.** Multica runs Claude with `--permission-mode bypassPermissions`, runs Codex with `sandbox_mode = "danger-full-access"`, and auto-accepts every approval. The agent itself clones (through a helper command), commits, pushes and runs `gh pr create` with the host's credentials. There is no human approval step.

Our spec (AD-4, AD-5, AD-7, AD-8, AD-11, Epic 3) requires much more than this: read-only Q&A, per-effect permission cards, a Docker sandbox for Code jobs, Worker-owned push, Plane-owned pull requests and no token near the agent. Most of our extra cost comes from the spec, not from the implementation. So the large savings need spec decisions from the user. Some smaller savings need no spec change.

## 1. Multica facts (Claude Code and Codex)

### 1.1 Daemon and server

- **Authentication.** `multica login` creates a 90-day personal access token (`mul_`) (`CLI_AND_DAEMON.md:78-92`). The daemon sends it as `Authorization: Bearer` (`server/internal/daemon/client.go:813`). A test comment says production daemon traffic uses `mul_` PATs and daemon-token (`mdt_`) minting "isn't wired up yet" (`server/internal/middleware/daemon_auth_test.go:56`). Each task gets a separate task-scoped token `mat_` in `MULTICA_TOKEN`, bound to agent and task (`server/internal/daemon/daemon.go:167-190`, `apps/docs/content/docs/security-model.mdx:40`).
- **Registration.** The daemon posts `/api/daemon/register` with `workspace_id`, `daemon_id`, device name, CLI version and one runtime entry per detected CLI (`name`, `type`, `version`, `status: online`) (`client.go:1085`, `daemon.go:2976`).
- **CLI discovery.** `exec.LookPath`, with a fallback to the user's login shell PATH. Discovery has "no version detection and no minimum-version gate" (`server/internal/daemon/agents_probe.go:82`). Registration then runs `--version` and checks a minimum (`daemon.go:1201`). The minimum is `claude` 2.0.0 and `codex` 0.100.0 (`server/pkg/agent/version.go:20-21`).
- **Getting tasks.** WebSocket wake signal plus a catch-up poll every 30 s. The daemon claims tasks in one batch for all its runtimes (`CLI_AND_DAEMON.md:251-257, 265`; `client.go:306` with `daemon_id`, `runtime_ids`, `max_tasks`). Claim SQL uses `FOR UPDATE SKIP LOCKED` (`server/pkg/db/queries/agent.sql:808, 912, 959`). Heartbeat every 15 s (`CLI_AND_DAEMON.md:267`). A `prepare-lease` call exists (`client.go:437`); I did not verify its fencing rules, so I do not claim it equals our `lease_generation`.
- **Streaming and results.** The daemon batches parsed events and posts them to `/api/daemon/tasks/{id}/messages` with a sequence number (`client.go:616`). Results go to `/complete`, `/fail`, `/usage`; the session ID goes to `/session` (`client.go:703`).

### 1.2 Exact invocation

**Claude Code** (`server/pkg/agent/claude.go:1078-1135`, `buildClaudeArgs`):

```
claude -p --output-format stream-json --input-format stream-json --verbose \
  --permission-mode bypassPermissions --disallowedTools AskUserQuestion \
  [--strict-mcp-config --mcp-config <file>] [--model M] [--effort E] [--max-turns N] \
  [--resume <session_id>] [custom args] [--settings <daemon file>]
```

- The prompt goes on stdin as stream-json; stdin stays open for later input.
- The system prompt is not passed with `--append-system-prompt`. The daemon writes a per-task `CLAUDE.md` in the workdir instead (`claude.go:1112`).
- Users cannot override `-p`, `--output-format`, `--input-format`, `--permission-mode`, `--mcp-config` or `--effort` through custom args (`claude.go:1063` `claudeBlockedArgs`).
- **Environment:** the full daemon `os.Environ()`, minus `MULTICA_*` and five internal Claude markers (`CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_EXECPATH`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_SSE_PORT`) (`claude.go:1283-1330`). The daemon then adds `MULTICA_TOKEN`, server URL, workspace, agent and task IDs, and a per-task `TMPDIR` (`daemon.go:178-195`).
- The daemon refuses to start under root unless `IS_SANDBOX=1` (`claude.go:1245`).
- **Working directory:** `~/multica_workspaces/<workspace>/<task>/workdir`, or a user-chosen local directory or worktree (`server/internal/daemon/execenv/execenv.go:76-90`).

**Codex** (`server/pkg/agent/codex.go:364`): `codex app-server --listen stdio://` (JSON-RPC). Multica does **not** use `codex exec --json`.

- `thread/start` sends `cwd`, `model`, and `approvalPolicy: nil`, `sandbox: nil`, `developerInstructions: nil` (`codex.go:2068-2087`). Instructions come from a per-task `AGENTS.md` in the workdir.
- The sandbox mode comes from a daemon-managed block in a per-task `$CODEX_HOME/config.toml` (`execenv/codex_sandbox.go:356`).
- On a follow-up, the daemon calls `thread/resume`. If that fails, it falls back to `thread/start` (`codex.go:1558`).

### 1.3 Isolation and safety

- **Claude:** `bypassPermissions`. No Claude sandbox settings, no permission deny rules. The only `--settings` file disables inherited skills (`claude.go:1121-1134`).
- **Codex:** in practice `danger-full-access` on every OS. The macOS `workspace-write` branch never runs, because `CodexDarwinNetworkAccessFixedVersion = ""` (`execenv/codex_sandbox.go:34, 301`). The reason is that macOS Seatbelt ignores `network_access` in `workspace-write` (openai/codex#10390). On Linux this is a product decision (`codex_sandbox.go:64-131`). Only a Windows user who opts in to the native sandbox keeps `workspace-write`.
- **Approvals:** every `commandExecution`, `fileChange` and `permissions` approval request is auto-accepted, and MCP elicitations too (`codex.go:2928-2945`).
- **Documented model:** "By default a run executes with the full permissions of the operating-system user running the daemon … Multica makes no filesystem-sandbox guarantee." The docs recommend a dedicated Unix user, a container or a VM (`apps/docs/content/docs/security-model.mdx:10-30`). The agent tool's own sandbox and approvals are "not a boundary" (`:42-45`).
- **What Multica does isolate (convenience, not security):** a per-run workdir, a per-run `CODEX_HOME`, and a run-scoped API token (`security-model.mdx:34-40`).
- **Secrets:** nothing is kept out. Runs inherit the real `HOME`, so `gh`, `aws` and `kubectl` work (`security-model.mdx:44`).

### 1.4 Sessions, follow-up, mid-task input, stop

- **Resume.** The server gives the next task on the same issue `prior_session_id` and `prior_work_dir` (`server/internal/daemon/types.go:111-113`). Claude gets `--resume <id>` (`claude.go:1117`), and Codex gets `thread/resume`. If the CLI rejects the resume, the daemon drops the ID and retries with a fresh session.
- **Mid-task input ("supplements").** The daemon claims a supplement every 5 s or on a WebSocket hint (`server/internal/daemon/task_supplement.go:19`; `client.go:448`).
  - Claude: the code comment says "Claude has no conditional, current-turn-only user input request". So Multica registers SDK hooks (`UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `Stop`) and injects the text as `additionalContext` at the next hook boundary (`server/pkg/agent/claude_supplement.go:20-28`).
  - Codex: `turn/steer` (`codex.go:1954`).
- **Stop.** The daemon polls task status every 5 s, and also reacts to a WebSocket reconcile signal (`daemon.go:742, 5671`). On a terminal status, Codex gets `turn/interrupt` (`codex.go:2655`). Claude gets EOF on stdin, then SIGTERM, then SIGKILL on the whole process group (`claude.go:216`).

### 1.5 Connection and health check

- "Available" means: found on PATH, `--version` parses, and the version is at or above the minimum. There is no login check and no test prompt (`agents_probe.go:82`; `daemon.go:1201`). An auth failure shows up only when a task fails.
- **Models.**
  - Claude: a one-shot `claude --print --verbose --input-format stream-json --output-format stream-json --strict-mcp-config` with a `control_request` `{subtype: list_models}` on stdin (`server/pkg/agent/claude_models.go:69, 281`). If that fails, Multica uses a static list.
  - Codex: `codex debug models`, then `codex debug models --bundled`, then a static list (`server/pkg/agent/thinking.go:309-345, 387`).

### 1.6 Git and PR flow

- The daemon keeps a bare clone cache (`git clone --bare`) using the daemon's environment, so host credential helpers such as `gh` work. It sets `GIT_TERMINAL_PROMPT=0` (`server/internal/daemon/repocache/cache.go:51, 596`).
- The **agent** runs `multica repo checkout <url>`. That command creates a `git worktree add -b <branch>` from the cache (`server/cmd/multica/cmd_repo.go:53`; `cache.go:1478`; `execenv/execenv.go:1-3`).
- The **agent** commits, pushes and opens the PR with `gh pr create --base <branch>`. The platform does not create PRs (`execenv/runtime_config_sections.go:421-454`). Credentials are whatever the daemon user has.

### 1.7 Approvals and human in the loop

There are none. Approvals are auto-accepted (1.3). `AskUserQuestion` is disabled, and the agent is told to ask in an issue comment (`claude.go:1085-1091`).

### 1.8 Scale

- Up to 20 concurrent tasks per daemon by default (`CLI_AND_DAEMON.md:276`), enforced by a slot semaphore (`daemon.go:5349`).
- Server claim uses `SKIP LOCKED` batches.
- There is no container slot pool, but there is a workspace GC (TTL table, `CLI_AND_DAEMON.md:281-292`).

## 2. Comparison table

| Topic            | Our design (plan + Worker code)                                                                                                                                                                                                                          | Multica                                                                                                  |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Daemon auth      | One `AgentWorker` token (SHA-256 at rest, 0600 file), Bearer, own throttle-free API (phase-02 Key decisions)                                                                                                                                             | User's 90-day PAT as Bearer; per-task `mat_` token for the agent                                         |
| Task pickup      | Worker polls `runs/claim/` every 2 s (`config.py:21`); lease with generation, 409 fencing (contracts §4)                                                                                                                                                 | WebSocket wake + 30 s poll, batch claim, heartbeat 15 s                                                  |
| Event stream     | Batched events with `source_key`, Plane assigns `seq` (phase-03 data flow 6)                                                                                                                                                                             | Batched `/messages` with seq; same shape                                                                 |
| Claude flags     | `-p` stream-json in/out, `--include-partial-messages --replay-user-messages --safe-mode --restricted --strict-mcp-config --disable-slash-commands --setting-sources "" --permission-prompt-tool stdio --settings <boundary>` (`drivers/claude.py:64-81`) | `-p` stream-json in/out, `--permission-mode bypassPermissions --disallowedTools AskUserQuestion`         |
| Codex transport  | `app-server` JSON-RPC, `model/list`, `turn/steer`, approvals mapped to deny in Q&A (phase-06)                                                                                                                                                            | `app-server --listen stdio://`, approvals auto-accepted                                                  |
| Environment      | Allowlist of 13 names (`drivers/claude.py:85-100`)                                                                                                                                                                                                       | Full daemon env minus `MULTICA_*` and 5 markers                                                          |
| Context delivery | Context envelope (`prompt.py`) + Plane MCP tools (phase-03/04)                                                                                                                                                                                           | Per-task `CLAUDE.md` / `AGENTS.md` in the workdir; the agent uses the `multica` CLI with `MULTICA_TOKEN` |
| Q&A isolation    | Claude: built-in sandbox, writes denied, `denyRead` of Run root, token and credential stores; `Edit` deny; hooks off (`drivers/claude_boundary.py:53-85`, Q16). Codex/Grok/Omp: outer macOS profile + disposable runtime dir (Q1)                        | None. Boundary = daemon OS user. Codex `danger-full-access`, Claude `bypassPermissions`                  |
| Code isolation   | Docker per Code Run, network none, only the Worktree writable, effects through MCP tools, file publish by Worker (phase-07, AD-8)                                                                                                                        | Same as Q&A: full user rights in a per-task worktree                                                     |
| Workspace        | Fresh full clone per Run at `<run_root>/<run_id>/clone`; Worktree for Code; inode check on resume (AD-7, phase-05)                                                                                                                                       | Bare cache + `git worktree add -b` per task, made by the agent on demand                                 |
| Connection check | 7 checks: auth (`claude auth status`), model report, follow-up resume, progress, interruption, permission, recovery; about 33 s, 4 sessions (`drivers/base.py:22-30`, `drivers/claude.py:397-626`)                                                       | PATH + `--version` + minimum version. No login check, no test prompt                                     |
| Models           | `initialize` control request in a session (`drivers/claude.py:466-483`)                                                                                                                                                                                  | `list_models` control request (Claude), `codex debug models` (Codex), static fallback                    |
| Follow-up        | Same Run, same clone, resume native session or rebuild from snapshot (phase-04)                                                                                                                                                                          | Same issue, `prior_session_id` + `prior_work_dir`, fresh session if resume is rejected                   |
| Mid-turn input   | Queue states `queued/dispatching/accepted/...`; native injection if `midturn_input`, else cancel-then-next-turn (phase-05, AD-5)                                                                                                                         | Claude: hook `additionalContext` at tool/stop boundaries; Codex: `turn/steer`. No visible queue states   |
| Questions        | `plane_ask_question` MCP tool → `AgentRunQuestion` + `awaiting` (phase-04)                                                                                                                                                                               | `AskUserQuestion` disabled; the agent asks in an issue comment                                           |
| Stop             | Plane Stop command, interrupt, settle (30 s), clone kept (phase-05)                                                                                                                                                                                      | 5 s status poll, `turn/interrupt` or SIGTERM→SIGKILL on the process group                                |
| Push / PR        | Worker pushes `refs/heads/<branch>` only after a consumed grant; Plane creates the PR via `GitProviderClient`; token never near the agent (phase-07, contracts §11)                                                                                      | Agent pushes and runs `gh pr create` with host credentials                                               |
| HITL             | Per-effect permission card: allow once / allow for Run / deny (AD-8, Epic 3)                                                                                                                                                                             | None                                                                                                     |
| Scale            | `AgentCodeSlot` N=2 for Code; Q&A unbounded (phase-07)                                                                                                                                                                                                   | 20 concurrent tasks per daemon                                                                           |

## 3. Simplifications we could adopt

Ranked by value divided by risk. "Spec conflict" names the governing rule. Items that touch a user decision are in section 4 and are not recommended here.

### S1. Make the connection check cheap; run full conformance once per CLI version (recommended)

- **Change.** "Connect" runs `which` + `--version` + `auth status` + model list. That takes about 2-5 s, against about 33 s for the current probe. The 7 behavior checks run once per installed CLI version. The result is cached by `(harness, version)` and re-run when the version changes, or by an explicit "Re-verify" action. Multica shows that PATH + version is enough in practice. Our auth check adds the useful "not logged in" hint that Multica lacks.
- **Affects.** Stories 2.1 and 2.6 (epics.md:595-741), and 2.21, 2.23, 2.25 (epics.md:1135-1273). Files: `conformance.py`, `drivers/*`, `AgentConnection` (add `verified_version`).
- **Spec conflict.** AD-4 says "A driver is Connected only after a local probe verifies … for its installed version" (Spine line 81). Caching by version still meets the letter of that rule. A per-click 7-check run is not required.
- **Lost.** If a CLI breaks behavior without a version change (for example a server-side model change), we detect it at Run time, not at Connect time.
- **Effort saved.** Small in Phase 2 (the probe already exists). About 1-2 d in Phase 6, because the Grok and Omp probes run less often and are easier to debug. Better UX: Connect becomes fast.

### S2. Use Multica's Claude mid-turn method, or drop Claude mid-turn input (recommended to decide early)

- **Change.** Multica's evidence says Claude has no true mid-turn user input, only hook `additionalContext` at tool boundaries. For Phase 5 Send now, choose one of two options:
  - (a) Set `midturn_input=false` for Claude and use AD-5 cancel-then-next-turn.
  - (b) Copy the Multica hook method. This needs hooks, but Q16 turns hooks off (`claude_boundary.py:28`).

  Option (a) is simplest and is already allowed by AD-5. Codex keeps `turn/steer`, which is proven by Multica.

- **Affects.** Phase 5 stories 2.14-2.20 (epics.md:957-1133), `drivers/claude.py` `_check_interruption`.
- **Spec conflict.** None for (a). For (b), Q16 says "hooks are off".
- **Lost.** With (a), Send now on Claude stops the current tool call and starts a new turn. Some in-flight work is lost, but the session resumes.
- **Effort saved.** About 1-2 d in Phase 5. It also avoids building on a mechanism that conflicts with Q16.

### S3. Model list without a full session (small, recommended)

- **Change.** Keep the `initialize` control request (it already works), but run it as a one-shot with stdin EOF, as Multica does (`claude_models.go:69-90`), with a static fallback. For Codex, use `model/list` (already planned), with `codex debug models` as a fallback.
- **Affects.** 2.6, 2.21. **Lost:** nothing. **Saved:** less than 0.5 d; it also makes the probe less fragile.

### S4. Reuse a per-run `CODEX_HOME` as the Q1 disposable runtime (recommended, aligns with Q1)

- **Change.** Multica gives each run its own `CODEX_HOME` with a managed `config.toml` block that sets `sandbox_mode` (`security-model.mdx:39`, `codex_sandbox.go:356`). Multica does not set `approval_policy`. For Phase 6, the Q1 "private runtime directory" can simply be `CODEX_HOME=<run_root>/<run_id>/turn-N/codex-home`. Our `config.toml` would set `sandbox_mode` and `approval_policy`, and auth is linked or copied from `~/.codex/auth.json`.
- **Affects.** Phase 6, 2.21-2.22. **Spec conflict:** none (this is how Q1 is implemented). **Lost:** nothing. **Saved:** about 1 d of design work. Note the Multica finding: Codex `workspace-write` on macOS ignores `network_access`. That does not matter for read-only Q&A.

### S5. Keep clarification questions in the conclusion comment, not in a structured tool (needs light user OK)

- **Change.** Drop `plane_ask_question` and `AgentRunQuestion(kind=harness)`. Keep only the Plane-side repository question (2.11, UX-DR11). As Multica does, disable `AskUserQuestion` and let the agent ask in its reply. The member answers with a normal follow-up (2.13).
- **Affects.** Phase 4 key decision "Harness questions"; Phase 6 2.26 (Omp UI-response maps to a question).
- **Spec conflict.** UX-DR11 (epics.md:282-285) names only repository choices. FR9 lists "elicitation" as a timeline row type (epics.md:78, 254). Omp UI-response would need a decision: map it to a plain message, or refuse it.
- **Lost.** "Waiting for you" state and selectable answers for Harness questions.
- **Effort saved.** About 1-1.5 d across Phases 4 and 6.

### Not recommended to copy

- **Bare cache + worktree instead of a fresh clone.** It is faster and uses less disk, but it adds code (cache, eviction, GC) and shares git objects across Runs. That breaks the cross-Run read denial in `claude_boundary.py` (`denyRead` on the Run root). It is not a simplification for one Mac Mini.
- **Full environment passthrough.** Our 13-name allowlist costs nothing and is what keeps tokens out.
- **WebSocket wake.** Our 2 s poll is simpler and fine for one Worker.
- **Agent-run `gh pr create`.** This breaks the success criterion "No provider token appears in … process environment" (plan.md:66) and the protected-branch guard. See F2.

## 4. Where our spec requires something Multica does not do (user decision)

Each item below is large. The user must decide; I do not recommend reversing any of them silently.

| #   | Spec requirement                                                                                                                                              | Multica                                                                     | Option if the user wants to simplify                                                                                                                                                                                                          | Lost                                                                                                            | Saved (estimate)                                                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F1  | Per-effect permission card before each write, command, network or path escalation, and before commit, push and PR (AD-8; stories 3.1-3.5, epics.md:1280-1438) | No HITL; everything auto-approved                                           | One approval "Start Code job" (escalation), then free writes inside a sandboxed Worktree; keep separate approvals only for push and PR                                                                                                        | Per-command audit and deny; "Allow for this Run" scope logic; network and path escalation cards (3.4, 3.5)      | 5-7 d of Phase 7's 17 d                                                                                                                                                                           |
| F2  | Worker-owned push, Plane-owned PR, token never near the agent (contracts §11; plan.md:65-66)                                                                  | Agent pushes and opens the PR with host credentials                         | Keep as is (recommended). Alternative: agent commits in the Worktree (no credentials needed), Worker pushes and Plane opens the PR. This drops only the separate `plane_commit` grant                                                         | Commit grant (3.1 AC "each of commit, push and PR needs its own grant")                                         | about 0.5-1 d                                                                                                                                                                                     |
| F3  | Docker container per Code Run with N slots (AD-11; 3.6-3.7)                                                                                                   | No container; boundary = OS user; 20 concurrent tasks                       | Run the Code turn in Claude's built-in sandbox with writes allowed only in the Worktree and network off (extends Q16 to Code). Drop `AgentCodeSlot` and the Docker CLI seam                                                                   | Strong isolation for arbitrary build commands; the AD-8 file-publish path; capacity UX (3.6)                    | 4-6 d                                                                                                                                                                                             |
| F4  | Q&A read-only at an OS boundary; agent sandbox "not the only boundary" (AD-7, Spine line 128)                                                                 | No read-only mode at all                                                    | Extend the Q16 exception to Codex: Codex `sandbox_mode = "read-only"` and `approval_policy = "never"` in the per-run `config.toml` instead of the outer macOS profile. Then Q1 becomes only "per-run `CODEX_HOME`" (S4). Grok and Omp keep Q1 | Same trade-off as Q16. The Codex process itself runs unsandboxed and Codex's sandbox covers only model commands | 1-2 d in Phase 6. **[UNVERIFIED]** for Codex 0.157: that read-only mode rejects `apply_patch` and that the app-server writes its state only under `CODEX_HOME`. The Phase 6 probe must prove both |
| F5  | 7-check probe on every Connect (AD-4)                                                                                                                         | PATH + version only                                                         | S1: cache by version                                                                                                                                                                                                                          | See S1                                                                                                          | See S1                                                                                                                                                                                            |
| F6  | Durable queue states for each panel message (AD-5; 2.14-2.20)                                                                                                 | Supplements with ack, no queue UI                                           | No change recommended; the states are core UX in the design handoff                                                                                                                                                                           | —                                                                                                               | —                                                                                                                                                                                                 |
| F7  | No ACP (contracts §9, PRD 2026-09-27)                                                                                                                         | Grok runs through ACP: `grok agent stdio` (`server/pkg/agent/agent.go:536`) | For information only: Multica's choice suggests ACP is the maintained Grok path. Re-check the Grok headless JSON route before Phase 6                                                                                                         | —                                                                                                               | —                                                                                                                                                                                                 |

## 5. Limitations

- I did not run Multica. The claims come from code and docs at `43b0571f99`, cross-checked against HEAD `dfcc633dda2e`.
- I did not verify the server-side claim and lease semantics of Multica (`prepare-lease`, `agent.sql` claim queries) beyond the `SKIP LOCKED` lines.
- I did not research Grok or Omp in depth in Multica, because the question was Claude and Codex.
- The effort numbers are estimates from the phase files, not measurements.
- GitNexus tools were not available in this session, so I read files directly.

## Unresolved questions for the user

1. F1/F3: Do you want to keep per-effect HITL and Docker for Code jobs (spec as written), or move to "one Code-job approval + agent sandbox in the Worktree + approvals only for push and PR"? This is the largest saving (about 9-13 d) and the largest security change.
2. F4: Do you want to extend the Q16 decision (agent built-in sandbox instead of an outer OS boundary) to Codex Q&A?
3. S2: For Claude Send now, do you accept cancel-then-next-turn (simplest), or do you want Multica's hook method, which needs hooks that Q16 turns off?
4. S5: Can Harness questions become plain text in the reply (no structured question card), with only the repository question kept as a card?
5. S1: Is "full conformance once per CLI version, cheap check on Connect" an acceptable reading of AD-4?
