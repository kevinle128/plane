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
