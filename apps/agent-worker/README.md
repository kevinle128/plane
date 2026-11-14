# Plane Agent Worker

The Worker runs on the Mac Mini, next to the local CLI Harnesses. It polls the
Plane API on localhost, runs Harness connection probes, and (in later releases)
Q&A Runs and Code jobs. It runs natively, not in Docker, because it needs the
installed CLIs and their macOS sandboxes.

## Setup

1. Create a Worker token on the Plane API host. The command writes the token to a
   new file with mode `0600` and never prints it:

   ```bash
   cd apps/api
   uv run python manage.py create_agent_worker --name mini --token-file ~/.config/plane-agent-worker/token
   ```

2. Install the Worker environment (uv `0.12.21`, Python 3.12):

   ```bash
   cd apps/agent-worker
   uv sync
   ```

3. Start the Worker:

   ```bash
   export PLANE_AGENT_WORKER_API_ORIGIN=http://localhost:8000
   export PLANE_AGENT_WORKER_TOKEN_FILE=~/.config/plane-agent-worker/token
   export PLANE_AGENT_WORKER_RUN_ROOT=/srv/agents/runs
   uv run python -m plane_agent_worker run
   ```

| Variable                            | Required | Rule                                                                                       |
| ----------------------------------- | -------- | ------------------------------------------------------------------------------------------ |
| `PLANE_AGENT_WORKER_API_ORIGIN`     | yes      | `http` or `https` origin on `localhost`, `127.0.0.1` or `[::1]`, without path or user info |
| `PLANE_AGENT_WORKER_TOKEN_FILE`     | yes      | Absolute path, regular file, mode `0600`, owned by the Worker user, outside the Run root   |
| `PLANE_AGENT_WORKER_RUN_ROOT`       | yes      | Absolute path, mode `0700`, outside the Plane checkout                                     |
| `PLANE_AGENT_WORKER_PLANE_CHECKOUT` | no       | The Plane checkout; found automatically when the Worker runs from it                       |
| `PLANE_AGENT_WORKER_CLAUDE_BIN`     | no       | Path of the `claude` command; default is `claude` on `PATH`                                |
| `PLANE_AGENT_WORKER_POLL_SECONDS`   | no       | Poll interval, 1 to 60 seconds (default 2)                                                 |

Keep the Run root path short (under about 150 characters): Claude Code names its
session directory after the working directory, and it shortens long names.

## Security rules

- The token goes only in `Authorization: Bearer`, never in `X-Api-Key`.
- The client follows no redirect and uses no proxy.
- Harness processes get an allowlisted environment (no Worker variables, no
  outer agent session variables) and a private temporary directory.
- Claude Code (user decision Q16) runs with its built-in sandbox and permission
  rules, from a settings file that the Worker writes next to the working
  directory (`claude-settings.json`, mode `0600`) and passes with `--settings`
  and `--setting-sources ""`, so the user's own `~/.claude` settings cannot
  widen it. See `plane_agent_worker/drivers/claude_boundary.py`:
  - Bash runs in the sandbox, which must start and cannot be bypassed. It cannot
    write in the working directory or elsewhere on the Host (the one exception
    is Claude Code's per-user temporary directory, which the Bash tool needs),
    and cannot read other Runs, the token file, the Plane checkout, the Claude
    configuration directory (sessions, credentials) or the usual credential stores.
  - Edit, Write and NotebookEdit are denied by a permission rule; Read and the
    other file tools work only inside the working directory (`--restricted`).
  - Hooks, MCP servers, plugins and slash commands are off.
  - The `claude` process itself is outside the sandbox, so it keeps its session
    history and `--resume` works. It can also create a `.claude` folder in the
    working directory for its own records.
- Each Harness process group is recorded under `<run root>/.processes`, with the
  Claude session folder of the probe. At start the Worker stops the groups a
  previous Worker left behind, removes those session folders and removes every
  folder under `<run root>/probes`.

## Connection probe

`uv run python -m plane_agent_worker probe` runs one local probe without Plane
and prints the report. Claude Code is Connected only when all seven checks pass:
authentication, model report, resumed follow-up, progress events, interruption,
permission enforcement and recovery after a crash. Permission enforcement needs
both denials: a Write in the working directory denied by the permission rule
(no approval prompt), and a Bash write there denied by the built-in sandbox.

The probe budget is 100 seconds or the time left before Plane's answer
deadline, whichever is shorter. While a probe runs, the Worker asks Plane every
5 seconds whether the probe is still current; it stops a probe that a new
Connect or a Disconnect replaced, and does not report it.

## Tests

```bash
uv run pytest -m "not native and not docker"   # unit tests, any OS
uv run pytest -m native                        # real Claude probe with the built-in sandbox, on the Mini
uv run ruff check . && uv run ruff format --check .
```

The Claude driver tests use `tests/fakes/fake_claude.py`, which answers with the
message shapes recorded in `tests/transcripts/claude` (see the README there).
