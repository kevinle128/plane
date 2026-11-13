# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Claude Code driver: connection probe over the stream-JSON control protocol.

Every Claude process runs under the macOS read-only boundary with safe mode,
restricted mode and strict MCP settings, so user hooks, plugins, settings files
and MCP servers do not run inside a probe. Permission prompts come to the Worker
over stdio (``--permission-prompt-tool stdio``) and the Worker denies them.

Probe steps (verified with Claude Code 2.1.289):
1. ``--version`` and ``auth status`` (JSON).
2. A metadata session: ``initialize`` returns the model list. No prompt is sent.
3. Session A: a turn with partial-message events (progress), a Write request
   that must raise a permission prompt and stay unwritten (permission), and a long
   turn that receives a queued message and then ``interrupt`` (interruption and the
   midturn input flag).
4. Session B resumes the session and recalls a code word (follow-up, native resume).
5. Session C resumes, is killed during a turn; session D resumes and recalls the
   code word again (recovery).
"""

import json
import os
import queue
import re
import secrets
import shutil
import signal
import subprocess
import threading
import uuid
from pathlib import Path

from plane_agent_worker.drivers.base import (
    MAX_HINT_CHARS,
    ProbeOutcome,
    ProbeTimeout,
    bounded,
)
from plane_agent_worker.sandbox_macos import SandboxPaths

HARNESS = "claude_code"
SUPPORTED_MAJOR_VERSION = 2
VERSION_PATTERN = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)")
MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:\[\]/-]{0,127}$")
MAX_MODELS = 50
MAX_LINE_CHARS = 2_000_000
COMMAND_TIMEOUT_SECONDS = 20
TURN_TIMEOUT_SECONDS = 45
# The probe uses the fastest reported model when one of these is present.
PROBE_MODEL_PREFERENCE = ("haiku",)

SESSION_FLAGS = (
    "-p",
    "--input-format",
    "stream-json",
    "--output-format",
    "stream-json",
    "--verbose",
    "--include-partial-messages",
    "--replay-user-messages",
    "--safe-mode",
    "--restricted",
    "--strict-mcp-config",
    "--disable-slash-commands",
    "--permission-prompt-tool",
    "stdio",
)

# Only these variables reach the Harness. The Worker token file path, outer agent
# session variables and unrelated credentials never do.
ENV_ALLOWLIST = (
    "HOME",
    "USER",
    "LOGNAME",
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TERM",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CONFIG_DIR",
)

WRITE_PROBE_FILE = "plane-permission-probe.txt"
COUNT_PROMPT = "Count from 1 to 400, one number per line, with no other text."


def harness_env(base_env, tmp):
    env = {name: base_env[name] for name in ENV_ALLOWLIST if base_env.get(name)}
    env["TMPDIR"] = f"{tmp}/"
    return env


def claude_config_dir(env):
    configured = env.get("CLAUDE_CONFIG_DIR")
    return Path(configured) if configured else Path(env.get("HOME", "~")).expanduser() / ".claude"


def session_dir_name(cwd):
    """Claude Code stores the sessions of a working directory under this name in its projects directory."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(cwd))


def parse_models(raw_models):
    models = []
    for item in raw_models if isinstance(raw_models, list) else []:
        if not isinstance(item, dict):
            continue
        model_id = item.get("value")
        if not isinstance(model_id, str) or not MODEL_ID_PATTERN.match(model_id):
            continue
        if any(model["id"] == model_id for model in models):
            continue
        models.append(
            {
                "id": model_id,
                "label": bounded(item.get("displayName") or model_id, 128),
                "description": bounded(item.get("description") or "", 300),
            }
        )
        if len(models) == MAX_MODELS:
            break
    return models


class StreamSession:
    """One Claude process in stream-JSON mode. Output is read on a thread so every wait has a deadline."""

    def __init__(self, registry, key, argv, env, cwd, recorder=None):
        self.registry = registry
        self.key = key
        self.recorder = recorder
        self.lines = queue.Queue()
        self.stderr_tail = ""
        self.process = registry.spawn(
            key,
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=cwd,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_stdout(self):
        stream = self.process.stdout
        while True:
            line = stream.readline(MAX_LINE_CHARS + 1)
            if not line:
                break
            if len(line) > MAX_LINE_CHARS:
                self.lines.put({"type": "worker_error", "error": "output line too long"})
                break
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if isinstance(message, dict):
                self.lines.put(message)
        self.lines.put(None)

    def _read_stderr(self):
        for line in self.process.stderr:
            self.stderr_tail = (self.stderr_tail + line)[-2000:]

    def send(self, message):
        if self.recorder:
            self.recorder(self.key, "in", message)
        try:
            self.process.stdin.write(json.dumps(message) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            pass

    def next_message(self, deadline):
        """The next JSON message, or ``None`` when the process ended its output."""
        try:
            message = self.lines.get(timeout=deadline.remaining())
        except queue.Empty:
            raise ProbeTimeout("no answer before the deadline") from None
        if message is not None and self.recorder:
            self.recorder(self.key, "out", message)
        return message

    def send_user(self, text, message_uuid=None):
        self.send(
            {
                "type": "user",
                "message": {"role": "user", "content": text},
                "parent_tool_use_id": None,
                "session_id": "",
                "uuid": message_uuid or str(uuid.uuid4()),
            }
        )

    def kill(self):
        """Kill the whole group at once, as a crash would."""
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        self.registry.release(self.key, self.process, grace_seconds=0)

    def close(self):
        try:
            self.process.stdin.close()
        except OSError:
            pass
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        self.registry.release(self.key, self.process)


class Turn:
    def __init__(self):
        self.result = None
        self.stream_events = 0
        self.permission_prompts = []
        self.replayed = []
        self.ended = False

    @property
    def succeeded(self):
        return bool(self.result) and self.result.get("subtype") == "success" and not self.result.get("is_error")

    @property
    def text(self):
        value = (self.result or {}).get("result")
        return value if isinstance(value, str) else ""


def read_turn(session, deadline, on_message=None):
    """Read messages until a ``result`` message. Permission prompts are denied unless ``on_message`` answers."""
    turn = Turn()
    while True:
        message = session.next_message(deadline)
        if message is None:
            turn.ended = True
            return turn
        kind = message.get("type")
        if kind == "stream_event":
            turn.stream_events += 1
        elif kind == "user" and message.get("isReplay"):
            turn.replayed.append(message.get("uuid"))
        elif kind == "control_request":
            request = message.get("request") or {}
            if request.get("subtype") == "can_use_tool":
                turn.permission_prompts.append(request)
                session.send(
                    {
                        "type": "control_response",
                        "response": {
                            "subtype": "success",
                            "request_id": message.get("request_id"),
                            "response": {"behavior": "deny", "message": "Plane denies this action in a probe."},
                        },
                    }
                )
        if on_message:
            on_message(message, turn)
        if kind == "result":
            turn.result = message
            return turn


class ClaudeDriver:
    harness = HARNESS

    def __init__(self, executable, registry, base_env=None, recorder=None):
        self.executable = executable
        self.registry = registry
        self.base_env = dict(os.environ if base_env is None else base_env)
        self.recorder = recorder

    # Commands -----------------------------------------------------------------

    def _resolve_executable(self):
        if self.executable:
            path = Path(self.executable)
            return str(path) if path.is_file() and os.access(path, os.X_OK) else None
        return shutil.which("claude", path=self.base_env.get("PATH"))

    def _run(self, argv, context, timeout=COMMAND_TIMEOUT_SECONDS):
        command = context["sandbox"].wrap(argv, context["paths"])
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=min(timeout, max(1.0, context["deadline"].remaining())),
            env=context["env"],
            cwd=context["cwd"],
            stdin=subprocess.DEVNULL,
        )

    def _session(self, context, name, extra_args=()):
        argv = [context["executable"], *SESSION_FLAGS, *extra_args]
        command = context["sandbox"].wrap(argv, context["paths"])
        key = f"{context['key_prefix']}-{name}"
        return StreamSession(self.registry, key, command, context["env"], context["cwd"], self.recorder)

    # Probe --------------------------------------------------------------------

    def probe(self, workspace, sandbox, deadline):
        outcome = ProbeOutcome()
        executable = self._resolve_executable()
        if executable is None:
            outcome.blocking_issue = "harness_not_found"
            outcome.failure_hint = "The claude command was not found on the Mini."
            return outcome
        outcome.location = executable

        env = harness_env(self.base_env, workspace.tmp)
        session_root = claude_config_dir(env) / "projects"
        session_dir = session_root / session_dir_name(os.path.realpath(workspace.cwd))
        context = {
            "executable": executable,
            "sandbox": sandbox,
            "env": env,
            "cwd": str(workspace.cwd),
            "deadline": deadline,
            "key_prefix": workspace.own_dir.name,
            "paths": SandboxPaths(
                run_root=workspace.run_root,
                own_dir=workspace.own_dir,
                private_tmp=workspace.tmp,
                session_root=session_root,
                session_dir=session_dir,
                token_file=workspace.token_file,
                plane_checkout=workspace.plane_checkout,
            ),
        }
        try:
            if self._check_version(context, outcome) and self._check_authentication(context, outcome):
                self._check_sessions(context, outcome, workspace, sandbox)
        except (ProbeTimeout, subprocess.TimeoutExpired):
            outcome.failure_hint = outcome.failure_hint or "The probe did not finish before its deadline."
        except OSError as error:
            outcome.failure_hint = f"The claude command could not run ({type(error).__name__})."
        finally:
            shutil.rmtree(session_dir, ignore_errors=True)
        return outcome

    def _check_version(self, context, outcome):
        result = self._run([context["executable"], "--version"], context)
        match = VERSION_PATTERN.match(result.stdout or "")
        if result.returncode != 0 or not match:
            outcome.blocking_issue = "harness_not_found"
            outcome.failure_hint = bounded(f"claude --version failed: {result.stderr or result.stdout}", MAX_HINT_CHARS)
            return False
        outcome.harness_version = ".".join(match.groups())
        if int(match.group(1)) != SUPPORTED_MAJOR_VERSION:
            outcome.blocking_issue = "unsupported_version"
            outcome.failure_hint = (
                f"Claude Code {outcome.harness_version} is not supported; "
                f"install a {SUPPORTED_MAJOR_VERSION}.x version on the Mini, then retry."
            )
            return False
        return True

    def _check_authentication(self, context, outcome):
        check = outcome.checks["authentication"]
        result = self._run([context["executable"], "auth", "status"], context)
        try:
            status = json.loads(result.stdout or "{}")
        except ValueError:
            status = {}
        if isinstance(status, dict) and status.get("loggedIn") is True:
            check.set(True)
            return True
        check.set(False, "claude auth status: not logged in")
        outcome.failure_hint = "Claude Code is not logged in on the Mini. Sign in with claude, then retry."
        for name, other in outcome.checks.items():
            if name != "authentication":
                other.set(False, "not run: authentication failed")
        return False

    def _discover_models(self, context, outcome):
        session = self._session(context, "models")
        try:
            session.send({"type": "control_request", "request_id": "plane-init", "request": {"subtype": "initialize"}})
            step = context["deadline"].within(COMMAND_TIMEOUT_SECONDS)
            while True:
                message = session.next_message(step)
                if message is None:
                    break
                if message.get("type") == "control_response":
                    response = message.get("response") or {}
                    if response.get("request_id") == "plane-init":
                        outcome.models = parse_models((response.get("response") or {}).get("models"))
                        break
        finally:
            session.close()
        check = outcome.checks["model_report"]
        check.set(bool(outcome.models), "" if outcome.models else "the CLI reported no usable model")

    def _probe_model_args(self, outcome):
        ids = [model["id"] for model in outcome.models]
        for preferred in PROBE_MODEL_PREFERENCE:
            if preferred in ids:
                return ("--model", preferred)
        return ()

    def _check_sessions(self, context, outcome, workspace, sandbox):
        self._discover_models(context, outcome)
        model_args = self._probe_model_args(outcome)
        code_word = f"PLANE-{secrets.token_hex(3).upper()}"
        session_id = self._session_a(context, outcome, workspace, sandbox, code_word, model_args)
        if session_id is None:
            for name in ("follow_up", "recovery"):
                outcome.checks[name].set(False, "not run: the first session did not finish")
            return
        self._session_follow_up(context, outcome, session_id, code_word, model_args)
        self._session_recovery(context, outcome, session_id, code_word, model_args)

    def _session_a(self, context, outcome, workspace, sandbox, code_word, model_args):
        deadline = context["deadline"]
        session = self._session(context, "session-a", ("--tools", "Write", *model_args))
        session_id = None
        try:
            # Progress: a normal turn with partial-message events.
            session.send_user(f"Remember the code word {code_word}. Reply with the single word READY.")
            turn = read_turn(session, deadline.within(TURN_TIMEOUT_SECONDS))
            progress = turn.succeeded and turn.stream_events > 0
            outcome.checks["progress"].set(
                progress, "" if progress else f"no progress events or no result ({turn.stream_events} events)"
            )
            if turn.result:
                session_id = turn.result.get("session_id")

            # Permission: the write must raise a prompt, stay unwritten after the denial,
            # and the OS boundary must deny a direct write in the working directory.
            session.send_user(
                f"Use the Write tool to create the file {WRITE_PROBE_FILE} in the current directory "
                "with the content probe. Do not ask questions."
            )
            turn = read_turn(session, deadline.within(TURN_TIMEOUT_SECONDS))
            prompted = bool(turn.permission_prompts)
            written = (workspace.cwd / WRITE_PROBE_FILE).exists()
            os_denied, os_detail = sandbox.verify_write_denied(workspace.cwd, context["paths"])
            outcome.capabilities["permission_prompt"] = prompted
            if not prompted:
                detail = "no permission prompt arrived before the write"
            elif written:
                detail = "the file was written after the denial"
            elif not os_denied:
                detail = f"the OS boundary did not deny a write: {os_detail}"
            else:
                detail = ""
            outcome.checks["permission"].set(prompted and not written and os_denied, detail)

            self._check_interruption(session, outcome, deadline)
        finally:
            session.close()
        return session_id

    def _check_interruption(self, session, outcome, deadline):
        queued_uuid = str(uuid.uuid4())
        state = {"queued": False, "interrupted": False}

        def steer(message, turn):
            if message.get("type") != "stream_event":
                return
            if turn.stream_events == 3 and not state["queued"]:
                session.send_user("Reply with the single word NEXT.", queued_uuid)
                state["queued"] = True
            elif turn.stream_events == 8 and not state["interrupted"]:
                session.send(
                    {"type": "control_request", "request_id": "plane-interrupt", "request": {"subtype": "interrupt"}}
                )
                state["interrupted"] = True

        session.send_user(COUNT_PROMPT)
        turn = read_turn(session, deadline.within(TURN_TIMEOUT_SECONDS), steer)
        midturn = queued_uuid in turn.replayed
        outcome.capabilities["midturn_input"] = midturn
        interrupted = bool(turn.result) and (
            turn.result.get("subtype") == "error_during_execution" or turn.result.get("is_error") is True
        )
        if not state["interrupted"] or not interrupted:
            outcome.checks["interruption"].set(False, "the turn was not interrupted")
            return
        # The process must still take the next turn after the interruption.
        if midturn:
            session.send_user("Reply with the single word NEXT.")
        follow = read_turn(session, deadline.within(TURN_TIMEOUT_SECONDS))
        continued = follow.succeeded and "NEXT" in follow.text.upper()
        outcome.checks["interruption"].set(continued, "" if continued else "no turn after the interruption")

    def _ask_code_word(self, session, deadline, code_word):
        session.send_user("What code word did I ask you to remember? Reply with only the word.")
        turn = read_turn(session, deadline.within(TURN_TIMEOUT_SECONDS))
        return turn.succeeded and code_word in turn.text

    def _session_follow_up(self, context, outcome, session_id, code_word, model_args):
        session = self._session(context, "session-b", ("--tools", "", "--resume", session_id, *model_args))
        try:
            recalled = self._ask_code_word(session, context["deadline"], code_word)
        except ProbeTimeout:
            recalled = False
        finally:
            session.close()
        if not recalled and session.stderr_tail:
            detail = f"the resumed session did not answer: {session.stderr_tail}"
        else:
            detail = "" if recalled else "the resumed session did not recall the first turn"
        outcome.checks["follow_up"].set(recalled, detail)
        outcome.capabilities["native_resume"] = recalled

    def _session_recovery(self, context, outcome, session_id, code_word, model_args):
        deadline = context["deadline"]
        crashed = self._session(context, "session-c", ("--tools", "", "--resume", session_id, *model_args))
        killed = False
        try:

            def crash(message, turn):
                nonlocal killed
                if message.get("type") == "stream_event" and turn.stream_events == 3 and not killed:
                    killed = True
                    crashed.kill()

            crashed.send_user(COUNT_PROMPT)
            read_turn(crashed, deadline.within(TURN_TIMEOUT_SECONDS), crash)
        except ProbeTimeout:
            pass
        finally:
            if not killed:
                crashed.close()
        if not killed:
            outcome.checks["recovery"].set(False, "the resumed session ended before it could be stopped")
            return
        session = self._session(context, "session-d", ("--tools", "", "--resume", session_id, *model_args))
        try:
            recovered = self._ask_code_word(session, deadline, code_word)
        except ProbeTimeout:
            recovered = False
        finally:
            session.close()
        outcome.checks["recovery"].set(recovered, "" if recovered else "the session did not resume after a crash")
