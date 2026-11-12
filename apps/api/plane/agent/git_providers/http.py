# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The only HTTP seam for Git provider calls.

Every GitHub and GitLab request goes through :func:`request`. It uses
``pinned_fetch`` (resolve once, validate, pin the IP, no redirects, no proxy),
caps the response body, enforces per-call timeouts and an optional total
deadline, and maps transport failures to fixed reason codes of the form
``<provider>_<reason>``. Tests replace :func:`request` and nothing else.

Log lines carry the method, scheme, host, path and status only. Headers,
query strings and bodies can hold tokens, so they are never logged.
"""

# Python imports
import json
import logging
import time
from dataclasses import dataclass, field
from urllib.parse import urlencode, urljoin, urlsplit

# Third party imports
import requests

# Module imports
from plane.agent.git_providers.base import ProviderError
from plane.utils.url_security import pinned_fetch

logger = logging.getLogger("plane.agent.git_providers.http")

CONNECT_TIMEOUT_SECONDS = 5
READ_TIMEOUT_SECONDS = 10
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
        except (UnicodeDecodeError, ValueError):
            return None


def new_deadline(seconds):
    """Return a deadline for a sequence of calls that share one time budget."""
    return time.monotonic() + seconds


def _timeouts(provider, deadline):
    timeout = (CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)
    if deadline is None:
        return timeout
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ProviderError(f"{provider}_url_unreachable", provider, "timeout", http_status=502)
    return (min(timeout[0], remaining), min(timeout[1], remaining))


def _redacted_target(url):
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.hostname}{parts.path}"


def _redirect_origin(url, location):
    target = urlsplit(urljoin(url, location or ""))
    return f"{target.scheme}://{target.hostname}" if target.hostname else ""


def _read_capped(response, provider, max_bytes):
    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=_CHUNK_BYTES):
        total += len(chunk)
        if total > max_bytes:
            raise ProviderError(f"{provider}_unexpected_response", provider, "response_too_large", http_status=502)
        chunks.append(chunk)
    return b"".join(chunks)


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
    deadline=None,
    max_bytes=MAX_RESPONSE_BYTES,
):
    """Send one provider request and return an :class:`HttpResponse`.

    Raises :class:`ProviderError` for transport failures, a redirect, or a
    body larger than ``max_bytes``. HTTP error statuses are returned, not
    raised, so each caller maps them to its own reason codes.
    """
    timeout = _timeouts(provider, deadline)
    target = f"{url}?{urlencode(params)}" if params else url
    extra = {}
    if data is not None:
        extra["data"] = data
    if json_body is not None:
        extra["json"] = json_body
    if auth is not None:
        extra["auth"] = auth

    try:
        response = pinned_fetch(method, target, headers=headers, timeout=timeout, stream=True, **extra)
    except ValueError:
        logger.warning("provider request blocked: %s %s", method, _redacted_target(url))
        raise ProviderError(f"{provider}_url_not_allowed_or_unresolved", provider, http_status=400)
    except requests.exceptions.SSLError:
        logger.warning("provider TLS failure: %s %s", method, _redacted_target(url))
        raise ProviderError(f"{provider}_tls_failed", provider, http_status=502)
    except requests.exceptions.Timeout:
        logger.warning("provider timeout: %s %s", method, _redacted_target(url))
        raise ProviderError(f"{provider}_url_unreachable", provider, "timeout", http_status=502)
    except requests.exceptions.RequestException:
        logger.warning("provider connection failure: %s %s", method, _redacted_target(url))
        raise ProviderError(f"{provider}_url_unreachable", provider, "connection", http_status=502)

    try:
        if 300 <= response.status_code < 400:
            origin = _redirect_origin(url, response.headers.get("Location"))
            logger.warning("provider redirect refused: %s %s -> %s", method, _redacted_target(url), origin)
            raise ProviderError(f"{provider}_url_redirected", provider, origin, http_status=502)
        content = _read_capped(response, provider, max_bytes)
    except requests.exceptions.RequestException:
        raise ProviderError(f"{provider}_url_unreachable", provider, "connection", http_status=502)
    finally:
        response.close()

    logger.info("provider request: %s %s -> %s", method, _redacted_target(url), response.status_code)
    return HttpResponse(status_code=response.status_code, headers=dict(response.headers), content=content)
