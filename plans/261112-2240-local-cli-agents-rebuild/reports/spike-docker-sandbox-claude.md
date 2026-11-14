# Spike: Claude Code in Docker Sandboxes (decision Q30)

Date: 2026-11-14 (Asia/Saigon). Time used: about half a working day. Host: this Mac (not the Mini), macOS 27.2.1, Apple silicon (arm64), 16 CPU, 48 GiB RAM, Docker Desktop 29.5.2.

## Verdict: GO with limits

The microVM can be the boundary. The Worker can drive the sandboxed `claude` over plain pipes, with stream-json, `initialize`, `--resume`, interrupt, a real model call through the user's gateway, a gateway-only network policy and full permissions. The agent could not read a host canary file.

The limits:

1. All hands-on results come from the Docker Desktop plugin `docker sandbox` v0.12.0. The current tool `sbx` v0.53.0 is installed, but it needs `sbx login` (Docker OAuth). That is a user step, so no `sbx` command was run against a sandbox. `sbx` behavior is documented, not tested.
2. A host-side kill does not stop the process inside the sandbox. The Worker must stop the process inside (pidfile kill or the stream-json `interrupt`).
3. The primary workspace must be read-write. A read-only Q&A Run needs an empty scratch primary plus the repository as a read-only extra mount.
4. Disk cost is high: 9 to 17 GiB per sandbox on this Mac. Keep few sandboxes and remove them after use.
5. The user's `~/.claude` (hooks, MCP servers, skills, settings) is not imported. Q29 ("user hooks and MCP stay on") cannot hold as decided. Only project-level `.claude/` in the workspace works.
6. With the plugin, the gateway token is copied into the VM as an env var (accepted by Q30). With `sbx set-custom`, the VM sees only a placeholder. That path is untested.

## Tool and versions

| Item | Value | Evidence |
| --- | --- | --- |
| `docker sandbox` (Docker Desktop plugin) | v0.12.0 | `docker sandbox version` -> `Client Version: v0.12.0 f13b3c1a` |
| `sbx` | v0.53.0, installed | `brew trust docker/tap && brew install docker/tap/sbx` -> `Cask sbx (0.53.0)`. Documented at docs.docker.com/ai/sandboxes/install |
| `sbx` state | not signed in | `sbx ls` -> `Error: not signed in to Docker`; `sbx diagnose` -> 12 passed, daemon not running |
| Claude Code in template | 2.1.306 | `claude --version` inside `docker/sandbox-templates:claude-code` |
| Guest | Linux 6.12.67-linuxkit aarch64, user `agent` (uid 1000) with sudo, own Docker Engine 29.2.0 | `id`, `uname -a`, `docker info` inside |

Why the plugin: the brief prefers `sbx` when the install is a normal step. The install was normal. The sign-in is not (browser OAuth, or a Docker PAT). The plugin worked with no sign-in.

## The 10 questions

All commands ran from `/tmp/sandbox-spike/`. The probe scripts are `stream_probe.py`, `interrupt_probe.py` and `allow_gateway.sh` there. The probe runs `docker sandbox exec -i -w <ws> [-e NAME...] <sandbox> claude -p --input-format stream-json --output-format stream-json --verbose --include-partial-messages --replay-user-messages --permission-prompt-tool stdio [extra]`. It sends `initialize`, then one user message, over a pipe with no TTY.

| # | Question | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Non-interactive stream-json over pipes | PASS. First event in 0.24 to 0.42 s (warm). A full "pong" turn took 2.5 to 3.7 s. Stdin EOF is forwarded. | `printf 'line1\nline2\n' \| docker sandbox exec -i spike-ds-a cat` echoed both lines, exit 0. Probe: `0.28s control_response/success models=['default','opus','fable','sonnet','haiku']`, `0.30s system/init ...`, `1.95s result/success is_error=False result='pong'`, `exit=0`. A warm `exec true` takes 0.085 s. |
| 2 | Session resume across invocations | PASS. It also survives `stop` and restart of the sandbox. | Turn 1: "Remember the code word ZEBRA-41" -> session `22b77317-...`. A second exec with `--resume 22b77317-...` -> `result='ZEBRA-41'`. After `docker sandbox stop` and a new exec -> `result='ZEBRA-41'` again. Sessions live in `/home/agent/.claude/projects/-tmp-sandbox-spike-ws-a/` inside the VM, not on the host. |
| 3 | Interrupt | PASS with stream-json; FAIL with host signals. | `control_request {subtype: interrupt}` after 8 stream events -> `control_response success at 3.29s`, `result#1 subtype=error_during_execution`, then a next turn in the same process -> `result#2 ... 'ready'`, exit 0. Host SIGKILL of the exec client: `claude -p` was still running inside 3 s later; it was gone after 17 s (turn ended). Host SIGTERM to `docker sandbox exec ... sleep 120`: `sleep 120` still ran inside. A kill from a pidfile inside (`kill -TERM $(cat /tmp/spike-sleep.pid)`) worked. |
| 4 | Auth | PASS with the plugin. sbx path: documented, untested. | Plugin: `-e ANTHROPIC_BASE_URL -e ANTHROPIC_AUTH_TOKEN` (name only) copies the host values. Note: this worked because the spike shell already had both variables (Claude Code put them there from `~/.claude/settings.json` `env`). A Worker daemon will not have them; see the design. The values were never printed. With the gateway allowed: `result='pong'`. The template sets no `ANTHROPIC_*` variable (env names only: `HTTP(S)_PROXY`, `NODE_EXTRA_CA_CERTS`, `SSL_CERT_FILE`, ...). The token is readable by the agent in the VM (accepted, Q30). sbx: the built-in `anthropic` secret injects only into `api.anthropic.com`, `claude.ai` and two more Anthropic hosts. A gateway needs the experimental `sbx secret set-custom --host <gateway-host> --env ANTHROPIC_AUTH_TOKEN` (see "User steps"). |
| 5 | Network policy | PASS. A gateway-only policy works, with one caveat. | Plugin default is open (`https://example.com 200`, `github.com 200`, `http://host.docker.internal:8000/ 500`). `docker sandbox network proxy spike-ds-a --policy deny --allow-host example.com` -> example.com 200, host port 403, direct connection without the proxy fails (`--noproxy '*'` -> `000`). Caveat: deny keeps a built-in allow list (`api.anthropic.com:443`, `github.com:443`, `*.npmjs.org:443`, `pypi.org:443`, `*.googleapis.com:443`, ...). `--block-host github.com` had no effect; `--block-host github.com:443` worked (`github.com 403`). Gateway: before allow -> `API Error: 403 Blocked by network policy: matched rule <default policy>`; after `allow_gateway.sh` -> `pong`. The policy survives a restart. The gateway URL uses plain `http`. sbx has presets (`sbx policy init balanced`, `deny-all`) and `sbx policy allow network --sandbox <name> <host>` (documented, untested). |
| 6 | Workspace | Live bind mount (virtiofs), read-write, same absolute path. Extra mounts can be `:ro`. The primary cannot. | `mount` -> `virtiofs0 on /tmp/sandbox-spike/ws-a type virtiofs (rw,...)`. A file written inside appears on the host at once (owner `dale`), and the other way. `create ... /tmp/sandbox-spike/ws-b /tmp/sandbox-spike/ro-docs:ro` -> `cannot create .../ro-docs/w.txt: Read-only file system`, also with `sudo`. `create ... ws-c:ro` -> `primary workspace must be read/write`. The host sees agent edits directly, so `git diff` on the host gives the patch. sbx adds `--clone` (changes stay in the VM until `git fetch sandbox-<name>`) and mountless sandboxes with `sbx cp` (documented, untested). |
| 7 | User hooks, MCP, skills | Project-level config works. User-level config does not. | `ws-a/.claude/settings.json` with a `UserPromptSubmit` hook -> `hook-proof.txt` written (hook ran inside the VM). `--mcp-config /tmp/sandbox-spike/ws-a/.spike-mcp.json` with a stdio server -> `result='pong-from-mcp'` (server ran inside the VM). Host HTTP port: `--allow-host localhost:8000` -> `host.docker.internal:8000 -> 500` (reachable). VM `~/.claude/settings.json` is the template's own (`defaultMode: bypassPermissions`). Docs: `~/.claude` is not imported. `sbx skills import` copies `~/.claude/skills` into the VM read-only (experimental, untested). The plugin has no skills command. |
| 8 | Isolation with full permissions | PASS. | Agent run with `--dangerously-skip-permissions` (`perm=bypassPermissions`, model haiku), own Bash: `cat /tmp/sandbox-spike/outside/canary.txt` -> `No such file or directory`; `ls /Users/dale/Desktop/workspace` -> no such directory; `ls /private/tmp` -> no such directory; `find / -name canary.txt` -> nothing; host port 8000 -> 403; write in workspace -> ok. Sandbox B could not see sandbox A's workspace. The `/tmp/sandbox-spike` parent inside holds only the mounts and a template `CLAUDE.md`. |
| 9 | Costs | See table below. | |
| 10 | Operations on the Mac Mini | See section below. | Missing sandbox: `docker sandbox exec nosuch-sandbox true` -> `VM nosuch-sandbox not found`, exit 1. |

### Costs (Q9)

| Measure | Value | Evidence |
| --- | --- | --- |
| First create, image not cached | 89 s (pull of `docker/sandbox-templates:claude-code`, 2.92 GB) | `time docker sandbox create ...` -> `1:29.26 total` |
| Cold create, image cached | 18.4 to 19.3 s | `/usr/bin/time -p docker sandbox create -q ...` -> `real 19.28`, `real 18.38` |
| Warm restart of a stopped sandbox | 2.2 s (first `exec` starts it) | `Starting sandbox container...`, `real 2.23` |
| Warm exec | 0.085 to 0.12 s | `real 0.12` |
| Stop | 0.5 s | `real 0.50` |
| Memory per VM (host RSS) | 0.38 to 1.55 GB | `ps -o rss` of the three `com.docker.krun` processes: 415408, 384368, 1551696 KB |
| Guest memory | about 4 GB, 16 vCPU | `free -m` -> total 3917; `nproc` -> 16 |
| Disk per sandbox | 9.1 to 17 GB | `du -sh ~/.docker/sandboxes/vm/spike-ds-*`. Host free space fell from 65 GiB to 12 GiB with three sandboxes. It came back after `rm`. |
| Concurrency | 3 sandboxes, 3 parallel turns, wall 3.75 s, each first event under 0.42 s | parallel probe on a, b, d |
| Cleanup | `docker sandbox rm <name>`; sbx: `sbx rm`, `sbx prune`, `sbx df` | Plugin left an 8 KB `~/.docker/sandboxes/vm/spike-ds-d/container-platform.log` dir after `rm` (removed by hand). |

### Operations (Q10)

- macOS 14 or later, Apple silicon only (docs: install page). The Mini must be Apple silicon.
- `sbx` does not need Docker Desktop. The plugin needs Docker Desktop running.
- `sbx` needs a Docker sign-in. For an unattended Mini: `echo "$DOCKER_PAT" | sbx login --username <docker-id> --password-stdin` (PAT with Read scope). `sbx reset` deletes all secrets; never run it from the Worker.
- Secrets are in the macOS Keychain. The Worker must run in the user's login session.
- Failure modes seen or documented: sandbox missing (exit 1 plugin, 125 sbx); Docker Desktop or `sandboxd` not running (`sbx diagnose` reports "Daemon - not reachable"); policy blocks the gateway (`API Error: 403 Blocked by network policy` in the `result` event, so the Worker can map it); disk full (each sandbox takes 9 to 17 GB).
- First run pulls about 3 GB. Pre-pull at install time.

## User steps (needed before the sbx path is tested)

Run on the machine that runs the Worker. Values are typed at the prompt, never on the command line.

```sh
sbx login                                    # or: echo "$DOCKER_PAT" | sbx login --username <docker-id> --password-stdin
sbx policy init deny-all                     # or balanced for Code jobs (Q27)
sbx policy allow network <gateway-host>:<port>
sbx secret set-custom --host <gateway-host> --env ANTHROPIC_AUTH_TOKEN   # prompts for the value
```

Then the Worker passes `-e ANTHROPIC_BASE_URL=<gateway-url>` and the placeholder that `set-custom` prints as `ANTHROPIC_AUTH_TOKEN`. `set-custom` is experimental. Its header replacement on a plain `http` gateway is untested.

## Proposed Worker design (if GO)

- One long-lived sandbox per repository (or per Worker), created once. Cold create costs about 19 s and 9 to 17 GB, so a sandbox per Run is too costly. Each Run is one `exec` (about 0.1 s).
- Credentials: inside the VM, Claude does not read the host `~/.claude/settings.json`, so the Q28 path ("Claude reads its own settings") is gone. The Worker must get the gateway URL and token itself: from its own config, from the `env` block of the user settings file, or (sbx) from `sbx secret set-custom` so only a placeholder enters the VM. The driver `ENV_ALLOWLIST` already names the variables; nothing fills them yet.
- Permissions: the Worker must pass `--dangerously-skip-permissions`. Without it, `exec` runs showed `perm=default` (the template's `defaultMode: bypassPermissions` did not apply with `-p ... --permission-prompt-tool stdio`), so Claude would send `can_use_tool` requests over stdio. With the flag: `perm=bypassPermissions`.
- Process: `docker sandbox exec -i -w <cwd> -e ... <sandbox> sh -c 'echo $$ > /run/plane/<run-id>.pid; exec claude <SESSION_FLAGS> ...'` (sbx: `sbx exec -i ... -- ...`). The driver keeps its stdin/stdout JSON code. Only the spawn command changes.
- Stop: send the stream-json `interrupt` first. To end the process, send `kill -TERM` by pidfile through a second `exec`. Do not rely on `os.killpg` of the host client.
- Q&A Run: primary = empty per-Run scratch dir; repository = extra mount `:ro`. The agent runs with full permissions. Writes to the repository fail at the mount. This needs a sandbox per repository, because mounts are fixed at create.
- Code job: primary = the per-job worktree, read-write. The Worker reads changes with `git diff` on the host and commits and pushes itself (Q22). Network: balanced or open policy (Q27). Alternative with sbx: `--clone` and `git fetch sandbox-<name>`.
- Network: deny by default, allow the gateway host and the Plane MCP port (`localhost:<port>` via `host.docker.internal`). With the plugin, also block each built-in allow entry by `host:port`.
- Plane MCP server: run it as HTTP on the host (allowed port), or as stdio inside the VM. Proven: both reach the agent.
- Sessions stay in the VM. `--resume` works while the sandbox exists. Removing the sandbox loses the history. Keep the sandbox, or copy `~/.claude/projects` out before `rm`.
- Model list: `initialize` works in the VM as on the host.
- Permission prompt tool: in bypass mode no `can_use_tool` request comes. The Worker still handles the event shape. Harness questions (Q24) go through the Plane MCP tool, which still works.

### What of Q16, Q28, Q29 can be deleted

- Q16: delete the built-in Bash sandbox, `denyRead`/`denyWrite`, the `Read(...)` deny rules, the Edit/Write/NotebookEdit deny rules and `disableBypassPermissionsMode`. Delete `claude_boundary.py` settings and the boundary checks in `conformance.py`. Keep the stream-json, model and resume checks; run them through `exec`.
- Q28: "run Claude as installed" no longer applies. The VM has its own Claude install and settings. Auth moves to sandbox env or sbx secrets. The precedence proof against user settings is not needed.
- Q29: user hooks and MCP servers do not load (not imported). This reverses the effect of Q29. It needs a user decision: accept, or mount selected items (`sbx skills import`, project `.claude/`, `--mcp-config`).
- The open question about repository `.claude/settings.json` falls away: project hooks run, but inside the VM.
- `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` can stay. It costs nothing.

## Effort impact (Phases 3 to 7)

| Phase | Change | Estimate |
| --- | --- | --- |
| 2 (done or in review) | Boundary code becomes dead code after the switch. | -0 now; removal goes with Phase 3 |
| 3 | +0.5d: Worker-side credential source (gateway URL and token). +2d: sandbox manager (create, ensure-running, exec spawn, pidfile, policy, cleanup), sbx install and sign-in check in the connection probe. -1.5d: no boundary proof. | +1d |
| 4 | Read-only repository mount and scratch primary per sandbox. | +0.5d |
| 5 | Stop through `interrupt` and pidfile kill; stale recovery must find orphan processes in the VM. | +1d |
| 6 | Codex and Omp can use the same sandboxes (`sbx` has a Codex agent; Omp needs a shell sandbox or a custom template). Q1 outer profile and Q23 proofs may drop. | -1d to +1d (needs its own check) |
| 7 | Worktree as primary workspace; diff on the host stays the same; balanced policy. Disk limits for concurrent Code jobs. | +0.5d |

Net: about +2 to +4 days, plus a 0.5-day sbx check after the user signs in.

## Open questions

1. Plugin or sbx? The plugin worked today but is older (v0.12) and tied to Docker Desktop. sbx is current but needs a Docker sign-in on the Mini. Docs do not say whether the plugin is deprecated.
2. Does `sbx secret set-custom` replace the placeholder on a plain `http` gateway? Does Claude send `Authorization: Bearer` with only `ANTHROPIC_AUTH_TOKEN` set in the sbx claude kit (which may set `ANTHROPIC_API_KEY=proxy-managed`)?
3. Q29 reversal: accept that user hooks, MCP servers and skills do not load, or choose items to bring in?
4. Disk: is 9 to 17 GB per sandbox acceptable on the Mini? How many sandboxes at most?
5. Session history lives in the VM. Is losing it on sandbox removal acceptable, or must the Worker copy it out?
6. Codex, Omp: use sandboxes too (Phase 6), or keep Q1 and Q23?

## Cleanup record

- Before: `docker sandbox ls` -> `No sandboxes found`; 3 containers; 110 volumes.
- Created: sandboxes `spike-ds-a`, `spike-ds-b`, `spike-ds-d` (`spike-ds-c` failed at create, nothing made). All removed with `docker sandbox rm`.
- After: same as before (`diff baseline-before.txt baseline-after.txt` -> no difference). No other project's containers were touched.
- Left on the host: the `sbx` 0.53.0 cask (`brew uninstall --cask sbx` to remove; `brew trust docker/tap` was added), the image `docker/sandbox-templates:claude-code` (2.92 GB, `docker rmi` to remove), `~/.docker/sandboxes/image-cache` (752 MB), and throwaway files under `/tmp/sandbox-spike/`.
