# Plane Agent Worker

The Worker runs on the Mac Mini. It polls the Plane API on localhost and runs
Harness connection probes and Q&A Runs. The Worker itself runs natively on the
host (it holds the Worker token and the Git credentials); it runs every agent CLI
inside a Docker Sandbox microVM through the standalone `sbx` CLI.

## Setup

1. Install Docker Sandboxes and sign in, in the Worker user's login session
   (Apple silicon, macOS 14 or later). Values come from stdin, never from the
   command line:

   ```bash
   brew trust docker/tap && brew install docker/tap/sbx
   echo "$DOCKER_PAT" | sbx login --username <docker-id> --password-stdin   # a PAT with Read scope
   sbx diagnose
   sbx policy init deny-all
   # Pull the kit image once (about 50 s, 1.5 GB):
   mkdir -p ~/sbx-warmup && sbx --no-input create --name warmup claude ~/sbx-warmup && sbx rm --force warmup
   ```

   Never run `sbx setup`, `sbx secret import` or `sbx reset`: the first two store
   host secrets globally, and `reset` deletes all secrets.

2. Configure Claude Code on the host once. Each sandbox mounts the host
   `~/.claude/settings.json` read-only and passes it with `--settings`, so its
   `env` (for example `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN` of a
   gateway) applies inside the sandbox. The Worker reads only
   `env.ANTHROPIC_BASE_URL` from that file, to allow the gateway host in the
   sandbox network policy. The Worker config holds no gateway URL or token.

3. Create a Worker token on the Plane API host. The command writes the token to a
   new file with mode `0600` and never prints it:

   ```bash
   cd apps/api
   uv run python manage.py create_agent_worker --name mini --token-file ~/.config/plane-agent-worker/token
   ```

4. Install the Worker environment (uv `0.12.21`, Python 3.12):

   ```bash
   cd apps/agent-worker
   uv sync
   ```

5. Start the Worker:

   ```bash
   export PLANE_AGENT_WORKER_API_ORIGIN=http://localhost:8000
   export PLANE_AGENT_WORKER_TOKEN_FILE=~/.config/plane-agent-worker/token
   export PLANE_AGENT_WORKER_RUN_ROOT=/srv/agents/runs
   uv run python -m plane_agent_worker run
   ```

| Variable                            | Required | Rule                                                                                       |
| ----------------------------------- | -------- | ------------------------------------------------------------------------------------------ |
| `HOME`                              | yes      | The Worker user's home directory; `~/.claude/settings.json` must exist there               |
| `PLANE_AGENT_WORKER_API_ORIGIN`     | yes      | `http` or `https` origin on `localhost`, `127.0.0.1` or `[::1]`, without path or user info |
| `PLANE_AGENT_WORKER_TOKEN_FILE`     | yes      | Absolute path, regular file, mode `0600`, owned by the Worker user, outside the Run root   |
| `PLANE_AGENT_WORKER_RUN_ROOT`       | yes      | Absolute path, mode `0700`, outside the Plane checkout                                     |
| `PLANE_AGENT_WORKER_PLANE_CHECKOUT` | no       | The Plane checkout; found automatically when the Worker runs from it                       |
| `PLANE_AGENT_WORKER_SBX_BIN`        | no       | Path of the `sbx` command; default is `sbx` on `PATH`                                      |
| `PLANE_AGENT_SANDBOX_MEMORY`        | no       | Memory of each sandbox, for example `8g` (default: the `sbx` default)                      |
| `PLANE_AGENT_WORKER_POLL_SECONDS`   | no       | Poll interval, 1 to 60 seconds (default 2)                                                 |

## Security rules

- The token goes only in `Authorization: Bearer`, never in `X-Api-Key`.
- The client follows no redirect and uses no proxy.
- Every Claude process runs inside a sandbox with full permissions
  (`--dangerously-skip-permissions`). The sandbox microVM and its mounts are the
  boundary (`plane_agent_worker/sandbox.py`):
  - The primary mount (the sandbox's scratch folder under the Run root) is
    writable. Every other mount is read-only: a write fails, also with `sudo`.
  - Host files outside the mounts do not exist in the VM: the Worker token, the
    Plane checkout, other sandboxes' folders and the rest of `~/.claude`.
  - Read-only user config: `~/.claude/settings.json` at
    `/opt/user-claude/settings.json`, `~/.claude/hooks` at its host path (hook
    commands name absolute host paths), and the skills (`~/.claude/skills`,
    `~/.agents/skills` and every folder a skill link points to). A hook stored
    outside `~/.claude/hooks`, or a hook that needs Node.js, fails in the VM
    (the `claude` kit has no Node.js); Claude continues.
  - Network: `deny-all`, plus a per-sandbox allow rule for the gateway host and
    a deny rule for the allow list of the `claude` kit. The Docker MCP gateway
    gets no servers (`--static-mcp none`) and Claude loads no MCP config but the
    one the Worker passes (`--strict-mcp-config`).
  - The gateway token is in the mounted settings file, so the agent can read it
    inside the VM (accepted). It never appears in a host argv or a Worker log.
- No host environment variable reaches the VM. The Worker does not set
  `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`: with it, Claude Code leaves bypass mode
  and asks before each command.
- A signal to the host `sbx exec` client does not stop the process inside. Each
  Claude process writes its PID to a pidfile in the scratch folder, and the
  Worker stops it with `kill` of that PID through a second `sbx exec`. Never use
  a broad kill inside a sandbox: killing its keep-alive process stops it.
- `sbx` stops an idle sandbox 30 s after its last command; the next use starts it
  again (about 2 s). The health check before each use reads the mounted settings
  file. When a host tool replaces `~/.claude/settings.json` (write and rename),
  the single-file mount goes stale until the sandbox restarts, so a failed read
  stops the sandbox once and checks again.
- Each host `sbx exec` client is recorded under `<run root>/.processes`. At start
  the Worker stops the clients a previous Worker left behind and removes the
  probe folders in the probe sandbox's scratch folder.

## Connection probe

`uv run python -m plane_agent_worker probe` runs one local probe without Plane
and prints the report. Claude Code is Connected only when all seven checks pass:
authentication, model report, resumed follow-up, progress events, interruption,
permissions and recovery after a crash. The permission check proves that Claude
runs in `bypassPermissions` mode and runs a Bash write in its scratch folder
without a permission request.

Each Connect or Retry runs a quick check: `sbx` is installed and signed in
(otherwise the missing action is "Sign in to Docker with `sbx login` on the
Worker machine"), the probe sandbox `plane-probe-claude-code` exists (created on
first use, about 6 s), then inside it `claude --version`, `claude auth status`
and the model list. The other checks come from the behavior suite, which runs
once for each Claude Code version in the sandbox and gives the report its `suite`
record. The probe budget is 100 seconds or the time left before Plane's answer
deadline, whichever is shorter. While a probe runs, the Worker asks Plane every 5
seconds whether the probe is still current; it stops a probe that a new Connect
or a Disconnect replaced, and does not report it.

### Behavior suite cache

- File: `<run root>/state/conformance.json`, mode `0600`, in a `0700` folder.
  Only the Worker writes it; it is outside every sandbox mount.
- Key: Harness, CLI version and suite version (`SUITE_VERSION` in the driver).
  The Worker stores only a suite that passed. A failed suite is not stored, so
  the next Connect or Retry runs it again.
- A new CLI version (for example after a Claude Code auto-update) has no record,
  so the next Connect runs the suite. One suite runs at a time for each Harness
  and version; other callers wait for its result.
- To force the suite on the installed version, stop the Worker, delete the file,
  start the Worker, then select Retry:

  ```bash
  rm "$PLANE_AGENT_WORKER_RUN_ROOT/state/conformance.json"
  ```

  Do this when you think the CLI behavior changed without a version change.

## Deployment assumption: trusted network only

The Worker has no workspace allowlist, and Plane does not limit how often
Connect or Retry runs. Any workspace admin of the instance can make the Worker
use the Claude Code login of the Mini. This is accepted only while the instance
is reachable through Tailscale, so only trusted people can sign up and create
workspaces. Before the instance is exposed outside Tailscale, add an instance
workspace allowlist that Connect and the probe claim both check, and a Connect
limit for each workspace.

## Tests

```bash
uv run pytest -m "not native and not docker"   # unit tests, any OS
uv run pytest -m native                        # real Claude in a real sandbox (signed in to sbx, deny-all); removes its plane-test-* sandboxes
uv run ruff check . && uv run ruff format --check .
```

The Claude driver tests use `tests/fakes/fake_claude.py`, which answers with the
message shapes recorded in `tests/transcripts/claude` (see the README there).
