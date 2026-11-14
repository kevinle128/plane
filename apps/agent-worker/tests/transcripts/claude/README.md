# Claude Code probe transcripts

Recorded from a native probe of Claude Code 2.1.289 with its built-in sandbox
and the Worker permission rules:

```bash
python -m plane_agent_worker probe --record tests/transcripts/claude
```

Each line is `{"direction": "in" | "out", "message": <stream-JSON message>}`.
The recorder drops account data, signatures, usage, cost and machine listings,
and replaces the home directory and the Run root with `<home>` and `<run_root>`.
`tests/fakes/fake_claude.py` builds its answers from these message shapes. The
tool-use, tool-result and `permission_denials` shapes of the permission turns
follow the same recording.
Record again when the supported Claude Code version changes.

The recording is older than two driver changes, and the fake follows the
current driver:

- `session-a.jsonl` sends a queued user message during the counting turn,
  before `interrupt`. The driver no longer does this: it interrupts the turn
  and then sends the next message as a new turn, and reports `midturn_input`
  as false. The out messages that the fake uses keep the same shapes.
- `session-a.jsonl` has a permission prompt for the Write and no Bash turn
  (it is from the outer-sandbox boundary). The fake builds the rule-denial and
  sandbox-denial answers from the tool-use and tool-result shapes of the
  recording, and uses the prompt shape only for the `prompts_for_write` case.
