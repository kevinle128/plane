# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The only HTTP seam for Git provider calls.

Every GitHub and GitLab request goes through :func:`request`. It uses
``pinned_fetch`` (resolve once, validate, pin the IP, no redirects, no proxy)
with the operator allowlists ``AGENT_GIT_ALLOWED_HOSTS`` and
``AGENT_GIT_ALLOWED_IPS``, caps the response body, enforces per-read
timeouts and an absolute deadline per call, and maps transport failures to
fixed reason codes of the form ``<provider>_<reason>``. The deadline is a
:class:`SocketDeadline` armed before the connection opens: when it passes,
the socket is shut down, so a server that sends the status line, headers,
chunk-size lines, body or trailers one byte at a time cannot hold the call
past its budget. A connection CA
bundle is written to a private file and passed as ``verify`` for that
request only; every other request keeps system trust. Tests replace
:func:`request` and nothing else.

Log lines carry the method, scheme, host, path and status only. Headers,
query strings and bodies can hold tokens, so they are never logged.
"""

# Python imports
import hashlib
import json
import logging
import os
import socket
import stat
import tempfile
import time
from dataclasses import dataclass, field
from urllib.parse import urlencode, urljoin, urlsplit

# Third party imports
import requests
import urllib3
from django.conf import settings

# Module imports
from plane.agent.git_providers.base import ProviderError
from plane.utils.url_security import SocketDeadline, pinned_fetch

logger = logging.getLogger("plane.agent.git_providers.http")

CONNECT_TIMEOUT_SECONDS = 5
READ_TIMEOUT_SECONDS = 10
# Total time for one call that has no shared deadline, body read included.
CALL_BUDGET_SECONDS = 30
MAX_RESPONSE_BYTES = 1024 * 1024
_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: dict = field(default_factory=dict)
    content: bytes = b""

    def header(self, name, default=None):
        lowered = name.lower()
        for key, value in self.headers.items():
            if key.lower() == lowered:
                return value
        return default

    def json(self):
        """Return the decoded JSON body, or ``None`` when the body is not JSON."""
        try:
            return json.loads(self.content.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError):
            # A deeply nested body from a hostile server raises RecursionError.
            return None

    def json_object(self):
        """Return the decoded body when it is a JSON object, else an empty dict."""
        body = self.json()
        return body if isinstance(body, dict) else {}


def new_deadline(seconds):
    """Return a deadline for a sequence of calls that share one time budget."""
    return time.monotonic() + seconds


def _ca_bundle_directory():
    """A directory that only this OS user can read; refuse one that someone else owns."""
    directory = os.path.join(tempfile.gettempdir(), f"plane-agent-git-ca-{os.getuid()}")
    os.makedirs(directory, mode=0o700, exist_ok=True)
    info = os.lstat(directory)
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise RuntimeError("CA bundle directory is not a private directory of this user")
    os.chmod(directory, 0o700)
    return directory


def ca_bundle_path(pem):
    """Write ``pem`` once to a private file named by its SHA-256 and return the path.

    The file is written under a temporary name and renamed into place, so a
    concurrent reader never sees a partial bundle.
    """
    directory = _ca_bundle_directory()
    path = os.path.join(directory, f"{hashlib.sha256(pem.encode()).hexdigest()}.pem")
    if not os.path.exists(path):
        descriptor, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(descriptor, "w") as handle:
                handle.write(pem)
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        except BaseException:
            if os.path.exists(temporary):
                os.unlink(temporary)
            raise
    return path


def _timeout_error(provider):
    return ProviderError(f"{provider}_url_unreachable", provider, "timeout", http_status=502)


def _remaining(provider, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise _timeout_error(provider)
    return remaining


def _redacted_target(url):
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.hostname}{parts.path}"


def _redirect_origin(url, location):
    target = urlsplit(urljoin(url, location or ""))
    return f"{target.scheme}://{target.hostname}" if target.hostname else ""


def _limit_socket_wait(raw, seconds):
    """Make the next socket read wait at most ``seconds``."""
    sock = getattr(getattr(raw, "connection", None), "sock", None)
    if sock is not None:
        sock.settimeout(seconds)


def _read_capped(response, provider, max_bytes, deadline):
    """Read the body with a size cap and stop when ``deadline`` passes.

    ``read1`` makes at most one socket read, so the deadline is checked
    between reads even when a server sends one byte at a time. A buffered
    read (``iter_content``) would wait for a full chunk and skip the check.
    The body is read without decoding: ``request`` asks for ``identity`` and
    refuses an encoded body, because decoding can join many reads into one.
    """
    raw = response.raw
    chunks = []
    total = 0
    while True:
        _limit_socket_wait(raw, min(READ_TIMEOUT_SECONDS, _remaining(provider, deadline)))
        chunk = raw.read1(_CHUNK_BYTES, decode_content=False)
        if not chunk:
            # A connection that the deadline shut down while trailers were
            # read also ends with an empty read, so check the deadline again.
            _remaining(provider, deadline)
            return b"".join(chunks)
        total += len(chunk)
        if total > max_bytes:
            raise ProviderError(f"{provider}_unexpected_response", provider, "response_too_large", http_status=502)
        chunks.append(chunk)


def _fetch_error(error, provider, method, url, deadline_expired):
    """Map an error of ``pinned_fetch`` to a :class:`ProviderError`.

    After the deadline shut the socket down, the error can be any transport
    error (even a TLS error), so the deadline decides first.
    """
    target = _redacted_target(url)
    if deadline_expired or isinstance(error, requests.exceptions.Timeout):
        logger.warning("provider timeout: %s %s", method, target)
        return _timeout_error(provider)
    if isinstance(error, ValueError):
        logger.warning("provider request blocked: %s %s", method, target)
        return ProviderError(f"{provider}_url_not_allowed_or_unresolved", provider, http_status=400)
    if isinstance(error, requests.exceptions.SSLError):
        logger.warning("provider TLS failure: %s %s", method, target)
        return ProviderError(f"{provider}_tls_failed", provider, http_status=502)
    logger.warning("provider connection failure: %s %s", method, target)
    return ProviderError(f"{provider}_url_unreachable", provider, "connection", http_status=502)


def request(
    method,
    url,
    *,
    provider,
    headers=None,
    params=None,
    data=None,
    json_body=None,
    auth=None,
    ca_bundle=None,
    deadline=None,
    max_bytes=MAX_RESPONSE_BYTES,
):
    """Send one provider request and return an :class:`HttpResponse`.

    Raises :class:`ProviderError` for transport failures, a redirect, an
    encoded body, or a body larger than ``max_bytes``. A call without a
    shared ``deadline`` gets its own budget of ``CALL_BUDGET_SECONDS``. HTTP
    error statuses are returned, not raised, so each caller maps them to its
    own reason codes.
    """
    if deadline is None:
        deadline = new_deadline(CALL_BUDGET_SECONDS)
    remaining = _remaining(provider, deadline)
    timeout = (min(CONNECT_TIMEOUT_SECONDS, remaining), min(READ_TIMEOUT_SECONDS, remaining))
    target = f"{url}?{urlencode(params)}" if params else url
    headers = {**(headers or {}), "Accept-Encoding": "identity"}
    extra = {}
    if data is not None:
        extra["data"] = data
    if json_body is not None:
        extra["json"] = json_body
    if auth is not None:
        extra["auth"] = auth

    with SocketDeadline(remaining) as socket_deadline:
        try:
            response = pinned_fetch(
                method,
                target,
                headers=headers,
                timeout=timeout,
                stream=True,
                verify=ca_bundle_path(ca_bundle) if ca_bundle else True,
                allowed_hosts=settings.AGENT_GIT_ALLOWED_HOSTS,
                allowed_ips=settings.AGENT_GIT_ALLOWED_IPS,
                on_socket=socket_deadline.attach,
                **extra,
            )
        except (ValueError, requests.exceptions.RequestException) as error:
            raise _fetch_error(error, provider, method, url, socket_deadline.expired)

        try:
            if 300 <= response.status_code < 400:
                origin = _redirect_origin(url, response.headers.get("Location"))
                logger.warning("provider redirect refused: %s %s -> %s", method, _redacted_target(url), origin)
                raise ProviderError(f"{provider}_url_redirected", provider, origin, http_status=502)
            if (response.headers.get("Content-Encoding") or "identity").strip().lower() != "identity":
                raise ProviderError(f"{provider}_unexpected_response", provider, "content_encoding", http_status=502)
            content = _read_capped(response, provider, max_bytes, deadline)
            if socket_deadline.expired:
                raise _timeout_error(provider)
        except (requests.exceptions.Timeout, urllib3.exceptions.TimeoutError, socket.timeout):
            logger.warning("provider body read timeout: %s %s", method, _redacted_target(url))
            raise _timeout_error(provider)
        except (requests.exceptions.RequestException, urllib3.exceptions.HTTPError, OSError):
            if socket_deadline.expired:
                logger.warning("provider body read timeout: %s %s", method, _redacted_target(url))
                raise _timeout_error(provider)
            raise ProviderError(f"{provider}_url_unreachable", provider, "connection", http_status=502)
        finally:
            response.close()

    logger.info("provider request: %s %s -> %s", method, _redacted_target(url), response.status_code)
    return HttpResponse(status_code=response.status_code, headers=dict(response.headers), content=content)
