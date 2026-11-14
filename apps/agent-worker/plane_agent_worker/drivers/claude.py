# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Claude Code driver: connection probe over the stream-JSON control protocol.

Every Claude process runs with the Worker boundary settings (see
``claude_boundary``: built-in sandbox for Bash, permission deny rules for the
file tools), safe mode, restricted mode, strict MCP settings and no setting
sources, so user hooks, plugins, settings files and MCP servers do not run inside
a probe. Permission prompts come to the Worker over stdio
(``--permission-prompt-tool stdio``) and the Worker denies them; the boundary
denies writes without a prompt, so a prompt for a write means a rule is missing.

Quick check (each Connect): ``--version``, ``auth status`` (JSON) and one
``initialize`` request in a one-shot process (stdin closes after the request)
that returns the model list. No prompt is sent. When that request fails, the
Connect reports the CLI aliases ``opus``, ``sonnet`` and ``haiku`` with source
``fallback``; its model report check then comes from the suite.

Behavior suite (once per CLI version, see ``conformance.ensure_verified``;
verified with Claude Code 2.1.289):
1. ``--version`` and the model list again, so the result belongs to one version.
2. Session A: a turn with partial-message events (progress); a Write in the
   working directory that a permission rule must deny, and a Bash write there
   that the built-in sandbox must deny (permission); and a long turn that
   receives ``interrupt``, then a next turn in the same process (interruption).
   The driver reports ``midturn_input`` as False and does not measure it: Send
   now for Claude stops the turn and sends the message as the next turn.
3. Session B resumes the session and recalls a code word (follow-up, native resume).
4. Session C resumes, is killed during a turn; session D resumes and recalls the
   code word again (recovery).
"""

import contextlib
import hashlib
import json
import logging
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
    REQUIRED_CHECKS,
    WAIT_SLICE_SECONDS,
    ProbeOutcome,
    ProbeTimeout,
    ProbeWorkspace,
    bounded,
)
from plane_agent_worker.drivers.claude_boundary import boundary_settings, write_boundary_settings

HARNESS = "claude_code"
# The version of the behavior suite. A passing suite result is cached per (Harness, CLI version,
# suite version). Change it when the checks, the session flags or the boundary change; a unit test
# pins ``suite_fingerprint()`` for each version.
SUITE_VERSION = 1
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
    "--safe-mode",
    "--restricted",
    "--strict-mcp-config",
    "--disable-slash-commands",
    "--setting-sources",
    "",
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
BASH_PROBE_FILE = "plane-sandbox-probe.txt"
FILE_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})
SANDBOX_DENIAL = "operation not permitted"
COUNT_PROMPT = "Count from 1 to 400, one number per line, with no other text."


def harness_env(base_env, tmp):
    env = {name: base_env[name] for name in ENV_ALLOWLIST if base_env.get(name)}
    env["TMPDIR"] = f"{tmp}/"
    # Claude Code keeps its own temporary files under this directory instead of the shared /tmp.
    env["CLAUDE_CODE_TMPDIR"] = str(tmp)
    return env


def display_path(path, home):
    """``path`` with the home directory shown as ``~``, so the report does not name the operator account."""
    if home:
        home = os.path.realpath(os.path.expanduser(home))
        real = os.path.realpath(path)
        if real == home or real.startswith(home + os.sep):
            return "~" + real[len(home) :]
    return str(path)


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
                "source": "reported",
            }
        )
        if len(models) == MAX_MODELS:
            break
    return models


class StreamSession:
    """One Claude process in stream-JSON mode. Output is read on a thread so every wait has a deadline."""

    def __init__(self, registry, key, argv, env, cwd, recorder=None, cleanup_paths=()):
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
        self.tool_uses = {}
        self.tool_results = {}
        self.ended = False

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


def suite_fingerprint():
    """A hash of what the behavior suite proves: the checks, the session flags and the boundary.

    The boundary settings are built for fixed paths that do not exist, so the hash is the same
    on every host.
    """
    root = Path("/plane-suite-fingerprint")
    own_dir = root / "runs" / "probes" / "probe"
    workspace = ProbeWorkspace(
        run_root=root / "runs",
        own_dir=own_dir,
        cwd=own_dir / "workspace",
        tmp=own_dir / "tmp",
        token_file=root / "token",
        plane_checkout=root / "plane",
    )
    document = {
        "checks": list(REQUIRED_CHECKS),
        "session_flags": list(SESSION_FLAGS),
        "boundary": boundary_settings(workspace, root / "home" / ".claude", root / "home"),
    }
    return hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()


class ClaudeDriver:
    harness = HARNESS
    suite_version = SUITE_VERSION

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

    def _run(self, argv, context, name, timeout=COMMAND_TIMEOUT_SECONDS):
        """Run a short command in its own recorded process group; the whole group stops when it ends."""
        key = f"{context['key_prefix']}-{name}"
        process = self.registry.spawn(
            key,
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=context["env"],
            cwd=context["cwd"],
            cleanup_paths=context["cleanup_paths"],
        )
        try:
            stdout, stderr = process.communicate(timeout=min(timeout, max(1.0, context["deadline"].remaining())))
        finally:
            self.registry.release(key, process, grace_seconds=0.5)
        return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)

    def _session(self, context, name, extra_args=()):
        argv = [context["executable"], *SESSION_FLAGS, "--settings", context["settings_file"], *extra_args]
        key = f"{context['key_prefix']}-{name}"
        return StreamSession(
            self.registry, key, argv, context["env"], context["cwd"], self.recorder, context["cleanup_paths"]
        )

    # Probe --------------------------------------------------------------------

    @contextlib.contextmanager
    def _harness_context(self, workspace, deadline, outcome):
        """The command context of one probe step in ``workspace``, or ``None`` when the CLI is missing.

        A deadline or start failure ends the step with a failure hint. The Claude session folder of the
        working directory is removed when the step ends.
        """
        executable = self._resolve_executable()
        if executable is None:
            outcome.blocking_issue = "harness_not_found"
            outcome.failure_hint = "The claude command was not found on the Mini."
            yield None
            return
        env = harness_env(self.base_env, workspace.tmp)
        outcome.location = display_path(executable, env.get("HOME"))

        config_dir = claude_config_dir(env)
        session_dir = config_dir / "projects" / session_dir_name(os.path.realpath(workspace.cwd))
        try:
            yield {
                "executable": executable,
                "env": env,
                "cwd": str(workspace.cwd),
                "deadline": deadline,
                "key_prefix": workspace.own_dir.name,
                "settings_file": str(write_boundary_settings(workspace, config_dir, env.get("HOME", "~"))),
                # A Worker that stops during the probe removes this folder at its next start.
                "cleanup_paths": [str(session_dir)],
            }
        except (ProbeTimeout, subprocess.TimeoutExpired):
            outcome.failure_hint = outcome.failure_hint or "The probe did not finish before its deadline."
        except OSError as error:
            outcome.failure_hint = f"The claude command could not run ({type(error).__name__})."
        finally:
            shutil.rmtree(session_dir, ignore_errors=True)

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
        result = self._run([context["executable"], "--version"], context, "version")
        match = VERSION_PATTERN.match(result.stdout or "")
        if result.returncode != 0 or not match:
            # The CLI output can name local paths; it stays in the Worker log.
            logger.warning("claude --version failed: %s", bounded(result.stderr or result.stdout, MAX_HINT_CHARS))
            outcome.blocking_issue = "harness_not_found"
            outcome.failure_hint = "claude --version did not report a version. See the Worker log on the Mini."
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
        result = self._run([context["executable"], "auth", "status"], context, "auth")
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
        session = self._session(context, "session-a", ("--tools", "Bash,Write", *model_args))
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

            # Permission: a permission rule denies the file tool and the sandbox denies the Bash write.
            session.send_user(
                f"Use the Write tool to create the file {WRITE_PROBE_FILE} in the current directory "
                "with the content probe. Do not ask questions."
            )
            file_turn = read_turn(session, deadline.within(TURN_TIMEOUT_SECONDS))
            session.send_user(
                f"Use the Bash tool to run this command: echo probe > {BASH_PROBE_FILE}\n"
                "Run it once, exactly as written. Do not ask questions."
            )
            bash_turn = read_turn(session, deadline.within(TURN_TIMEOUT_SECONDS))
            prompted = bool(file_turn.permission_prompts or bash_turn.permission_prompts)
            problem = file_tool_problem(file_turn, workspace.cwd) or bash_write_problem(bash_turn, workspace.cwd)
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


def file_tool_problem(turn, cwd):
    """Why the file-tool write was not proven denied by a permission rule, or ``None`` when it was."""
    if turn.prompted_for(FILE_TOOLS):
        return "Write asked for approval instead of being denied by a permission rule"
    tool_ids = turn.tool_ids(FILE_TOOLS)
    if not tool_ids:
        return "Write was not attempted, so the permission rule was not proven"
    if not all(tool_id in turn.denied_tool_ids for tool_id in tool_ids):
        return "Write was not denied by a permission rule"
    if (Path(cwd) / WRITE_PROBE_FILE).exists():
        return "Write created the file although a permission rule denied it"
    return None


def bash_write_problem(turn, cwd):
    """Why the Bash write was not proven denied by the built-in sandbox, or ``None`` when it was."""
    if turn.prompted_for({"Bash"}):
        return "Bash asked for approval, so the command did not run in the sandbox"
    tool_ids = turn.tool_ids({"Bash"})
    if not tool_ids:
        return "Bash was not attempted, so the sandbox was not proven"
    if any(tool_id in turn.denied_tool_ids for tool_id in tool_ids):
        return "Bash was denied by a permission rule before the sandbox could deny the write"
    results = [turn.tool_results.get(tool_id) for tool_id in tool_ids]
    if (Path(cwd) / BASH_PROBE_FILE).exists() or not all(
        result and result["is_error"] and SANDBOX_DENIAL in result["text"].lower() for result in results
    ):
        return "Bash wrote in the working directory; the sandbox did not deny the write"
    return None
