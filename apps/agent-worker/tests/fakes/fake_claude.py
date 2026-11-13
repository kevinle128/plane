# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Scripted stand-in for the ``claude`` CLI in stream-JSON mode.

It answers with message shapes taken from the recorded transcripts in
``tests/transcripts/claude`` and keeps a session file under
``$HOME/.claude/projects/<working directory name>`` so ``--resume`` works as in
the real CLI. ``FAKE_CLAUDE_SCENARIO`` selects a failure:

- ``ok``: every probe step behaves like Claude Code 2.1.289.
- ``no_permission_prompt``: a Write runs without a permission prompt.
- ``not_logged_in``: ``auth status`` reports no login.
- ``no_models``: ``initialize`` reports an empty model list.
- ``no_resume``: ``--resume`` finds no conversation.
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


class FakeClaude:
    def __init__(self, args):
        self.args = args
        self.replay = "--replay-user-messages" in args
        self.inbox = queue.Queue()
        self.pending_users = []
        resume = args[args.index("--resume") + 1] if "--resume" in args else None
        self.session = Session(os.getcwd(), resume)

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
        message.update(result=text, session_id=self.session.id, is_error=False)
        emit(message)

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
        write = re.search(r"create the file (\S+)", text)
        if remember:
            self.session.remember(code_word=remember.group(1))
            self.answer("READY")
        elif write:
            self.write_turn(write.group(1))
        elif text.startswith("Count from 1 to"):
            self.count_turn()
        elif text.startswith("What code word"):
            self.answer(self.session.state().get("code_word", "I do not know."))
        elif "NEXT" in text:
            self.answer("NEXT")
        else:
            self.answer("OK")

    def write_turn(self, name):
        if SCENARIO == "no_permission_prompt":
            Path(self.session.cwd, name).write_text("probe")
            self.answer("Created the file.")
            return
        request = copy.deepcopy(PERMISSION_REQUEST)
        request["request_id"] = str(uuid.uuid4())
        request["request"]["input"] = {"file_path": str(Path(self.session.cwd, name)), "content": "probe"}
        emit(request)
        while True:
            reply = self.inbox.get()
            if reply is None:
                return
            if reply.get("type") == "control_response" and reply["response"].get("request_id") == request["request_id"]:
                break
            self.pending_users.append(reply)
        if reply["response"]["response"].get("behavior") == "allow":
            Path(self.session.cwd, name).write_text("probe")
            self.answer("Created the file.")
        else:
            self.answer("The write was denied.")

    def count_turn(self):
        for number in range(1, 401):
            try:
                message = self.inbox.get_nowait()
            except queue.Empty:
                message = None
            if message is not None:
                request = message.get("request") or {}
                if message.get("type") == "control_request" and request.get("subtype") == "interrupt":
                    response = copy.deepcopy(INTERRUPT_RESPONSE)
                    response["response"]["request_id"] = message.get("request_id")
                    emit(response)
                    interrupted = copy.deepcopy(RESULT_INTERRUPTED)
                    interrupted["session_id"] = self.session.id
                    emit(interrupted)
                    return
                # Like Claude Code 2.1.289, a message sent during a turn waits for the next turn.
                self.pending_users.append(message)
            self.text_delta(f"{number}\n")
            time.sleep(COUNT_EVENT_SECONDS)
        self.assistant("400")
        self.result("400")

    def run(self):
        if "--resume" in self.args and not self.session.exists():
            print(f"No conversation found with session ID: {self.session.id}", file=sys.stderr)
            return 1
        threading.Thread(target=self.read_stdin, daemon=True).start()
        while True:
            message = self.next_input()
            if message is None:
                return 0
            kind = message.get("type")
            if kind == "control_request" and (message.get("request") or {}).get("subtype") == "initialize":
                response = copy.deepcopy(INIT_RESPONSE)
                response["response"]["request_id"] = message.get("request_id")
                if SCENARIO == "no_models":
                    response["response"]["response"]["models"] = []
                emit(response)
            elif kind == "user":
                self.turn(message)


def main(args):
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
