# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Docker Sandboxes for the agent CLIs, through the standalone ``sbx`` CLI (v0.53.0).

Every Claude process of a probe or a Run runs inside a sandbox microVM with full
permissions. The VM and its mounts are the boundary: the primary mount (the
sandbox's scratch folder) is writable, every other mount is read-only, and host
files outside the mounts do not exist in the VM.

Read-only user config in every sandbox:
- the host ``~/.claude/settings.json`` at ``/opt/user-claude/settings.json``, passed to
  Claude with ``--settings``, so its ``env`` (gateway URL and token) applies. The token
  never appears in a host argv;
- ``~/.claude/hooks`` at its host path, because hook commands name absolute host paths;
- the host skills: ``~/.claude/skills`` at ``/opt/user-claude/.claude/skills``,
  ``~/.agents/skills`` at ``/opt/user-claude/.agents/skills`` and at its host path, and
  every other folder that a skill link points to. A turn passes
  ``--add-dir /opt/user-claude`` so Claude finds them. ``sbx`` reserves the VM's
  ``~/.claude/skills``, so nothing goes there.

Network: the operator sets ``sbx policy init deny-all`` once. At create the Worker
allows the gateway host from ``env.ANTHROPIC_BASE_URL`` of the host settings plus any
extra hosts of the spec, and denies the allow list of the ``claude`` kit. Rules go in
before the first turn, because Claude caches a blocked HTTP MCP server as
``needs-auth``. ``--static-mcp none`` gives the Docker MCP gateway no servers; each
turn also passes ``--strict-mcp-config``.

``sbx`` stops a sandbox 30 s after its last command; the health check before each
use starts it again. The health check reads the mounted settings file: a host tool
that replaces that file (write and rename) leaves the single-file mount stale until
the sandbox restarts, so a failed read stops the sandbox once and checks again.
Mounts are fixed at create. The create arguments are kept in ``sandbox.json`` next to
the scratch folder; different arguments (for example a new skill link target)
remove and create the sandbox again, which loses its session history.

A signal to the host ``sbx exec`` client does not stop the process inside, so each
long-running process writes its PID to a pidfile and is stopped with ``kill`` of that
PID through a second ``sbx exec``. Never a broad kill: killing the keep-alive
process stops the whole sandbox.
"""

import json
import logging
import os
import shlex
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

AGENT_KIT = "claude"
VM_USER_CLAUDE = "/opt/user-claude"
VM_SETTINGS = f"{VM_USER_CLAUDE}/settings.json"
NOT_FOUND_EXIT = 125
CREATE_TIMEOUT_SECONDS = 300
COMMAND_TIMEOUT_SECONDS = 60
# The allow list that the ``claude`` kit adds to each sandbox even under ``deny-all``.
KIT_ALLOW_LIST = (
    "api.anthropic.com:443,bridge.claudeusercontent.com:443,claude.com:443,deb.debian.org:80,"
    "dhi.io:80,downloads.claude.ai:443,mcp-proxy.anthropic.com:443,platform.claude.com:443"
)
# No host variable reaches the VM. ``CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`` is not set: with it, Claude Code
# drops ``--dangerously-skip-permissions`` to the default permission mode and asks before each Bash
# command (verified with Claude Code 2.1.325 in the ``claude`` kit). It would hide nothing, because the
# agent can read the mounted settings file that holds the token.
SANDBOX_ENV = {}
# The host ``sbx`` client gets only these variables; no credential passes.
CLIENT_ENV_ALLOWLIST = ("HOME", "USER", "LOGNAME", "PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR")

SIGNED_OUT_HINT = "Sign in to Docker with `sbx login` on the Worker machine, then retry."
CLI_MISSING_HINT = "The sbx command was not found on the Worker machine. Install Docker Sandboxes, then retry."

logger = logging.getLogger("plane_agent_worker.sandbox")


class SandboxError(Exception):
    """A sandbox cannot be used.

    ``code`` is ``sandbox_cli_missing``, ``sandbox_not_signed_in`` or ``sandbox_unavailable``.
    """

    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class Mount:
    host: str
    target: str | None = None

    def argument(self):
        return f"{self.host}:{self.target}:ro" if self.target and self.target != self.host else f"{self.host}:ro"


@dataclass(frozen=True)
class SandboxSpec:
    name: str
    primary: Path
    mounts: tuple = ()
    allow: tuple = ()


def probe_scratch(run_root, harness):
    """The writable scratch folder of the probe sandbox of ``harness``."""
    return Path(run_root) / "sandboxes" / f"probe-{harness}" / "scratch"


def first_line(text):
    return next((line.strip() for line in (text or "").splitlines() if line.strip()), "")[:300]


def _is_under(path, parent):
    return path == parent or path.startswith(parent.rstrip("/") + "/")


def skill_mounts(home):
    """Read-only mounts for the host skills and every folder that a skill link points to."""
    home = Path(home)
    skills = home / ".claude" / "skills"
    agents = home / ".agents" / "skills"
    mounts = []
    if skills.is_dir():
        mounts.append(Mount(str(skills), f"{VM_USER_CLAUDE}/.claude/skills"))
    if agents.is_dir():
        mounts.append(Mount(str(agents), f"{VM_USER_CLAUDE}/.agents/skills"))
        mounts.append(Mount(str(agents)))
    if not skills.is_dir():
        return mounts
    for entry in sorted(skills.iterdir()):
        if not entry.is_symlink():
            continue
        target = os.path.realpath(entry)
        if not os.path.isdir(target):
            continue
        link = os.readlink(entry)
        if os.path.isabs(link):
            vm_path = os.path.normpath(link)
        else:
            lexical = os.path.normpath(os.path.join(skills, link))
            if not _is_under(lexical, str(home)):
                logger.warning("Skill link %s points outside the home folder; it is not mounted", entry.name)
                continue
            vm_path = f"{VM_USER_CLAUDE}/{os.path.relpath(lexical, home)}"
        if any(_is_under(vm_path, mount.target or mount.host) for mount in mounts):
            continue
        mounts.append(Mount(target, vm_path))
    return mounts


def user_config_mounts(home):
    """The host settings file, hook scripts and skills, all read-only."""
    home = Path(home)
    mounts = [Mount(str(home / ".claude" / "settings.json"), VM_SETTINGS)]
    hooks = home / ".claude" / "hooks"
    if hooks.is_dir():
        mounts.append(Mount(str(hooks)))
    return tuple(mounts + skill_mounts(home))


def gateway_rule(home):
    """``host:port`` of ``env.ANTHROPIC_BASE_URL`` in the host settings, or ``None``. Reads no other value."""
    try:
        settings = json.loads((Path(home) / ".claude" / "settings.json").read_text(encoding="utf-8"))
        url = urlsplit(str((settings.get("env") or {}).get("ANTHROPIC_BASE_URL") or ""))
        if url.scheme not in ("http", "https") or not url.hostname:
            return None
        return f"{url.hostname}:{url.port or (443 if url.scheme == 'https' else 80)}"
    except (OSError, ValueError, AttributeError):
        return None


class Sandboxes:
    """Create, check and use sandboxes through the ``sbx`` CLI at ``executable``."""

    def __init__(self, executable, home, memory=None, base_env=None, prefix="plane-"):
        self.executable = executable
        # Every sandbox name starts with this prefix; tests use their own prefix.
        self.prefix = prefix
        self.home = Path(home)
        self.memory = memory
        base_env = dict(os.environ if base_env is None else base_env)
        self._locks = {}
        self._locks_guard = threading.Lock()
        self.client_env = {name: base_env[name] for name in CLIENT_ENV_ALLOWLIST if base_env.get(name)}

    def probe_name(self, harness):
        return f"{self.prefix}probe-{harness.replace('_', '-')}"

    def qa_name(self, key):
        return f"{self.prefix}qa-{key}"

    # Commands -----------------------------------------------------------------

    def _run(self, args, timeout=COMMAND_TIMEOUT_SECONDS):
        try:
            return subprocess.run(
                [self.executable, *args],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                env=self.client_env,
                timeout=timeout,
            )
        except FileNotFoundError as error:
            raise SandboxError("sandbox_cli_missing", CLI_MISSING_HINT) from error
        except subprocess.TimeoutExpired as error:
            raise SandboxError("sandbox_unavailable", f"sbx {args[0]} did not answer in {timeout} s") from error

    def check_signed_in(self):
        """``sbx ls`` must succeed; it fails when the Docker sign-in is missing."""
        if not self.executable:
            raise SandboxError("sandbox_cli_missing", CLI_MISSING_HINT)
        result = self._run(["ls"])
        if result.returncode != 0:
            logger.warning("sbx ls failed: %s", first_line(result.stderr or result.stdout))
            raise SandboxError("sandbox_not_signed_in", SIGNED_OUT_HINT)

    def create_args(self, spec):
        args = ["--no-input", "create", "--name", spec.name, "--static-mcp", "none"]
        if self.memory:
            args += ["--memory", self.memory]
        return [*args, AGENT_KIT, str(spec.primary), *(mount.argument() for mount in spec.mounts)]

    def rules(self, spec):
        allow = [rule for rule in (gateway_rule(self.home), *spec.allow) if rule]
        return [["allow", rule] for rule in dict.fromkeys(allow)] + [["deny", KIT_ALLOW_LIST]]

    def ensure(self, spec):
        """Make sure the sandbox of ``spec`` exists with the current mounts and is running.

        Returns True when the sandbox was created now. Concurrent callers for one sandbox wait for each other.
        """
        with self._locks_guard:
            lock = self._locks.setdefault(spec.name, threading.Lock())
        with lock:
            return self._ensure(spec)

    def _ensure(self, spec):
        state_file = Path(spec.primary).parent / "sandbox.json"
        wanted = {"create": self.create_args(spec), "rules": self.rules(spec)}
        try:
            known = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            known = None
        if known != wanted:
            self.remove(spec.name)
            self._create(spec, wanted, state_file)
            return True
        status = self.health(spec.name)
        if status == NOT_FOUND_EXIT:
            self._create(spec, wanted, state_file)
            return True
        return False

    def health(self, name):
        """0 when the sandbox answers and reads its settings; ``NOT_FOUND_EXIT`` when it does not exist.

        A stopped sandbox starts. A failed settings read (a stale single-file mount) stops the
        sandbox once and checks again. Any other failure raises ``sandbox_unavailable``.
        """
        check = ["exec", name, "sh", "-c", f"test -r {VM_SETTINGS}"]
        result = self._run(check)
        if result.returncode == 1:
            self._run(["stop", name])
            result = self._run(check)
        if result.returncode in (0, NOT_FOUND_EXIT):
            return result.returncode
        raise SandboxError("sandbox_unavailable", first_line(result.stderr) or f"exit {result.returncode}")

    def _create(self, spec, wanted, state_file):
        Path(spec.primary).mkdir(mode=0o700, parents=True, exist_ok=True)
        result = self._run(wanted["create"], timeout=CREATE_TIMEOUT_SECONDS)
        if result.returncode != 0:
            raise SandboxError("sandbox_unavailable", first_line(result.stderr) or "sbx create failed")
        for action, rule in wanted["rules"]:
            result = self._run(["policy", action, "network", "--sandbox", spec.name, rule])
            if result.returncode != 0:
                self.remove(spec.name)
                raise SandboxError("sandbox_unavailable", first_line(result.stderr) or f"sbx policy {action} failed")
        state_file.write_text(json.dumps(wanted), encoding="utf-8")
        logger.info("Created sandbox %s", spec.name)

    def remove(self, name):
        self._run(["rm", "--force", name])

    def exec_argv(self, name, cwd, command, pidfile=None, interactive=True):
        """The host argv that runs ``command`` in the sandbox. With ``pidfile``, the process writes its PID there."""
        argv = [self.executable, "exec"]
        if interactive:
            argv.append("-i")
        argv += ["-w", str(cwd)]
        for key, value in SANDBOX_ENV.items():
            argv += ["-e", f"{key}={value}"]
        argv.append(name)
        if pidfile is not None:
            argv += ["sh", "-c", f'echo $$ > {shlex.quote(str(pidfile))}; exec "$@"', "sh"]
        return [*argv, *command]

    def kill(self, name, pidfile, signal_name="KILL"):
        """Stop the process of ``pidfile`` inside the sandbox. Returns True when ``kill`` succeeded."""
        script = f'kill -{signal_name} "$(cat {shlex.quote(str(pidfile))})"'
        try:
            result = self._run(["exec", name, "sh", "-c", script])
        except SandboxError:
            return False
        return result.returncode == 0
