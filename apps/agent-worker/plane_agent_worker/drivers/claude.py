# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Claude Code driver: connection probe over the stream-JSON control protocol.

Every Claude process runs inside the probe sandbox of the Worker (``sandbox.py``)
with full permissions (``--dangerously-skip-permissions``); the sandbox microVM and
its mounts are the boundary. Claude reads the host ``~/.claude/settings.json``
through a read-only mount (``--settings``), so the user's gateway and token apply,
and loads no MCP server (``--strict-mcp-config`` without a config file).
Permission prompts would come to the Worker over stdio
(``--permission-prompt-tool stdio``); under full permissions none must arrive.

Quick check (each Connect): Docker sign-in (``sbx ls``), the probe sandbox, then
inside it ``--version``, ``auth status`` (JSON) and one ``initialize`` request in a
one-shot process (stdin closes after the request) that returns the model list. No
prompt is sent. When that request fails, the Connect reports the CLI aliases
``opus``, ``sonnet`` and ``haiku`` with source ``fallback``; its model report check
then comes from the suite.

Behavior suite (once per CLI version, see ``conformance.ensure_verified``):
1. ``--version`` and the model list again, so the result belongs to one version.
2. Session A: a turn with partial-message events (progress); a Bash write in the
   working directory that must run without a permission request, in a session
   whose ``init`` message reports ``bypassPermissions`` (permission); and a long
   turn that receives ``interrupt``, then a next turn in the same process
   (interruption). The driver reports ``midturn_input`` as False and does not
   measure it: Send now for Claude stops the turn and sends the message as the
   next turn.
3. Session B resumes the session and recalls a code word (follow-up, native resume).
4. Session C resumes and is killed during a turn (a kill of its pidfile inside the
   sandbox); session D resumes and recalls the code word again (recovery).
"""

import contextlib
import hashlib
import json
import logging
import os
import queue
import re
import secrets
import signal
import subprocess
import threading
import uuid
from pathlib import Path

from plane_agent_worker.drivers.base import (
    MAX_HINT_CHARS,
    REQUIRED_CHECKS,
    WAIT_SLICE_SECONDS,
    ProbeOutcome,
    ProbeTimeout,
    bounded,
)
from plane_agent_worker.sandbox import (
    SANDBOX_ENV,
    VM_SETTINGS,
    VM_USER_CLAUDE,
    SandboxError,
    SandboxSpec,
    probe_scratch,
    user_config_mounts,
)

HARNESS = "claude_code"
# The version of the behavior suite. A passing suite result is cached per (Harness, CLI version,
# suite version). Change it when the checks, the session flags or the boundary change; a unit test
# pins ``suite_fingerprint()`` for each version. Version 3 runs inside the probe sandbox.
SUITE_VERSION = 3
SUPPORTED_MAJOR_VERSION = 2
VERSION_PATTERN = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)")
MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:\[\]/-]{0,127}$")
MAX_MODELS = 50
# Shown at Connect only when the model list request fails; the suite always needs a real report.
# They are CLI aliases, so the list does not age when new models come out.
FALLBACK_MODELS = tuple(
    {"id": model_id, "label": label, "description": "", "source": "fallback"}
    for model_id, label in (("opus", "Opus"), ("sonnet", "Sonnet"), ("haiku", "Haiku"))
)
MODEL_REQUEST_FAILED = "the CLI did not answer the model list request"
MAX_LINE_CHARS = 2_000_000
COMMAND_TIMEOUT_SECONDS = 20
TURN_TIMEOUT_SECONDS = 45
# The probe uses the fastest reported model when one of these is present.
PROBE_MODEL_PREFERENCE = ("haiku",)

logger = logging.getLogger("plane_agent_worker.drivers.claude")

SESSION_FLAGS = (
    "-p",
    "--input-format",
    "stream-json",
    "--output-format",
    "stream-json",
    "--verbose",
    "--include-partial-messages",
    "--replay-user-messages",
    "--disable-slash-commands",
    "--permission-prompt-tool",
    "stdio",
)

# Every probe process: full permissions inside the sandbox, the host settings from the read-only
# mount, and no MCP server.
PROBE_FLAGS = ("--dangerously-skip-permissions", "--settings", VM_SETTINGS, "--strict-mcp-config")
# A Run turn also loads all host skills and the turn's MCP config, and nothing else.
RUN_FLAGS = (
    "--dangerously-skip-permissions",
    "--settings",
    VM_SETTINGS,
    "--add-dir",
    VM_USER_CLAUDE,
    "--strict-mcp-config",
)
BYPASS_MODE = "bypassPermissions"
# A wrong gateway token makes Claude retry for about 3 minutes before it reports 401, so a turn that
# sends no model output within this time fails with a gateway hint.
FIRST_OUTPUT_SECONDS = 30
OUTPUT_TYPES = frozenset({"stream_event", "assistant", "result"})
BASH_PROBE_FILE = "plane-sandbox-probe.txt"
COUNT_PROMPT = "Count from 1 to 400, one number per line, with no other text."


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
                "source": "reported",
            }
        )
        if len(models) == MAX_MODELS:
            break
    return models


class StreamSession:
    """One Claude process in stream-JSON mode. Output is read on a thread so every wait has a deadline."""

    def __init__(self, registry, key, argv, env, cwd, recorder=None, cleanup_paths=(), stop_inside=None):
        self.registry = registry
        self.key = key
        self.recorder = recorder
        # Stops the process inside the sandbox; a signal to the host client does not reach it.
        self.stop_inside = stop_inside
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
            cleanup_paths=cleanup_paths,
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
        while True:
            remaining = deadline.remaining()
            if remaining <= 0:
                raise ProbeTimeout("no answer before the deadline")
            try:
                message = self.lines.get(timeout=min(WAIT_SLICE_SECONDS, remaining))
                break
            except queue.Empty:
                continue
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

    def close_input(self):
        """End stdin; the CLI answers the requests it already has, then exits."""
        try:
            self.process.stdin.close()
        except OSError:
            pass

    def kill(self):
        """Kill the process at once, as a crash would: inside the sandbox first, then the host client."""
        if self.stop_inside:
            self.stop_inside()
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
            if self.stop_inside:
                self.stop_inside()
        self.registry.release(self.key, self.process)


class TurnOutcome:
    """How a Run turn ended."""

    def __init__(self):
        self.result = None
        self.session_id = ""
        self.output_started = False
        self.timed_out = False
        self.no_output = False
        self.ended = False
        self.stderr_tail = ""

    @property
    def succeeded(self):
        return bool(self.result) and self.result.get("subtype") == "success" and not self.result.get("is_error")

    @property
    def text(self):
        value = (self.result or {}).get("result")
        return value if isinstance(value, str) else ""


class Turn:
    def __init__(self):
        self.result = None
        self.stream_events = 0
        self.permission_prompts = []
        self.replayed = []
        self.tool_uses = {}
        self.tool_results = {}
        self.ended = False
        # The tools and the permission mode of the ``init`` message; ``None`` when no ``init`` arrived.
        self.tools = None
        self.permission_mode = None

    @property
    def succeeded(self):
        return bool(self.result) and self.result.get("subtype") == "success" and not self.result.get("is_error")

    @property
    def text(self):
        value = (self.result or {}).get("result")
        return value if isinstance(value, str) else ""

    @property
    def denied_tool_ids(self):
        denials = (self.result or {}).get("permission_denials")
        return (
            {item.get("tool_use_id") for item in denials if isinstance(item, dict)}
            if isinstance(denials, list)
            else set()
        )

    def tool_ids(self, names):
        return [tool_id for tool_id, tool in self.tool_uses.items() if tool["name"] in names]

    def prompted_for(self, names):
        return any(request.get("tool_name") in names for request in self.permission_prompts)


def _content_blocks(message):
    content = (message.get("message") or {}).get("content")
    return [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []


def _result_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(block.get("text", "") for block in content if isinstance(block, dict))
    return ""


def read_turn(session, deadline, on_message=None, allow_tools=frozenset()):
    """Read messages until a ``result`` message.

    A permission prompt is allowed for a tool in ``allow_tools`` and denied for every other tool.
    """
    turn = Turn()
    while True:
        message = session.next_message(deadline)
        if message is None:
            turn.ended = True
            return turn
        kind = message.get("type")
        if kind == "system" and message.get("subtype") == "init":
            if isinstance(message.get("tools"), list):
                turn.tools = [tool for tool in message["tools"] if isinstance(tool, str)]
            turn.permission_mode = message.get("permissionMode")
        elif kind == "stream_event":
            turn.stream_events += 1
        elif kind == "user" and message.get("isReplay"):
            turn.replayed.append(message.get("uuid"))
        elif kind == "assistant":
            for block in _content_blocks(message):
                if block.get("type") == "tool_use" and isinstance(block.get("id"), str):
                    turn.tool_uses[block["id"]] = {"name": block.get("name"), "input": block.get("input")}
        elif kind == "user":
            for block in _content_blocks(message):
                if block.get("type") == "tool_result" and isinstance(block.get("tool_use_id"), str):
                    turn.tool_results[block["tool_use_id"]] = {
                        "is_error": block.get("is_error") is True,
                        "text": _result_text(block.get("content")),
                    }
        elif kind == "control_request":
            request = message.get("request") or {}
            if request.get("subtype") == "can_use_tool":
                turn.permission_prompts.append(request)
                if request.get("tool_name") in allow_tools:
                    answer = {"behavior": "allow", "updatedInput": request.get("input") or {}}
                else:
                    answer = {"behavior": "deny", "message": "Plane denies this action in a probe."}
                session.send(
                    {
                        "type": "control_response",
                        "response": {"subtype": "success", "request_id": message.get("request_id"), "response": answer},
                    }
                )
        if on_message:
            on_message(message, turn)
        if kind == "result":
            turn.result = message
            return turn


def suite_fingerprint():
    """A hash of what the behavior suite proves: the checks, the session flags and the sandbox environment."""
    document = {
        "checks": list(REQUIRED_CHECKS),
        "session_flags": list(SESSION_FLAGS),
        "probe_flags": list(PROBE_FLAGS),
        "sandbox_env": SANDBOX_ENV,
    }
    return hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()


class ClaudeDriver:
    harness = HARNESS
    suite_version = SUITE_VERSION

    def __init__(self, sandboxes, run_root, registry, recorder=None):
        self.sandboxes = sandboxes
        self.run_root = run_root
        self.registry = registry
        self.recorder = recorder

    # Commands -----------------------------------------------------------------

    def _run(self, args, context, name, timeout=COMMAND_TIMEOUT_SECONDS):
        """Run one short ``claude`` command in the sandbox, in its own recorded host process group."""
        key = f"{context['key_prefix']}-{name}"
        argv = self.sandboxes.exec_argv(context["sandbox"], context["cwd"], ["claude", *args], interactive=False)
        process = self.registry.spawn(
            key,
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.sandboxes.client_env,
            cwd=context["cwd"],
        )
        try:
            stdout, stderr = process.communicate(timeout=min(timeout, max(1.0, context["deadline"].remaining())))
        finally:
            self.registry.release(key, process, grace_seconds=0.5)
        return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)

    def _session(self, context, name, extra_args=()):
        sandbox = context["sandbox"]
        pidfile = Path(context["pid_dir"]) / f"{name}.pid"
        command = ["claude", *SESSION_FLAGS, *PROBE_FLAGS, *extra_args]
        argv = self.sandboxes.exec_argv(sandbox, context["cwd"], command, pidfile=pidfile)
        key = f"{context['key_prefix']}-{name}"
        return StreamSession(
            self.registry,
            key,
            argv,
            self.sandboxes.client_env,
            context["cwd"],
            self.recorder,
            stop_inside=lambda: self.sandboxes.kill(sandbox, pidfile),
        )

    # Run turns ----------------------------------------------------------------

    def cli_version(self, key, sandbox, cwd, deadline):
        """``claude --version`` inside ``sandbox``, or ``None`` when it does not report one."""
        context = {"sandbox": sandbox, "cwd": str(cwd), "deadline": deadline, "key_prefix": key}
        result = self._run(["--version"], context, "version")
        match = VERSION_PATTERN.match(result.stdout or "")
        if result.returncode != 0 or not match:
            logger.warning("claude --version failed in %s: %s", sandbox, bounded(result.stderr, MAX_HINT_CHARS))
            return None
        return ".".join(match.groups())

    def run_turn(
        self,
        *,
        key,
        sandbox,
        cwd,
        host_dir,
        pidfile,
        prompt,
        mcp_config,
        model,
        deadline,
        on_message,
        first_output_seconds=FIRST_OUTPUT_SECONDS,
    ):
        """Run one Q&A turn in ``sandbox`` with ``cwd`` as working directory. Returns a ``TurnOutcome``.

        ``on_message`` gets every stream message. The turn ends at its ``result`` message, when the
        process ends, when no model output arrives in ``FIRST_OUTPUT_SECONDS`` or at ``deadline``.
        """
        command = ["claude", *SESSION_FLAGS, *RUN_FLAGS, "--mcp-config", str(mcp_config)]
        if model:
            command += ["--model", model]
        argv = self.sandboxes.exec_argv(sandbox, cwd, command, pidfile=pidfile)
        session = StreamSession(
            self.registry,
            key,
            argv,
            self.sandboxes.client_env,
            str(host_dir),
            self.recorder,
            stop_inside=lambda: self.sandboxes.kill(sandbox, pidfile),
        )
        outcome = TurnOutcome()
        try:
            session.send_user(prompt)
            first = deadline.within(first_output_seconds)
            while outcome.result is None:
                message = session.next_message(deadline if outcome.output_started else first)
                if message is None:
                    outcome.ended = True
                    break
                kind = message.get("type")
                if kind in OUTPUT_TYPES:
                    outcome.output_started = True
                if kind == "system" and message.get("subtype") == "init":
                    outcome.session_id = message.get("session_id") or outcome.session_id
                if kind == "control_request" and (message.get("request") or {}).get("subtype") == "can_use_tool":
                    # Full permissions: a permission request is not expected; deny it.
                    answer = {"behavior": "deny", "message": "Plane runs this turn with full permissions only."}
                    response = {"subtype": "success", "request_id": message.get("request_id"), "response": answer}
                    session.send({"type": "control_response", "response": response})
                on_message(message)
                if kind == "result":
                    outcome.result = message
        except ProbeTimeout:
            outcome.timed_out = True
            outcome.no_output = not outcome.output_started
            session.kill()
            return outcome
        finally:
            outcome.stderr_tail = session.stderr_tail
        session.close()
        return outcome

    # Probe --------------------------------------------------------------------

    def probe_spec(self):
        return SandboxSpec(
            name=self.sandboxes.probe_name(self.harness),
            primary=probe_scratch(self.run_root, self.harness),
            mounts=user_config_mounts(self.sandboxes.home),
        )

    @contextlib.contextmanager
    def _harness_context(self, workspace, deadline, outcome):
        """The command context of one probe step in ``workspace``, or ``None`` when the sandbox is not usable.

        A deadline or start failure ends the step with a failure hint.
        """
        spec = self.probe_spec()
        try:
            self.sandboxes.check_signed_in()
            self.sandboxes.ensure(spec)
        except SandboxError as error:
            if error.code == "sandbox_not_signed_in":
                outcome.blocking_issue = "sandbox_not_signed_in"
            elif error.code == "sandbox_cli_missing":
                outcome.blocking_issue = "harness_not_found"
            outcome.failure_hint = (
                bounded(f"The probe sandbox is not available: {error.detail}", MAX_HINT_CHARS)
                if error.code == "sandbox_unavailable"
                else error.detail
            )
            yield None
            return
        outcome.location = f"sbx sandbox {spec.name}"
        try:
            yield {
                "sandbox": spec.name,
                "cwd": str(workspace.cwd),
                "pid_dir": str(workspace.own_dir),
                "deadline": deadline,
                "key_prefix": workspace.own_dir.name,
            }
        except (ProbeTimeout, subprocess.TimeoutExpired):
            outcome.failure_hint = outcome.failure_hint or "The probe did not finish before its deadline."
        except OSError as error:
            outcome.failure_hint = f"The sbx command could not run ({type(error).__name__})."

    def quick_check(self, workspace, deadline):
        """The Connect check: CLI version, login and model list. The behavior suite does not run."""
        outcome = ProbeOutcome()
        with self._harness_context(workspace, deadline, outcome) as context:
            if (
                context is not None
                and self._check_version(context, outcome)
                and self._check_authentication(context, outcome)
            ):
                self._discover_models(context, outcome, allow_fallback=True)
        return outcome

    def run_suite(self, workspace, deadline):
        """The behavior suite of the installed version.

        It reads the version and the model list itself, so its result belongs to the version it
        ran on and proves a real model report. Then it runs the progress, permission,
        interruption, follow-up and recovery sessions.
        """
        outcome = ProbeOutcome()
        with self._harness_context(workspace, deadline, outcome) as context:
            if context is not None and self._check_version(context, outcome):
                self._discover_models(context, outcome)
                self._run_sessions(context, outcome, workspace)
        return outcome

    def _check_version(self, context, outcome):
        result = self._run(["--version"], context, "version")
        match = VERSION_PATTERN.match(result.stdout or "")
        if result.returncode != 0 or not match:
            # The CLI output can name local paths; it stays in the Worker log.
            logger.warning("claude --version failed: %s", bounded(result.stderr or result.stdout, MAX_HINT_CHARS))
            outcome.blocking_issue = "harness_not_found"
            outcome.failure_hint = "claude --version did not report a version in the sandbox. See the Worker log."
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
        result = self._run(["--settings", VM_SETTINGS, "auth", "status"], context, "auth")
        try:
            status = json.loads(result.stdout or "{}")
        except ValueError:
            status = {}
        if isinstance(status, dict) and status.get("loggedIn") is True:
            check.set(True)
            return True
        check.set(False, "claude auth status: not logged in")
        outcome.failure_hint = (
            "Claude Code in the sandbox is not logged in. Check the gateway URL and token in ~/.claude/settings.json "
            "on the Worker machine, then retry."
        )
        for name, other in outcome.checks.items():
            if name != "authentication":
                other.set(False, "not run: authentication failed")
        return False

    def _request_models(self, context):
        """One ``initialize`` request in a one-shot process. Returns the parsed models, or ``None`` on failure."""
        session = self._session(context, "models")
        try:
            session.send({"type": "control_request", "request_id": "plane-init", "request": {"subtype": "initialize"}})
            session.close_input()
            step = context["deadline"].within(COMMAND_TIMEOUT_SECONDS)
            while True:
                try:
                    message = session.next_message(step)
                except ProbeTimeout:
                    if context["deadline"].expired:
                        raise
                    return None
                if message is None:
                    return None
                response = message.get("response") or {}
                if message.get("type") == "control_response" and response.get("request_id") == "plane-init":
                    if response.get("subtype") != "success":
                        return None
                    return parse_models((response.get("response") or {}).get("models"))
        finally:
            session.close()

    def _discover_models(self, context, outcome, allow_fallback=False):
        models = self._request_models(context)
        check = outcome.checks["model_report"]
        if models is None:
            check.set(False, MODEL_REQUEST_FAILED)
            if allow_fallback:
                outcome.models = [dict(model) for model in FALLBACK_MODELS]
                outcome.models_from_fallback = True
            return
        outcome.models = models
        check.set(bool(models), "" if models else "the CLI reported no usable model")

    def _probe_model_args(self, outcome):
        ids = [model["id"] for model in outcome.models]
        for preferred in PROBE_MODEL_PREFERENCE:
            if preferred in ids:
                return ("--model", preferred)
        return ()

    def _run_sessions(self, context, outcome, workspace):
        model_args = self._probe_model_args(outcome)
        code_word = f"PLANE-{secrets.token_hex(3).upper()}"
        session_id = self._session_a(context, outcome, workspace, code_word, model_args)
        if session_id is None:
            for name in ("follow_up", "recovery"):
                outcome.checks[name].set(False, "not run: the first session did not finish")
            return
        self._session_follow_up(context, outcome, session_id, code_word, model_args)
        self._session_recovery(context, outcome, session_id, code_word, model_args)

    def _session_a(self, context, outcome, workspace, code_word, model_args):
        deadline = context["deadline"]
        session = self._session(context, "session-a", ("--tools", "Bash", *model_args))
        session_id = None
        prompted = False
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

            # Permission: full permissions inside the sandbox. A write in the working directory (the
            # writable scratch folder) runs without a permission request.
            session.send_user(
                f"Use the Bash tool to run this command: echo probe > {BASH_PROBE_FILE}\n"
                "Run it once, exactly as written. Do not ask questions."
            )
            bash_turn = read_turn(session, deadline.within(TURN_TIMEOUT_SECONDS))
            prompted = bool(turn.permission_prompts or bash_turn.permission_prompts)
            problem = permission_problem(turn, bash_turn)
            outcome.checks["permission"].set(problem is None, problem or "")

            self._check_interruption(session, outcome, deadline)
        finally:
            outcome.capabilities["permission_prompt"] = prompted
            session.close()
        return session_id

    def _check_interruption(self, session, outcome, deadline):
        """Interrupt a long turn, then the same process must take the next turn.

        Send now for Claude stops the current turn and sends the message as the next turn, so no
        message is sent during the turn and midturn input is not measured: it stays False.
        """
        state = {"interrupted": False}

        def interrupt(message, turn):
            if message.get("type") == "stream_event" and turn.stream_events == 8 and not state["interrupted"]:
                session.send(
                    {"type": "control_request", "request_id": "plane-interrupt", "request": {"subtype": "interrupt"}}
                )
                state["interrupted"] = True

        session.send_user(COUNT_PROMPT)
        turn = read_turn(session, deadline.within(TURN_TIMEOUT_SECONDS), interrupt)
        outcome.capabilities["midturn_input"] = False
        interrupted = bool(turn.result) and (
            turn.result.get("subtype") == "error_during_execution" or turn.result.get("is_error") is True
        )
        if not state["interrupted"] or not interrupted:
            outcome.checks["interruption"].set(False, "the turn was not interrupted")
            return
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
            # The CLI error text can name local paths; it stays in the Worker log.
            logger.warning(
                "The resumed Claude session did not answer: %s", bounded(session.stderr_tail, MAX_HINT_CHARS)
            )
        outcome.checks["follow_up"].set(
            recalled, "" if recalled else "the resumed session did not recall the first turn"
        )
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


def permission_problem(turn, bash_turn):
    """Why full permissions were not proven, or ``None`` when they were."""
    if turn.permission_mode != BYPASS_MODE:
        return f"the CLI did not report the {BYPASS_MODE} mode (it reported {turn.permission_mode or 'no mode'})"
    if turn.permission_prompts or bash_turn.permission_prompts:
        return "the CLI sent a permission request although it runs with full permissions"
    if not bash_turn.tool_ids({"Bash"}) or not bash_turn.succeeded:
        return "the Bash command did not run"
    return None
