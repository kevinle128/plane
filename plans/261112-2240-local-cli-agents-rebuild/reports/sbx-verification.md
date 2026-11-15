# Phase 3 task 0: `sbx` verification, criteria 9 and 10

Date: 2026-11-14 (Asia/Saigon). Host: development Mac (Apple silicon), `sbx` v0.53.0 (`2c62838`), signed in. Kit: `docker.io/sbx/claude:latest` (Claude Code in the kit). Criteria 1-8 were done earlier: [spike-sbx-verification.md](./spike-sbx-verification.md).

Script: `/tmp/plane-sbx-verify/probe.py` (throwaway). It reads only `env.ANTHROPIC_BASE_URL` from the host `~/.claude/settings.json` to make the gateway allow rule, as the Worker will. It never prints the URL or a token; the gateway host is shown as `<gateway-host>`.

## Verdict

| # | Criterion | Result |
| --- | --- | --- |
| 9 | Host Claude settings, read-only (Q37) | PASS, with one limit (stale single-file mount after an atomic replace on the host) |
| 10 | Docker MCP gateway off (Q38) | PASS with `--static-mcp none` plus `--strict-mcp-config`; the deny rule is not needed (and has no effect) |

No decision changes. The fallback (env by name or `sbx secret set-custom`) is not needed.

## Setup

```sh
sbx policy init deny-all
sbx --no-input create --name plane-verify-qa --static-mcp none claude /tmp/plane-sbx-verify/ws \
  ~/.claude/settings.json:/opt/user-claude/settings.json:ro \
  ~/.claude/hooks:/opt/user-claude/hooks:ro \
  /tmp/plane-sbx-verify/live:/opt/live:ro \
  /tmp/plane-sbx-verify/live/test-settings.json:/opt/test/settings.json:ro      # 18.1 s (kit resolve), rc 0
sbx policy allow network --sandbox plane-verify-qa <gateway-host>:<port>         # rc 0
sbx policy deny network --sandbox plane-verify-qa "<kit allow list, 8 entries>"  # rc 0
```

## Criterion 9: host settings mounted read-only

| Check | Result |
| --- | --- |
| File inside the VM | `-rw------- 1 agent agent 67545 /opt/user-claude/settings.json`; the VM user (uid 1000) can read it (host mode 0600 maps to the VM user) |
| Token in the VM environment | `env \| grep -c ANTHROPIC_AUTH_TOKEN` -> 0 (Claude takes it from `--settings`, not from the exec environment) |
| Real turn | `sbx exec -i -w /tmp/plane-sbx-verify/ws plane-verify-qa claude -p --input-format stream-json --output-format stream-json --verbose --dangerously-skip-permissions --settings /opt/user-claude/settings.json --strict-mcp-config --mcp-config /tmp/plane-sbx-verify/ws/mcp.json` -> rc 0, 7.8 s, `permissionMode=bypassPermissions`, `result/success`, result `pong-from-mcp` |
| Token in host argv | The argv above is the full host argv: no `-e`, no token, no gateway URL |
| Write from inside | `true >> settings.json` -> rc 2; `sudo sh -c 'true >> ...'` -> `Read-only file system`; `sudo touch` -> `Read-only file system`. (The probe opens the file for append and writes no byte, so a failed check could not damage the host file.) |
| Host change, in-place write | Visible at the next exec through the single-file mount and through a directory mount |
| Host change, atomic replace (write a temp file, then rename) | The directory mount shows the new content. The single-file mount fails with `cat: /opt/test/settings.json: Stale file handle` until the sandbox restarts; after `sbx stop` and the next exec it shows the new content |
| Hooks | The hooks in the host settings run in the VM (Q40). Two `SessionEnd` hooks failed with `not found`: one points to `/Users/dale/.config/iterm2/cc-status`, one runs `/Users/dale/.local/bin/node /Users/dale/.claude/hooks/session-heartbeat.cjs` (host paths that are not in the VM, and the kit has no Node.js). The turn still succeeded; hook failures are written to stderr only |

Limit for the Worker: a host tool that rewrites `~/.claude/settings.json` with an atomic replace makes the single-file mount stale while the sandbox runs. `sbx` stops an idle sandbox after 30 s (Q39), and a restart remounts the file, so the problem heals by itself. The Worker health check reads the mounted file (`sbx exec <name> test -r /opt/user-claude/settings.json`) and, when the read fails, runs `sbx stop <name>` and checks again. This keeps the decision (single file at a neutral path) and adds no new mount.

## Criterion 10: Docker MCP gateway

| Case | `system/init` MCP servers | MCP tools |
| --- | --- | --- |
| `--static-mcp none` sandbox, turn with `--strict-mcp-config --mcp-config <one stdio test server>` | `verify-echo` (connected, `dynamic`) only | `mcp__verify-echo__ping` only |
| `--static-mcp none` sandbox, turn without `--strict-mcp-config` | `mcp-gateway` (connected, `user`) | `mcp__mcp-gateway__code-mode`, `mcp__mcp-gateway__mcp-exec` |
| Control sandbox (default create), turn without `--strict-mcp-config` | `mcp-gateway` (connected, `user`) | `code-mode`, `mcp-add`, `mcp-config-set`, `mcp-exec`, `mcp-find` |

- A request from inside: `curl http://mcp-gateway.docker.internal/` -> HTTP 400 (reachable) in both sandboxes; the VM has `MCP_GATEWAY_URL` and `MCP_SENTINEL_TOKEN_NAME` set.
- `sbx policy deny network --sandbox plane-verify-qa mcp-gateway.docker.internal` -> rule added, but the request still gets HTTP 400. The gateway connection does not go through the network policy, so the deny rule has no effect. It is not needed, because with `--strict-mcp-config` the gateway does not show in `system/init`.
- Observation (no decision change): with full permissions, an agent can still send raw HTTP to the gateway endpoint. With `--static-mcp none` the gateway has no servers (`mcp-add`, `mcp-find` and `mcp-config-set` are not offered), so the agent can reach no MCP server through it.

The Worker therefore uses `--static-mcp none` at create and `--strict-mcp-config --mcp-config <file>` on every turn, and adds no gateway deny rule.

## Cleanup record

- Before (`/tmp/plane-sbx-verify/baseline-before.txt`): no sandboxes; global policy not initialized; no secrets; one cached kit image (1.474 GB).
- Created: `plane-verify-qa`, `plane-verify-ctl`, their sandbox rules, global `deny-all`.
- Removed: `sbx rm --force plane-verify-qa plane-verify-ctl` (their rules went with them); `sbx policy reset --force`.
- After: same as before (`diff` shows only a cut-off `sbx secret ls` warning line). The host `~/.claude/settings.json` was mounted read-only and never changed. Throwaway files stay under `/tmp/plane-sbx-verify/`.
