# Spike: `sbx` verification for Claude Code agent runs (decision Q33)

Date: 2026-11-14 (Asia/Saigon). Host: this Mac (not the Mini), Apple silicon, macOS 27.2, Docker Desktop also running. Tool: standalone `sbx` v0.53.0 (`2c62838`), signed in, `sbx diagnose` healthy. Kit: `docker.io/sbx/claude@sha256:4df39400...`, Claude Code 2.1.325 inside.

Earlier spike (plugin `docker sandbox` v0.12.0): `spike-docker-sandbox-claude.md` in this folder. Throwaway scripts: `/tmp/sandbox-spike/sbx_probe.py`, `sbx_interrupt.py`, `sbx_allow_gateway.sh`, `skills_probe.py`, `skills_names.py`, `http_mcp.py`, `sbx-ws-a/stdio_mcp.py`.

## Verdict: sbx GO with limits

All 10 criteria pass on `sbx`. For criterion 10 the symlink idea works only until the first restart (sbx remounts its managed skills dir through the link); the durable route is extra `:ro` mounts plus `claude --add-dir`. No fallback to the plugin is needed. `sbx` is better than the plugin on auth (the VM sees only a placeholder), network (no hidden allow list after one deny rule), and disk (about 75 MB per sandbox instead of 9 to 17 GB).

The limits:

1. A host-side kill of `sbx exec` does not stop the process inside (same as the plugin). Stop with the stream-json `interrupt`, or with `kill` of a pidfile through a second `sbx exec`.
2. `deny-all` still has a kit allow list per sandbox (Anthropic hosts, `deb.debian.org:80`, `dhi.io:80`). Add one sandbox deny rule to close it. The kit also connects a Docker MCP gateway (`mcp-gateway.docker.internal`) by default.
3. `set-custom` does not put the placeholder into the VM env. The Worker must pass `-e ANTHROPIC_AUTH_TOKEN=<placeholder>`.
4. Sandboxes auto-stop 30 s after the last `exec` ends. The next `exec` restarts it in 1.4 to 2.1 s.
5. The kit has no Node.js. Stdio MCP servers must use Python or a binary, or the Worker adds a kit.
6. User skills: `sbx skills import` copies a static snapshot. A live, read-only view works with an extra mount plus `claude --add-dir` (criterion 10). The symlink idea works only until the sandbox restarts.
7. Claude caches an HTTP MCP server as `needs-auth` when the proxy blocks its first connect. Add the policy rule before the first run.
8. A wrong token placeholder makes Claude retry for about 3 minutes before it reports 401.

## Criteria

All commands ran from `/tmp/sandbox-spike/`. The gateway host is shown as `<gateway-host>`. The token value was never printed or read; it went into `sbx` only by stdin from the shell env.

| # | Criterion | Result | Command and evidence |
| --- | --- | --- | --- |
| 1 | stream-json over plain pipes, no TTY | PASS | `sbx exec -i -w <ws> -e ANTHROPIC_BASE_URL -e ANTHROPIC_AUTH_TOKEN sbx-a claude -p --input-format stream-json --output-format stream-json --verbose --dangerously-skip-permissions`. Output: `0.26s control_response/success models=['default','opus','fable','sonnet','haiku']`, `0.29s system/init ... perm=bypassPermissions`, `result/success result='pong'`, exit 0. First event 0.26 to 0.35 s in 6 runs. Full turn 2.0 to 3.7 s. `printf 'line1\nline2\n' \| sbx exec -i sbx-a cat` echoed both lines, exit 0. `-e NAME` (name only) copies the host value (`SPIKE_X=hello`). |
| 2 | Resume in a later separate exec | PASS | Turn 1 "Remember the code word ZEBRA-77" -> session `85588897-...`. New exec with `--resume 85588897-...` -> `result='ZEBRA-77'`. After `sbx stop sbx-a` and a new exec -> `result='ZEBRA-77'` again. Sessions live in the VM at `/home/agent/.claude/projects/-tmp-sandbox-spike-sbx-ws-a/`. |
| 3 | Interrupt and hard stop | PASS (pidfile and stream-json); host kill does not stop the process | `sbx_interrupt.py control`: `control_request {subtype: interrupt}` -> `control_response success at 2.16s`, `result#1 subtype=error_during_execution`, then `result#2 ... 'ready'` in the same process, exit 0. `sbx_interrupt.py pidkill` (inner `sh -c 'echo $$ > /tmp/spike-claude.pid; exec claude ...'`, then `sbx exec sbx-a sh -c 'kill -TERM $(cat /tmp/spike-claude.pid)'`) -> kill rc 0, host exit 143, `pgrep claude` inside: none. `hostkill` (SIGKILL of the host client group): `claude -p` still ran inside 3 s later, gone about 18 s later (turn ended). SIGTERM to `sbx exec -i sbx-a sleep 120` -> host prints `context canceled`, `sleep 120` still runs inside. Stdin EOF also does not end `sleep`. Same as the plugin. |
| 4a | Gateway auth with `sbx secret set-custom` | PASS | `printf '%s' "$ANTHROPIC_AUTH_TOKEN" \| sbx secret set-custom --sandbox sbx-a --host <gateway-host> --env ANTHROPIC_AUTH_TOKEN --value-stdin` -> `Generated placeholder: sbx-cs-RyTd...`. Inside the VM the variable was unset, also after restart ("You may need to update environment variable ... to the placeholder"). With `-e ANTHROPIC_BASE_URL -e ANTHROPIC_AUTH_TOKEN=sbx-cs-RyTd...` -> `result='pong'`. Inside: `len=23 prefix=sbx-cs-`, so the agent sees only the placeholder. Control with a wrong placeholder -> `API Error: 401 Authentication failed: invalid user_key` after 179 s of retries. So the proxy replaces the placeholder in the `Authorization: Bearer` header on a plain `http` gateway. The kit sets no `ANTHROPIC_API_KEY` (`SBX_CRED_ANTHROPIC_MODE=none`). Note: `sbx secret ls` shows a masked prefix and suffix of the stored value. |
| 4b | Gateway auth with env pass-through | PASS | `-e ANTHROPIC_BASE_URL -e ANTHROPIC_AUTH_TOKEN` (names only) -> `tok_len=39` inside, `result='pong'`. The real token is then readable by the agent in the VM. |
| 5 | Network: deny-all plus gateway | PASS | `sbx policy init deny-all` (global was uninitialized before). Before allow: `API Error: 403 Approval required for <gateway-host>`, and `sbx policy approval ls` lists a pending approval. `sbx policy allow network --sandbox sbx-a <gateway-host>:<port>` -> `pong`. Inside: `example.com`, `github.com`, `registry.npmjs.org`, `pypi.org`, `http://example.com`, `claude.ai`, `host.docker.internal:8000` -> 403; direct `--noproxy '*'` -> 000. But `api.anthropic.com/v1/models` -> 401 (reachable): `sbx policy ls sbx-a --wide` shows a `kit` rule `provisioned` for `api.anthropic.com:443, bridge.claudeusercontent.com:443, claude.com:443, deb.debian.org:80, dhi.io:80, downloads.claude.ai:443, mcp-proxy.anthropic.com:443, platform.claude.com:443`. `sbx policy deny network --sandbox sbx-a "<those hosts>"` -> all 403, gateway still `pong`. `sbx policy log sbx-a` lists allowed and blocked hosts. |
| 6 | Mounts: rw primary, `:ro` extra | PASS | `sbx create --name sbx-a claude <ws-a> <ro-docs>:ro`. `/proc/mounts`: `host <ws-a> virtiofs rw`, `host <ro-docs> virtiofs ro`. Write in ws-a -> on host at once (owner `dale`), and the other way. In ro-docs: `echo`, `sudo sh -c 'echo ...'`, `sudo rm` -> `Read-only file system`. No `mount` binary in the kit, so a remount is not possible. `sbx create ... <ws-c>:ro` -> `error: primary workspace must be read/write`. |
| 7 | Isolation canary, full permissions | PASS | Host canary `/tmp/sbx-canary.txt`. Agent (haiku, `perm=bypassPermissions`, own Bash tool): `cat /tmp/sbx-canary.txt`, `cat /private/tmp/sbx-canary.txt`, `cat <sbx-ws-b>/b-only.txt`, `cat /tmp/sandbox-spike/outside/canary.txt` -> `No such file or directory`; `ls /Users/dale` -> no such directory; `sudo find / -xdev -name ...` -> nothing; host port 8000 -> 403; write in its workspace -> ok. Sandbox B sees only `sbx-ws-b` under `/tmp/sandbox-spike`. Each sandbox is its own VM: different `boot_id`, kernel `7.0.14 aarch64`, one `docker-docklet` host process per running sandbox. |
| 8 | Skills import, MCP | PASS | `sbx skills import --dry-run` -> `Dry run: 525 skills would be imported into ~/Library/Application Support/com.docker.sandboxes/sandboxes/agent-skills`, from `~/.agents/skills`, `~/.claude/skills`, `~/.config/opencode/skills` (first copy wins). Nothing copied (dir stayed empty). That dir is mounted read-only at `/home/agent/.claude/skills` in every sandbox. Stdio MCP: the Node server from the plugin spike failed (`node` not in the kit); a Python stdio server via `--mcp-config` -> `spike-echo connected`, `result='pong-from-mcp'`. Host HTTP MCP on `127.0.0.1:18765`: blocked by default (`policy log`: `localhost:18765 ... default deny`); after `sbx policy allow network --sandbox sbx-a localhost:18765` Claude still showed `needs-auth` because of `~/.claude/mcp-needs-auth-cache.json` in the VM; after deleting it -> `spike-http connected`, `result='pong-from-http-mcp'`. Sandbox B (no rule) -> 403. |
| 9 | Lifecycle and cost | PASS | See table below. |
| 10 | All user skills, live and read-only | PASS with `--add-dir`; symlink route FAIL after restart | See section below. |

### Costs and lifecycle (criterion 9)

| Measure | sbx | Plugin (earlier spike) |
| --- | --- | --- |
| First create, image not cached | 49 s (kit image 1.47 GB) | 89 s (2.92 GB) |
| Create, image cached | 5.8 to 6.1 s | 18 to 19 s |
| Stop | 0.8 s | 0.5 s |
| Start (first exec on a stopped sandbox) | 1.4 to 2.1 s | 2.2 s |
| Warm exec `true` | 0.13 to 1.1 s (most 0.7 s) | 0.09 to 0.12 s |
| Remove | 0.3 s | not timed |
| Disk per sandbox | about 75 MB (container layer) + 7 MB volume; image 1.47 GB shared (`sbx df -v`) | 9 to 17 GB |
| Host memory per running sandbox | 0.9 to 1.2 GB RSS (`docker-docklet` process) | 0.4 to 1.6 GB |
| Guest | 16 vCPU, 24 GiB visible (`auto`), 20 GB root overlay | 16 vCPU, 4 GiB |
| Idle | auto-stop 30 s after the last session (`daemon.log`: `session disconnected, deferring auto-stop delay=30s`) | none seen |
| Missing sandbox | exit 125, `error: sandbox 'nosuch-sandbox' not found` | exit 1 |
| Daemon stopped | `sbx daemon stop` stops all running sandboxes. Any next `sbx` command starts the daemon again: `sbx exec sbx-a true` took 3.8 s, exit 0. | Needs Docker Desktop running |

Warning seen: `pkill sleep` inside killed PID 2 (`sleep infinity`, the container keep-alive) and stopped the sandbox. The Worker must kill by pidfile only.

### Criterion 10: all user skills, live and read-only

Host facts: `~/.claude/skills` has 497 entries; 178 are symlinks. 155 point to `../../.agents/skills/...`, 5 to `/Users/dale/.agents/skills/...`, the rest into two repositories under `~/Desktop/workspace/opensources/` (`mattpocock-skills/skills/...`, `colleague-skill`). All link targets must also be mounted, or those skills break.

| Route | Result | Evidence |
| --- | --- | --- |
| A. Extra mounts at the same path + symlink `~/.claude/skills` in the VM | Works until restart. FAIL as a durable route. | `sbx create --name sbx-c claude <ws-c> ~/.claude/skills:ro ~/.agents/skills:ro <mattpocock>/skills:ro <colleague-skill>:ro`. `/home/agent/.claude/skills` is a managed read-only mount; it needs `sudo python3 -c '...umount2(...)'` (no `umount` binary), `sudo rmdir`, `ln -s /Users/dale/.claude/skills ~/.claude/skills`. Then `system/init skills=502`, `hyperframes:yes wayfinder:yes create-colleague:yes`. After `sbx stop` + start, sbx mounts its empty managed dir through the symlink onto `/Users/dale/.claude/skills`, so the host skills are hidden (0 entries). |
| A'. Mount at `/home/agent/.claude/skills` with `PATH:TARGET:ro` | Refused | `error: ... target "/home/agent/.claude/skills" is reserved by the sandbox` |
| B. Extra mounts + `claude --add-dir` | PASS | `sbx create --name sbx-d claude <ws-d> ~/.claude/skills:/opt/user-claude/.claude/skills:ro ~/.agents/skills:/opt/user-claude/.agents/skills:ro ~/.agents/skills:ro <mattpocock>/skills:ro <colleague-skill>:ro`. Relative and absolute links resolve. Without `--add-dir`: `skills=18` (kit only). With `--add-dir /opt/user-claude`: `skills=441`, `hyperframes`, `wayfinder`, `create-colleague`, `ak-plan` present. Same names as route A, except 8 `superset:*` entries that only route A listed. After `sbx stop` + start: still 442. |
| (1) Claude loads them | PASS | `system/init` lists them. `Skill` tool call on `wayfinder` is parsed (refused only because that skill disables model invocation). |
| (2) Skill added on the host appears live | PASS | Added `~/.claude/skills/zz-sbx-spike-probe2/SKILL.md` on the host, no recreate: next run `skills=442 zz-sbx-spike-probe2:yes`, `Skill` tool -> `result='SPIKE-SKILL-OK'`. Probe skill removed from the host after the test. |
| (3) Writes fail | PASS | `echo x > .../skills/new-file.txt`, `sudo sh -c 'echo x > ...'`, `mkdir`, `sudo rm -rf .../hyperframes`, `sudo tee` into the `.agents/skills` mount -> `Read-only file system`. Host count stayed 494. |
| Compare: `sbx skills import` | Static copy | Copies 525 skills into one global dir, mounted read-only in all sandboxes. Top-level symlinks are followed at import. A skill added later needs a new `import` (it replaces the whole skill set). No per-sandbox choice. |

Recommendation: route B. It is live, read-only, survives restart and uses only documented flags. Mounts are fixed at create, so the link-target list must be known then.

## Differences vs the plugin

| Topic | sbx v0.53.0 | Plugin v0.12.0 |
| --- | --- | --- |
| Needs | Docker sign-in; no Docker Desktop | Docker Desktop running; no sign-in |
| Exec command | `sbx exec -i -w <cwd> -e ... <sandbox> <cmd>` | `docker sandbox exec -i -w <cwd> -e ... <sandbox> <cmd>` |
| Claude in kit | 2.1.325, no Node.js, Python present | 2.1.306, Node.js present |
| Token in VM | Placeholder only (`set-custom`) or real value (`-e`) | Real value only |
| deny-all extras | Kit allow list per sandbox; one deny rule closes it | Built-in allow list; needs `--block-host host:port` per entry |
| Blocked request | `403 Approval required` plus a pending approval | `403 Blocked by network policy` |
| Disk per sandbox | about 75 MB + shared 1.5 GB image | 9 to 17 GB |
| Create (cached) | 6 s | 19 s |
| Idle | Auto-stop after 30 s | Runs until stopped |
| MCP default | Docker MCP gateway connected (`mcp-gateway`) | none |
| Host kill of exec | Process inside keeps running | Same |

## Operator setup on the Mac Mini

Run in the user's login session (secrets are in the Keychain). Values come from stdin or a prompt, never from the command line.

```sh
brew trust docker/tap && brew install docker/tap/sbx
echo "$DOCKER_PAT" | sbx login --username <docker-id> --password-stdin   # PAT with Read scope
sbx diagnose
sbx policy init deny-all

# Pre-pull the kit (49 s, 1.5 GB) by one throwaway create in a scratch dir
mkdir -p ~/sbx-warmup && sbx --no-input create --name warmup claude ~/sbx-warmup && sbx rm --force warmup

# Per sandbox (the Worker runs these when it creates one)
sbx --no-input create --name <sandbox> claude <workspace> [<repo>:ro] \
  ~/.claude/skills:/opt/user-claude/.claude/skills:ro \
  ~/.agents/skills:/opt/user-claude/.agents/skills:ro ~/.agents/skills:ro \
  <each other skill link target dir>:ro
sbx policy allow network --sandbox <sandbox> <gateway-host>:<gateway-port>
sbx policy allow network --sandbox <sandbox> localhost:<plane-mcp-port>      # if Plane MCP runs on the host
sbx policy deny network --sandbox <sandbox> "api.anthropic.com:443,bridge.claudeusercontent.com:443,claude.com:443,deb.debian.org:80,dhi.io:80,downloads.claude.ai:443,mcp-proxy.anthropic.com:443,platform.claude.com:443"
printf '%s' "$GATEWAY_TOKEN" | sbx secret set-custom --sandbox <sandbox> \
  --host <gateway-host> --env ANTHROPIC_AUTH_TOKEN --value-stdin               # GATEWAY_TOKEN from the operator's secret store; prints the placeholder

# Per Run
sbx exec -i -w <workspace> -e ANTHROPIC_BASE_URL=<gateway-url> \
  -e ANTHROPIC_AUTH_TOKEN=<placeholder> <sandbox> \
  sh -c 'echo $$ > /tmp/<run-id>.pid; exec "$@"' sh \
  claude -p --input-format stream-json --output-format stream-json --verbose \
  --dangerously-skip-permissions --add-dir /opt/user-claude [--resume <session-id>]
# Hard stop:
sbx exec <sandbox> sh -c 'kill -TERM "$(cat /tmp/<run-id>.pid)"'
```

Do not run `sbx setup`, `sbx secret import` or `sbx reset` from the Worker. `setup` and `import` would store host env secrets globally; `reset` deletes all secrets.

## Cleanup record

- Before: `sbx ls` none; global policy uninitialized; no secrets; no MCP servers; `docker sandbox ls` none; 3 containers; 110 volumes; `sbx df` empty (`/tmp/sandbox-spike/sbx-baseline-before.txt`).
- Created: sandboxes `sbx-a`, `sbx-b`, `sbx-c`, `sbx-d` (twice); one sandbox-scoped custom secret; sandbox-scoped policy rules; global `deny-all`; host HTTP MCP server on port 18765; host canary `/tmp/sbx-canary.txt`; host probe skills `~/.claude/skills/zz-sbx-spike-probe*` (each removed right after its test).
- Removed: `sbx rm --force` on all four (sandbox-scoped secret and rules went with them, `sbx secret ls` -> none); `sbx policy reset --force` (policy back to uninitialized); MCP server stopped (port free); canary deleted; `~/.claude/skills` back to 494 entries.
- After: `diff sbx-baseline-before.txt sbx-baseline-after.txt` -> only `sbx df` differs (kit image 1.47 GB cached). Remove it with `sbx template rm` if needed. No other project's containers were touched.
- Left: the kit image cache (about 1.4 GB under `~/Library/Application Support/com.docker.sandboxes`), throwaway files under `/tmp/sandbox-spike/`.

## Open questions

1. Accept the 30 s auto-stop (1.4 to 2.1 s extra on the first exec of each Run after idle), or keep a session open?
2. The kit's Docker MCP gateway is connected by default. Keep it, or deny `mcp-gateway.docker.internal` (not tested)?
3. Which skill link targets must the Worker mount? It must read `~/.claude/skills` symlinks at create time.
