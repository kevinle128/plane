# Phase 3 implementation report: Claude Q&A Run and durable timeline

Branch `feat/local-cli-agents-phase-3` (worktree `plane-worktrees/local-cli-agents-phase-3`), from `origin/preview` with Phases 1 and 2 merged. Tracking issue kevinle128/plane#1. Dates in Asia/Saigon.

## Task 0: `sbx` verification (criteria 9 and 10)

Report: [sbx-verification.md](./sbx-verification.md). Criterion 9 PASS with one limit, criterion 10 PASS. No decision changed.

- 9: the host `~/.claude/settings.json` mounted read-only at `/opt/user-claude/settings.json` and passed with `claude --settings` authenticates a real turn through the gateway; there is no token in the host argv and no `-e`; writes fail. Limit: an atomic replace of the host file makes the single-file mount stale (`Stale file handle`) until the sandbox restarts.
- 10: `--static-mcp none` plus `--strict-mcp-config --mcp-config <file>` lists only the given server. Without the strict flag, the gateway shows. The gateway endpoint stays reachable by raw HTTP (HTTP 400), and a `sbx policy deny` rule does not block it.
- Extra check before the driver change: `sbx exec <probe> claude --settings /opt/user-claude/settings.json auth status` gives `loggedIn: true` (without `--settings`: `false`). Claude Code in the kit: 2.1.325.

## Baselines (Tests Before)

| #   | Check                                                              | Result on the branch head before any Phase 3 code |
| --- | ------------------------------------------------------------------ | ------------------------------------------------- |
| 5   | Worker unit suite (`uv run pytest -m "not native and not docker"`) | 110 passed                                        |

## Stories

### Claude probe and suite move into a Docker Sandbox (changes to Phase 2 code)

- New: `plane_agent_worker/sandbox.py` (create with `--static-mcp none`, read-only user config and skill mounts, gateway allow rule from `env.ANTHROPIC_BASE_URL`, kit deny rule, health check with the stale-mount stop, pidfile exec and kill), `tests/fakes/fake_sbx.py`, `tests/test_sandbox.py` (18 tests).
- Changed: the Claude driver runs every process through `sbx exec` in `plane-probe-claude-code` with `--dangerously-skip-permissions --settings /opt/user-claude/settings.json --strict-mcp-config`; the permission check now asserts `bypassPermissions` in `system/init` and a Bash write without a permission request; `SUITE_VERSION` 2 -> 3 (fingerprint pinned); probe folders live in the probe sandbox scratch; `StreamSession.kill` kills the pidfile inside the sandbox first; config reads `PLANE_AGENT_WORKER_SBX_BIN` and `PLANE_AGENT_SANDBOX_MEMORY` and requires the host `~/.claude/settings.json`. Deleted: `drivers/claude_boundary.py` and its boundary tests (settings file, deny rules, Bash sandbox, user-settings override).
- Test first: `sandbox.py` was written before `tests/test_sandbox.py` (not test-first). The driver and config tests were changed first: `test_claude_probe.py` + `test_config.py` + `test_suite_cache.py` failed (config: 7 failed; fingerprint: 1 failed; probe: every sandbox test failed on the old driver signature), then passed after the change.
- Green: Worker unit `133 passed, 1 deselected` (was 110 before the change); ruff check and format clean. Native (real `sbx` v0.53.0, Claude Code 2.1.325 in the kit, `deny-all`): `test_real_claude_probe_in_a_sandbox_passes_and_a_second_probe_uses_the_cached_suite` -> 1 passed in 67 s (two Connects; the second uses the cached suite). The test removes its `plane-test-probe-claude-code` sandbox; `sbx ls` before and after: none.
- Finding (live): `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` in the sandbox makes Claude Code 2.1.325 report `permissionMode: default` although `--dangerously-skip-permissions` (also with `--permission-mode bypassPermissions`) is given, and a Bash write then needs a permission answer (`Tool permission request failed`). Without the variable: `bypassPermissions`, no prompt. See deviation 3.

## Deviations

1. Health check of a sandbox reads the mounted settings file (`sbx exec <name> sh -c 'test -r /opt/user-claude/settings.json'`). Exit 1 means a stale single-file mount: the Worker runs `sbx stop <name>` and checks once more. This branch is not in the phase file. It keeps the single-file decision (Q37) and heals the stale mount found in task 0.
2. `~/.claude/hooks` is mounted read-only at its host path (not at a neutral path), because hook commands in the host settings use absolute host paths (task 0: `/Users/dale/.claude/hooks/...`). Hooks outside `~/.claude/hooks` and hooks that need Node.js fail in the kit (accepted by Q40).

3. The sandbox environment is empty: the Worker does not pass `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` (the phase file's "Changes to Phase 2 code" says the sandbox environment is only that variable). Reason: with it Claude leaves bypass mode, which breaks Q31 (full permissions) and the suite's permission check (bypass mode, no permission request). The scrub would protect nothing in the sandbox, because the agent can read the mounted settings file that holds the token (Q30 and Q37 accept that the token is visible inside the sandbox). Needs user confirmation; see Concerns.

## Not done

(Filled at the end.)
