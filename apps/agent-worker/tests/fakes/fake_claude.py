# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Scripted stand-in for the ``claude`` CLI in stream-JSON mode.

It answers with message shapes taken from the recorded transcripts in
``tests/transcripts/claude`` and keeps a session file under
``$HOME/.claude/projects/<working directory name>`` so ``--resume`` works as in
the real CLI. Like the real CLI, it applies the boundary in the ``--settings``
file: a Write in the working directory is denied when an ``Edit`` deny rule
covers it, and a Bash write there fails when the sandbox is on and denies
writes to it. Without that configuration, the write succeeds.
``FAKE_CLAUDE_SCENARIO`` selects a failure:

- ``ok``: every probe step behaves like Claude Code 2.1.289.
- ``not_logged_in``: ``auth status`` reports no login.
- ``no_models``: ``initialize`` reports an empty model list.
- ``no_resume``: ``--resume`` finds no conversation.
- ``no_interrupt``: an ``interrupt`` request is ignored and the turn completes.
- ``crash_not_resumable``: a resumed session that is killed during a turn
  cannot be resumed again.
- ``writes_despite_denial``: the tool named by ``FAKE_CLAUDE_WRITE_TOOL``
  (``Write`` or ``Bash``) writes the file although the boundary denies it.
- ``prompts_for_write``: a Write raises a permission prompt instead of a rule
  denial (the deny rule is not in force).
- ``midturn_replay``: a user message sent during a turn is replayed at once,
  like a CLI that takes input during a turn.
- ``init_after_eof``: ``initialize`` is answered only after stdin closes.
- ``no_initialize_at_connect``: ``initialize`` gets no answer in a Connect
  probe folder; the suite folder (``probes/suite-*``) gets the normal answer.
- ``no_initialize``: ``initialize`` never gets an answer.

``FAKE_CLAUDE_ARGV_LOG``, when set, names a file that gets one JSON line with
the arguments of each call. ``FAKE_CLAUDE_MIDTURN_LOG``, when set, names a file
that gets one JSON line for each user message that arrives during a turn.
"""

import copy
import json
import os
import queue
import re
import sys
import threading
import time
import uuid
from pathlib import Path

TRANSCRIPTS = Path(__file__).resolve().parents[1] / "transcripts" / "claude"
SCENARIO = os.environ.get("FAKE_CLAUDE_SCENARIO", "ok")
VERSION = os.environ.get("FAKE_CLAUDE_VERSION", "2.1.289")
WRITE_TOOL = os.environ.get("FAKE_CLAUDE_WRITE_TOOL", "")
FILE_RULE_DENIAL = "<tool_use_error>File is in a directory that is denied by your permission settings.</tool_use_error>"
COUNT_EVENT_SECONDS = 0.01


def recorded_messages():
    messages = []
    for path in sorted(TRANSCRIPTS.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry["direction"] == "out":
                messages.append(entry["message"])
    return messages


RECORDED = recorded_messages()


def template(predicate):
    for message in RECORDED:
        if predicate(message):
            return copy.deepcopy(message)
    raise LookupError("no recorded message matches")


def is_text_delta(message):
    event = message.get("event") or {}
    return message.get("type") == "stream_event" and (event.get("delta") or {}).get("type") == "text_delta"


def is_text_assistant(message):
    content = (message.get("message") or {}).get("content") or []
    return message.get("type") == "assistant" and any(block.get("type") == "text" for block in content)


INIT_RESPONSE = template(
    lambda m: m.get("type") == "control_response" and "models" in m["response"].get("response", {})
)
SYSTEM_INIT = template(lambda m: m.get("type") == "system" and m.get("subtype") == "init")
TEXT_DELTA = template(is_text_delta)
TEXT_ASSISTANT = template(is_text_assistant)
RESULT_SUCCESS = template(lambda m: m.get("type") == "result" and m.get("subtype") == "success")
RESULT_INTERRUPTED = template(lambda m: m.get("type") == "result" and m.get("subtype") == "error_during_execution")
PERMISSION_REQUEST = template(
    lambda m: m.get("type") == "control_request" and m["request"].get("subtype") == "can_use_tool"
)
INTERRUPT_RESPONSE = template(
    lambda m: m.get("type") == "control_response" and "still_queued" in m["response"].get("response", {})
)
REPLAY = template(lambda m: m.get("type") == "user" and m.get("isReplay"))


def emit(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


class Session:
    def __init__(self, cwd, resume):
        projects = Path(os.environ["HOME"]) / ".claude" / "projects"
        self.directory = projects / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd))
        self.id = resume or str(uuid.uuid4())
        self.cwd = cwd

    @property
    def path(self):
        return self.directory / f"{self.id}.jsonl"

    def exists(self):
        return self.path.exists() and SCENARIO != "no_resume"

    def remember(self, **values):
        self.directory.mkdir(parents=True, exist_ok=True)
        state = self.state()
        state.update(values)
        self.path.write_text(json.dumps(state))

    def state(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    @property
    def crash_marker(self):
        return self.directory / f"{self.id}.crashed"


def load_settings(args):
    if "--settings" not in args:
        return {}
    return json.loads(Path(args[args.index("--settings") + 1]).read_text())


def edit_denied(settings, cwd):
    rule = f"Edit(/{os.path.realpath(cwd)}/**)"
    return rule in ((settings.get("permissions") or {}).get("deny") or [])


def sandbox_denies_write(settings, cwd):
    sandbox = settings.get("sandbox") or {}
    deny_write = (sandbox.get("filesystem") or {}).get("denyWrite") or []
    return sandbox.get("enabled") is True and os.path.realpath(cwd) in deny_write


class FakeClaude:
    def __init__(self, args):
        self.args = args
        self.replay = "--replay-user-messages" in args
        self.inbox = queue.Queue()
        self.pending_users = []
        resume = args[args.index("--resume") + 1] if "--resume" in args else None
        self.resumed = resume is not None
        self.session = Session(os.getcwd(), resume)
        self.settings = load_settings(args)
        self.denials = []

    def read_stdin(self):
        for line in sys.stdin:
            try:
                self.inbox.put(json.loads(line))
            except ValueError:
                continue
        self.inbox.put(None)

    def next_input(self):
        if self.pending_users:
            return self.pending_users.pop(0)
        return self.inbox.get()

    # Output helpers -------------------------------------------------------------

    def system_init(self):
        message = copy.deepcopy(SYSTEM_INIT)
        message.update(session_id=self.session.id, cwd=self.session.cwd)
        emit(message)

    def text_delta(self, text):
        message = copy.deepcopy(TEXT_DELTA)
        message["event"]["delta"]["text"] = text
        message["session_id"] = self.session.id
        emit(message)

    def assistant(self, text):
        message = copy.deepcopy(TEXT_ASSISTANT)
        message["message"]["content"] = [{"type": "text", "text": text}]
        message["session_id"] = self.session.id
        emit(message)

    def result(self, text):
        message = copy.deepcopy(RESULT_SUCCESS)
        message.update(result=text, session_id=self.session.id, is_error=False, permission_denials=self.denials)
        self.denials = []
        emit(message)

    def tool_use(self, name, tool_input):
        tool_id = f"toolu_{uuid.uuid4().hex[:24]}"
        message = copy.deepcopy(TEXT_ASSISTANT)
        message["message"]["content"] = [{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}]
        message["session_id"] = self.session.id
        emit(message)
        return tool_id

    def tool_result(self, tool_id, content, is_error):
        emit(
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "content": content, "is_error": is_error, "tool_use_id": tool_id}
                    ],
                },
                "parent_tool_use_id": None,
                "session_id": self.session.id,
                "uuid": str(uuid.uuid4()),
            }
        )

    # Turns --------------------------------------------------------------------

    def answer(self, text):
        self.text_delta(text)
        self.assistant(text)
        self.result(text)

    def turn(self, message):
        text = (message.get("message") or {}).get("content") or ""
        self.session.remember(last_prompt=text)
        if self.replay:
            replay = copy.deepcopy(REPLAY)
            replay.update(uuid=message.get("uuid"), session_id=self.session.id)
            replay["message"] = message["message"]
            emit(replay)
        self.system_init()
        remember = re.search(r"Remember the code word (\S+)\.", text)
        write = re.search(r"Write tool to create the file (\S+)", text)
        bash = re.search(r"Bash tool to run this command: echo probe > (\S+)", text)
        if remember:
            self.session.remember(code_word=remember.group(1))
            self.answer("READY")
        elif write:
            self.write_turn(write.group(1))
        elif bash:
            self.bash_turn(bash.group(1))
        elif text.startswith("Count from 1 to"):
            self.count_turn()
        elif text.startswith("What code word"):
            self.answer(self.session.state().get("code_word", "I do not know."))
        elif "NEXT" in text:
            self.answer("NEXT")
        else:
            self.answer("OK")

    def forced_write(self, tool):
        return SCENARIO == "writes_despite_denial" and WRITE_TOOL == tool

    def write_turn(self, name):
        target = Path(self.session.cwd, name)
        tool_input = {"file_path": str(target), "content": "probe"}
        tool_id = self.tool_use("Write", tool_input)
        if SCENARIO == "prompts_for_write":
            if self.ask_permission("Write", tool_input):
                target.write_text("probe")
                self.tool_result(tool_id, f"File created successfully at: {target}", False)
            else:
                self.tool_result(tool_id, "The user denied this action.", True)
                self.denials.append({"tool_name": "Write", "tool_use_id": tool_id, "tool_input": tool_input})
        elif edit_denied(self.settings, self.session.cwd) and not self.forced_write("Write"):
            self.tool_result(tool_id, FILE_RULE_DENIAL, True)
            self.denials.append({"tool_name": "Write", "tool_use_id": tool_id, "tool_input": tool_input})
        else:
            target.write_text("probe")
            self.tool_result(tool_id, f"File created successfully at: {target}", False)
        self.answer("Done.")

    def bash_turn(self, name):
        tool_id = self.tool_use("Bash", {"command": f"echo probe > {name}", "description": "Write the probe file"})
        if sandbox_denies_write(self.settings, self.session.cwd) and not self.forced_write("Bash"):
            self.tool_result(tool_id, f"Exit code 1\n(eval):1: operation not permitted: {name}", True)
        else:
            Path(self.session.cwd, name).write_text("probe\n")
            self.tool_result(tool_id, "", False)
        self.answer("Done.")

    def ask_permission(self, tool, tool_input):
        """Send a permission prompt and wait for its answer. Returns True when the host allows the action."""
        request = copy.deepcopy(PERMISSION_REQUEST)
        request["request_id"] = str(uuid.uuid4())
        request["request"]["tool_name"] = tool
        request["request"]["input"] = tool_input
        emit(request)
        while True:
            reply = self.inbox.get()
            if reply is None:
                return False
            if reply.get("type") == "control_response" and reply["response"].get("request_id") == request["request_id"]:
                return reply["response"]["response"].get("behavior") == "allow"
            self.pending_users.append(reply)

    def count_turn(self):
        if self.resumed and SCENARIO == "crash_not_resumable":
            self.session.crash_marker.write_text("crashed")
        for number in range(1, 401):
            try:
                message = self.inbox.get_nowait()
            except queue.Empty:
                message = None
            if message is not None:
                request = message.get("request") or {}
                is_interrupt = message.get("type") == "control_request" and request.get("subtype") == "interrupt"
                if is_interrupt and SCENARIO == "no_interrupt":
                    continue
                if is_interrupt:
                    response = copy.deepcopy(INTERRUPT_RESPONSE)
                    response["response"]["request_id"] = message.get("request_id")
                    emit(response)
                    interrupted = copy.deepcopy(RESULT_INTERRUPTED)
                    interrupted["session_id"] = self.session.id
                    emit(interrupted)
                    return
                if message.get("type") == "user" and os.environ.get("FAKE_CLAUDE_MIDTURN_LOG"):
                    with open(os.environ["FAKE_CLAUDE_MIDTURN_LOG"], "a", encoding="utf-8") as handle:
                        handle.write(json.dumps(message) + "\n")
                if message.get("type") == "user" and SCENARIO == "midturn_replay":
                    replay = copy.deepcopy(REPLAY)
                    replay.update(uuid=message.get("uuid"), session_id=self.session.id)
                    replay["message"] = message["message"]
                    emit(replay)
                else:
                    # Like Claude Code 2.1.289, a message sent during a turn waits for the next turn.
                    self.pending_users.append(message)
            self.text_delta(f"{number}\n")
            time.sleep(COUNT_EVENT_SECONDS)
        self.assistant("400")
        self.result("400")

    def initialize_unanswered(self):
        in_suite = "/probes/suite-" in os.path.realpath(self.session.cwd)
        return SCENARIO == "no_initialize" or (SCENARIO == "no_initialize_at_connect" and not in_suite)

    def run(self):
        lost = SCENARIO == "crash_not_resumable" and self.session.crash_marker.exists()
        if "--resume" in self.args and (not self.session.exists() or lost):
            print(f"No conversation found with session ID: {self.session.id}", file=sys.stderr)
            return 1
        threading.Thread(target=self.read_stdin, daemon=True).start()
        while True:
            message = self.next_input()
            if message is None:
                return 0
            kind = message.get("type")
            if kind == "control_request" and (message.get("request") or {}).get("subtype") == "initialize":
                if self.initialize_unanswered():
                    continue
                if SCENARIO == "init_after_eof":
                    while self.inbox.get() is not None:
                        pass
                response = copy.deepcopy(INIT_RESPONSE)
                response["response"]["request_id"] = message.get("request_id")
                if SCENARIO == "no_models":
                    response["response"]["response"]["models"] = []
                emit(response)
                if SCENARIO == "init_after_eof":
                    return 0
            elif kind == "user":
                self.turn(message)


def main(args):
    if os.environ.get("FAKE_CLAUDE_ARGV_LOG"):
        with open(os.environ["FAKE_CLAUDE_ARGV_LOG"], "a", encoding="utf-8") as handle:
            handle.write(json.dumps(args) + "\n")
    if args[:1] == ["--version"]:
        print(f"{VERSION} (Claude Code)")
        return 0
    if args[:2] == ["auth", "status"]:
        projects = str(Path(os.environ["HOME"]) / ".claude" / "projects")
        print(json.dumps({"loggedIn": SCENARIO != "not_logged_in", "projectsDirectory": projects}))
        return 0
    return FakeClaude(args).run()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
