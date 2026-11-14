# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Worker configuration from the environment.

Rules:
- Plane is reached only on localhost, so the Worker token never leaves the Mini.
- The token file is a private regular file (mode 0600, owned by the Worker user,
  not a symbolic link) outside the Run root, where Harness processes can read.
- The Run root is private to the Worker user and is outside the Plane checkout.
- The host ``~/.claude/settings.json`` exists: every sandbox mounts it read-only.
"""

import ipaddress
import os
import re
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

LOCALHOST_NAMES = frozenset({"localhost", "127.0.0.1", "::1"})
DEFAULT_POLL_SECONDS = 2.0
MAX_TOKEN_BYTES = 256

ENV_ORIGIN = "PLANE_AGENT_WORKER_API_ORIGIN"
ENV_TOKEN_FILE = "PLANE_AGENT_WORKER_TOKEN_FILE"
ENV_RUN_ROOT = "PLANE_AGENT_WORKER_RUN_ROOT"
ENV_PLANE_CHECKOUT = "PLANE_AGENT_WORKER_PLANE_CHECKOUT"
ENV_SBX_BIN = "PLANE_AGENT_WORKER_SBX_BIN"
ENV_POLL_SECONDS = "PLANE_AGENT_WORKER_POLL_SECONDS"
ENV_SANDBOX_MEMORY = "PLANE_AGENT_SANDBOX_MEMORY"
MEMORY_PATTERN = re.compile(r"^[1-9][0-9]*[mMgG]$")
ENV_MCP_PORT = "PLANE_AGENT_MCP_PORT"
ENV_IMPORT_MCP_SERVERS = "PLANE_AGENT_IMPORT_MCP_SERVERS"
# The same names as the Plane API setting, so one value serves both.
ENV_GIT_ALLOWED_HOSTS = "AGENT_GIT_ALLOWED_HOSTS"
ENV_GIT_ALLOWED_IPS = "AGENT_GIT_ALLOWED_IPS"
DEFAULT_MCP_PORT = 7450


class ConfigError(Exception):
    """The Worker configuration is not safe to use."""


@dataclass(frozen=True)
class WorkerConfig:
    api_origin: str
    token_file: Path
    run_root: Path
    plane_checkout: Path
    home: Path
    sbx_bin: str | None = None
    sandbox_memory: str | None = None
    poll_seconds: float = DEFAULT_POLL_SECONDS
    mcp_port: int = DEFAULT_MCP_PORT
    import_mcp_servers: tuple = ()
    git_allowed_hosts: frozenset = frozenset()
    git_allowed_ips: tuple = ()

    def read_token(self):
        """Read the token again, with the same file checks as at start."""
        return read_token_file(self.token_file)


def _is_within(path, parent):
    return path == parent or parent in path.parents


def _absolute(env, name, required=True):
    value = (env.get(name) or "").strip()
    if not value:
        if required:
            raise ConfigError(f"{name} is required.")
        return None
    path = Path(value)
    if not path.is_absolute():
        raise ConfigError(f"{name} must be an absolute path.")
    return path


def validate_origin(origin):
    parts = urlsplit(origin or "")
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ConfigError(f"{ENV_ORIGIN} must be an http or https origin, for example http://localhost:8000.")
    if parts.hostname not in LOCALHOST_NAMES:
        raise ConfigError(f"{ENV_ORIGIN} must point to localhost; the Worker token never leaves the Mini.")
    if parts.username or parts.password or parts.path not in ("", "/") or parts.query or parts.fragment:
        raise ConfigError(f"{ENV_ORIGIN} must be a bare origin without user info, path, query or fragment.")
    try:
        _ = parts.port  # urlsplit raises ValueError only when the port is read
    except ValueError as error:
        raise ConfigError(f"{ENV_ORIGIN} has an invalid port.") from error
    return origin.rstrip("/")


def read_token_file(path):
    try:
        info = os.lstat(path)
    except FileNotFoundError as error:
        raise ConfigError(f"The token file {path} does not exist.") from error
    if stat.S_ISLNK(info.st_mode):
        raise ConfigError("The token file must not be a symbolic link.")
    if not stat.S_ISREG(info.st_mode):
        raise ConfigError("The token file must be a regular file.")
    if info.st_uid != os.getuid():
        raise ConfigError("The token file must belong to the Worker user.")
    if info.st_mode & 0o077:
        raise ConfigError("The token file must have mode 0600 (no group or other access).")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        raw = os.read(descriptor, MAX_TOKEN_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(raw) > MAX_TOKEN_BYTES:
        raise ConfigError("The token file is too large.")
    token = raw.decode("utf-8", errors="strict").strip()
    if not token:
        raise ConfigError("The token file is empty.")
    return token


def _prepare_run_root(run_root):
    run_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = os.lstat(run_root)
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ConfigError(f"{ENV_RUN_ROOT} must be a directory, not a symbolic link.")
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ConfigError(f"{ENV_RUN_ROOT} must be private to the Worker user (mode 0700).")


def default_plane_checkout():
    """The checkout that contains this package, when the Worker runs from a Plane checkout."""
    candidate = Path(__file__).resolve().parents[3]
    return candidate if (candidate / "apps" / "api").is_dir() else None


def _poll_seconds(env):
    raw = (env.get(ENV_POLL_SECONDS) or "").strip()
    if not raw:
        return DEFAULT_POLL_SECONDS
    try:
        value = float(raw)
    except ValueError as error:
        raise ConfigError(f"{ENV_POLL_SECONDS} must be a number of seconds from 1 to 60.") from error
    if not 1 <= value <= 60:
        raise ConfigError(f"{ENV_POLL_SECONDS} must be a number of seconds from 1 to 60.")
    return value


def _check_home(env):
    """The home directory must hold the Claude settings file that every sandbox mounts read-only."""
    home = (env.get("HOME") or "").strip()
    if not home or not os.path.isabs(home) or not os.path.isdir(home):
        raise ConfigError(
            "HOME must be the absolute path of the Worker user's home directory, where Claude Code keeps its settings."
        )
    settings = Path(home) / ".claude" / "settings.json"
    if not settings.is_file():
        raise ConfigError(
            f"{settings} is missing. Configure Claude Code on this machine first: the sandboxes read its settings."
        )
    return Path(home)


def _sandbox_memory(env):
    value = (env.get(ENV_SANDBOX_MEMORY) or "").strip()
    if value and not MEMORY_PATTERN.match(value):
        raise ConfigError(f"{ENV_SANDBOX_MEMORY} must be a size such as 4096m or 8g.")
    return value or None


def _mcp_port(env):
    raw = (env.get(ENV_MCP_PORT) or "").strip()
    if not raw:
        return DEFAULT_MCP_PORT
    if not raw.isdigit() or not 1 <= int(raw) <= 65535:
        raise ConfigError(f"{ENV_MCP_PORT} must be a TCP port from 1 to 65535.")
    return int(raw)


def _names(env, name):
    return tuple(item.strip() for item in (env.get(name) or "").split(",") if item.strip())


def _allowed_ips(env):
    try:
        return tuple(ipaddress.ip_network(item, strict=False) for item in _names(env, ENV_GIT_ALLOWED_IPS))
    except ValueError as error:
        raise ConfigError(
            f"{ENV_GIT_ALLOWED_IPS} must be a comma-separated list of IP addresses or networks."
        ) from error


def load_config(env):
    home = _check_home(env)
    origin = validate_origin((env.get(ENV_ORIGIN) or "").strip())
    run_root = _absolute(env, ENV_RUN_ROOT)
    token_file = _absolute(env, ENV_TOKEN_FILE)
    checkout = _absolute(env, ENV_PLANE_CHECKOUT, required=False) or default_plane_checkout()
    if checkout is None:
        raise ConfigError(f"{ENV_PLANE_CHECKOUT} is required when the Worker does not run from a Plane checkout.")

    run_root = Path(os.path.realpath(run_root))
    checkout = Path(os.path.realpath(checkout))
    if _is_within(run_root, checkout) or _is_within(checkout, run_root):
        raise ConfigError(f"{ENV_RUN_ROOT} must be outside the Plane checkout, and the checkout outside it.")
    # The real parent directory decides containment; the file itself must not be a link (checked on read).
    token_location = Path(os.path.realpath(token_file.parent)) / token_file.name
    if _is_within(token_location, run_root):
        raise ConfigError("The token file must be outside the Run root, where Harness processes can read.")

    _prepare_run_root(run_root)
    read_token_file(token_file)

    sbx_bin = (env.get(ENV_SBX_BIN) or "").strip() or shutil.which("sbx", path=env.get("PATH"))
    return WorkerConfig(
        api_origin=origin,
        token_file=token_file,
        run_root=run_root,
        plane_checkout=checkout,
        home=home,
        sbx_bin=sbx_bin,
        sandbox_memory=_sandbox_memory(env),
        poll_seconds=_poll_seconds(env),
        mcp_port=_mcp_port(env),
        import_mcp_servers=_names(env, ENV_IMPORT_MCP_SERVERS),
        git_allowed_hosts=frozenset(host.lower() for host in _names(env, ENV_GIT_ALLOWED_HOSTS)),
        git_allowed_ips=_allowed_ips(env),
    )
