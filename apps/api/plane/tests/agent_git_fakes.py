# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Test doubles for the Git provider HTTP seam.

Every provider call in ``plane.agent`` goes through
``plane.agent.git_providers.http.request``. Tests replace that one function
with :class:`FakeProviderHttp`, so no test opens a network connection.
"""

import json
import threading
from pathlib import Path
from urllib.parse import urlsplit

from plane.agent.git_providers.base import ProviderError
from plane.agent.git_providers.http import HttpResponse

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(*parts):
    """Load a JSON fixture from ``plane/tests/fixtures``."""
    with open(FIXTURES_DIR.joinpath(*parts), encoding="utf-8") as handle:
        return json.load(handle)


def json_response(status_code=200, body=None, headers=None):
    payload = b"" if body is None else json.dumps(body).encode()
    all_headers = {"Content-Type": "application/json"}
    all_headers.update(headers or {})
    return HttpResponse(status_code=status_code, headers=all_headers, content=payload)


def text_response(status_code=200, text="", headers=None):
    all_headers = {"Content-Type": "text/html"}
    all_headers.update(headers or {})
    return HttpResponse(status_code=status_code, headers=all_headers, content=text.encode())


class FakeProviderHttp:
    """Route provider requests to scripted responses.

    Routes are keyed by ``(METHOD, path)`` where ``path`` is the URL path
    without the query string, optionally prefixed by the host
    (``"github.com/login/device/code"``). A route value is a response, an
    exception, a callable ``(call) -> response`` or a list of these that is
    consumed in order (the last item repeats).
    """

    def __init__(self):
        self.routes = {}
        self.calls = []
        self._lock = threading.Lock()

    def add(self, method, path, *responses):
        self.routes[(method.upper(), path)] = list(responses)
        return self

    def count(self, method=None, path=None):
        return len(
            [
                call
                for call in self.calls
                if (method is None or call["method"] == method.upper())
                and (path is None or path in (call["path"], call["host_path"]))
            ]
        )

    def __call__(self, method, url, **kwargs):
        parts = urlsplit(url)
        call = {
            "method": method.upper(),
            "url": url,
            "host": parts.hostname,
            "path": parts.path,
            "host_path": f"{parts.hostname}{parts.path}",
            "query": parts.query,
            **kwargs,
        }
        with self._lock:
            self.calls.append(call)
            responses = self.routes.get((call["method"], call["host_path"])) or self.routes.get(
                (call["method"], call["path"])
            )
            if responses is None:
                raise AssertionError(f"Unexpected provider call: {method} {url}")
            item = responses[0] if len(responses) == 1 else responses.pop(0)
        if callable(item) and not isinstance(item, HttpResponse):
            item = item(call)
        if isinstance(item, (Exception, ProviderError)):
            raise item
        return item


def install_fake_http(mocker, fake=None):
    """Patch the provider HTTP seam with ``fake`` and return it."""
    fake = fake or FakeProviderHttp()
    mocker.patch("plane.agent.git_providers.http.request", side_effect=fake)
    return fake
