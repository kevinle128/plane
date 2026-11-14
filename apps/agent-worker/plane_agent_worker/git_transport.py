# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Clone a Run repository with git over HTTPS.

Rules for every git command:
- ``http.followRedirects=false``: with the default (``initial``) git uses a redirect
  target as the base URL of later requests.
- ``core.askPass=`` and ``GIT_TERMINAL_PROMPT=0`` (and no ``GIT_ASKPASS`` or
  ``SSH_ASKPASS``, which override ``core.askPass``): git never prompts.
- The Worker resolves the clone host itself and refuses blocked addresses (the rule of
  ``plane/utils/ip_address.py:is_blocked_ip``), unless the host or the address is in the
  operator allowlist. ``http.curloptResolve`` pins git to the checked addresses. One
  Worker serves every workspace, so a workspace admin must not steer it to the LAN or
  loopback of the Worker machine.
- The CA bundle is a file in a private folder, set only for the URL base of the clone.

Credential modes:
- ``host``: git uses the credentials of the Worker machine (its normal git config).
- ``plane_token``: ``credential.helper=`` (an empty value clears the helper list, so no
  system helper such as ``osxkeychain`` gets or stores the token), then
  ``git_credential_pipe.py``, which reads the token from an inherited pipe. The token is
  never in argv, the environment, the remote URL, ``.git/config``, a file or a log.
"""

import ipaddress
import logging
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

CLONE_TIMEOUT_SECONDS = 600
COMMAND_TIMEOUT_SECONDS = 60
MAX_DETAIL = 500
PIPE_HELPER = Path(__file__).with_name("git_credential_pipe.py")
# These variables override ``core.askPass``.
PROMPT_VARIABLES = ("GIT_ASKPASS", "SSH_ASKPASS")

logger = logging.getLogger("plane_agent_worker.git_transport")

# Same list as ``plane/utils/ip_address.py``: networks that the ``ipaddress`` flags do not
# classify the same way on every Python version.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network(cidr)
    for cidr in (
        "0.0.0.0/8",
        "100.64.0.0/10",
        "169.254.0.0/16",
        "255.255.255.255/32",
        "::ffff:0:0/96",
        "64:ff9b::/96",
        "64:ff9b:1::/48",
        "2002::/16",
        "2001::/32",
        "fec0::/10",
    )
]
_NAT64 = ipaddress.ip_network("64:ff9b::/96")

# Checked in order; the first match gives the code.
_FAILURE_PATTERNS = (
    ("git_dns_failed", re.compile(r"could not resolve host", re.IGNORECASE)),
    ("git_unreachable", re.compile(r"connection refused|timed out|couldn't connect|failed to connect", re.IGNORECASE)),
    ("git_tls_failed", re.compile(r"ssl certificate problem|server certificate verification failed", re.IGNORECASE)),
    (
        "git_auth_failed",
        re.compile(r"authentication failed|returned error: 40[13]\b|could not read username", re.IGNORECASE),
    ),
    ("git_not_found", re.compile(r"\brepository\b.*\bnot found|returned error: 404\b", re.IGNORECASE)),
)


class GitTransportError(Exception):
    """A clone failed.

    ``code`` is ``git_dns_failed``, ``git_unreachable``, ``git_tls_failed``,
    ``git_auth_failed``, ``git_not_found``, ``git_failed`` or ``git_host_blocked``.
    ``detail`` has at most 500 characters and never contains the token.
    """

    def __init__(self, code, detail=""):
        detail = detail[:MAX_DETAIL]
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _embedded_ipv4(ip):
    """The IPv4 addresses inside an IPv6 transition address (mapped, 6to4, Teredo, NAT64)."""
    if ip.version != 6:
        return
    if ip.ipv4_mapped is not None:
        yield ip.ipv4_mapped
    if ip.sixtofour is not None:
        yield ip.sixtofour
    if ip.teredo is not None:
        yield from ip.teredo
    if ip in _NAT64:
        yield ipaddress.ip_address(int(ip) & 0xFFFFFFFF)


def is_blocked_ip(ip):
    """True when ``ip`` must not be a clone target: a copy of Plane's ``is_blocked_ip`` rule."""
    if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return True
    if any(ip.version == net.version and ip in net for net in _BLOCKED_NETWORKS):
        return True
    return any(is_blocked_ip(embedded) for embedded in _embedded_ipv4(ip))


def failure_code(stderr):
    """The ``git_*`` code for the stderr text of a failed git command."""
    for code, pattern in _FAILURE_PATTERNS:
        if pattern.search(stderr or ""):
            return code
    return "git_failed"


def _resolve(hostname, port, allowed_hosts, allowed_ips):
    """The checked addresses of ``hostname``, in resolver order."""
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as error:
        raise GitTransportError("git_dns_failed", f"Could not resolve host: {hostname}") from error
    trusted_host = hostname.rstrip(".").lower() in {name.rstrip(".").lower() for name in allowed_hosts if name}
    addresses = []
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        allowed = any(net.version == ip.version and ip in net for net in allowed_ips)
        if not trusted_host and not allowed and is_blocked_ip(ip):
            raise GitTransportError("git_host_blocked", f"{hostname} resolves to a blocked address")
        if ip not in addresses:
            addresses.append(ip)
    if not addresses:
        raise GitTransportError("git_dns_failed", f"Could not resolve host: {hostname}")
    return addresses


def _pin_option(hostname, port, addresses):
    """``http.curloptResolve`` for a host name; an IP literal needs no pin."""
    try:
        ipaddress.ip_address(hostname)
        return []
    except ValueError:
        pass
    pinned = ",".join(f"[{ip}]" if ip.version == 6 else str(ip) for ip in addresses)
    return ["-c", f"http.curloptResolve={hostname}:{port}:{pinned}"]


def _write_ca_bundle(ca_dir, ca_bundle):
    path = Path(ca_dir) / "ca.pem"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(ca_bundle)
    return path


def _git_env(env):
    git_env = dict(os.environ if env is None else env)
    for name in PROMPT_VARIABLES:
        git_env.pop(name, None)
    git_env["GIT_TERMINAL_PROMPT"] = "0"
    return git_env


def _detail(stderr, token):
    lines = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
    detail = " ".join(line for line in lines if not line.startswith("Cloning into"))
    if token:
        detail = detail.replace(token, "[token]")
    return detail[-MAX_DETAIL:]


def _run_git(args, env, timeout, token="", pass_fds=()):
    try:
        result = subprocess.run(
            ["git", *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
            pass_fds=pass_fds,
        )
    except FileNotFoundError as error:
        raise GitTransportError("git_failed", "The git command was not found on the Worker machine.") from error
    except subprocess.TimeoutExpired as error:
        raise GitTransportError("git_unreachable", f"git did not finish in {timeout} s") from error
    if result.returncode != 0:
        raise GitTransportError(failure_code(result.stderr), _detail(result.stderr, token))
    return result.stdout


def _clone(transport, clone_url, destination, branch, env, token):
    args = [*transport]
    pass_fds = ()
    read_end = None
    if token:
        read_end, write_end = os.pipe()
        try:
            os.write(write_end, token.encode())
        finally:
            os.close(write_end)
        host = urlsplit(clone_url).netloc
        helper = f"!{shlex.quote(sys.executable)} {shlex.quote(str(PIPE_HELPER))} {read_end} {shlex.quote(host)}"
        args += ["-c", "credential.helper=", "-c", f"credential.helper={helper}"]
        pass_fds = (read_end,)
    args += ["clone", "--depth", "1", "--single-branch", "--no-tags"]
    if branch:
        args += ["--branch", branch]
    args += ["--", clone_url, str(destination)]
    try:
        _run_git(args, env, CLONE_TIMEOUT_SECONDS, token=token, pass_fds=pass_fds)
    finally:
        if read_end is not None:
            os.close(read_end)


def clone_repository(
    *,
    clone_url: str,
    host: str,
    credential_mode: str,
    destination: Path,
    ca_bundle: str | None,
    ca_dir: Path,
    fetch_token: Callable[[], str],
    allowed_hosts: frozenset[str] = frozenset(),
    allowed_ips: tuple = (),
    branch: str | None = None,
    env: dict | None = None,
) -> None:
    """Shallow-clone ``clone_url`` into ``destination`` (which must not exist), or raise ``GitTransportError``."""
    destination = Path(destination)
    if credential_mode not in ("host", "plane_token"):
        raise GitTransportError("git_failed", f"Unknown credential mode: {credential_mode}")
    parts = urlsplit(clone_url)
    if parts.scheme != "https":
        raise GitTransportError("git_host_blocked", "Only https clone URLs are allowed.")
    if parts.username is not None or parts.password is not None:
        raise GitTransportError("git_failed", "The clone URL must not contain credentials.")
    if parts.netloc != host or not parts.hostname:
        raise GitTransportError("git_failed", f"The clone URL host does not match {host}.")
    try:
        port = parts.port or 443
    except ValueError as error:
        raise GitTransportError("git_failed", f"The clone URL port is not valid: {host}") from error
    if destination.exists() or destination.is_symlink():
        raise GitTransportError("git_failed", "The clone destination exists already.")

    addresses = _resolve(parts.hostname, port, allowed_hosts, allowed_ips)

    token = ""
    if credential_mode == "plane_token":
        token = fetch_token()
        if not token or any(char in token for char in "\r\n\x00"):
            raise GitTransportError("git_auth_failed", "The fetch credential from Plane is not valid.")

    git_env = _git_env(env)
    transport = [
        "-c",
        "http.followRedirects=false",
        "-c",
        "core.askPass=",
        *_pin_option(parts.hostname, port, addresses),
    ]
    if ca_bundle:
        ca_file = _write_ca_bundle(ca_dir, ca_bundle)
        transport += ["-c", f"http.{parts.scheme}://{host}/.sslCAInfo={ca_file}"]

    logger.info("Cloning %s (%s credentials) into %s", clone_url, credential_mode, destination)
    try:
        _clone(transport, clone_url, destination, branch, git_env, token)
        local = [*transport, "-C", str(destination), "remote"]
        _run_git([*local, "set-url", "origin", clone_url], git_env, COMMAND_TIMEOUT_SECONDS)
        remote = _run_git([*local, "get-url", "origin"], git_env, COMMAND_TIMEOUT_SECONDS).strip()
        if remote != clone_url:
            raise GitTransportError("git_failed", "The clone remote URL does not match the clone URL.")
    except GitTransportError as error:
        logger.warning("Clone of %s failed: %s %s", clone_url, error.code, error.detail)
        shutil.rmtree(destination, ignore_errors=True)
        raise
