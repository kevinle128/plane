# Claude Code probe transcripts

Recorded on 2026-11-14 from a native probe of Claude Code 2.1.289, run as it is
installed on the Mini (its own settings, login, hooks and MCP servers), with the
Worker boundary settings on top (built-in sandbox, bare-name deny rules for the
file tools, credential scrub):

```bash
env -i HOME="$HOME" USER="$USER" LOGNAME="$USER" PATH="$PATH" LANG=en_US.UTF-8 \
  PLANE_AGENT_WORKER_API_ORIGIN=http://localhost:8000 \
  PLANE_AGENT_WORKER_TOKEN_FILE=<token file> PLANE_AGENT_WORKER_RUN_ROOT=<run root> \
  uv run python -m plane_agent_worker probe --record tests/transcripts/claude
```

Each line is `{"direction": "in" | "out", "message": <stream-JSON message>}`.
The recorder drops account data, signatures, usage, cost and machine listings
(including the tool list of the `init` message, which names the user's MCP
tools), and replaces the home directory and the Run root with `<home>` and
`<run_root>`. `tests/fakes/fake_claude.py` builds its answers from these message
shapes; it sets the tool list of its `init` message itself.

In `session-a.jsonl`, Claude Code asks for permission before the Bash write to
the working directory (a path the sandbox denies). The Worker allows that call,
and the sandbox denies the write (`operation not permitted`).

Record again when the supported Claude Code version changes, and check that the
recording holds no account data or local paths before you commit it.
