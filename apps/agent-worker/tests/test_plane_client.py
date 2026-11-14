# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from plane_agent_worker.plane_client import MAX_RESPONSE_BYTES, PlaneClient, PlaneClientError, ProbeRejected

TOKEN = "plane_aw_client-test-token-0001"


class Recorder:
    def __init__(self):
        self.requests = []
        self.responses = {}

    def respond(self, path, status, body, headers=None):
        self.responses[path] = (status, body, headers or {})


def start_server(recorder):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            recorder.requests.append({"path": self.path, "headers": dict(self.headers), "body": body})
            status, payload, headers = recorder.responses.get(self.path, (200, {}, {}))
            raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


@pytest.fixture
def plane():
    recorder = Recorder()
    server = start_server(recorder)
    recorder.origin = f"http://127.0.0.1:{server.server_address[1]}"
    yield recorder
    server.shutdown()
    server.server_close()


def test_heartbeat_sends_the_token_as_bearer_and_never_as_api_key(plane):
    plane.respond("/api/agent-worker/v1/heartbeat/", 200, {"worker": "mini"})

    result = PlaneClient(plane.origin, TOKEN).heartbeat()

    assert result == {"worker": "mini"}
    headers = {name.lower(): value for name, value in plane.requests[0]["headers"].items()}
    assert headers["authorization"] == f"Bearer {TOKEN}"
    assert "x-api-key" not in headers
    assert headers["content-type"] == "application/json"


def test_claim_posts_the_harness_list_and_returns_the_probe(plane):
    probe = {"id": "p1", "harness": "claude_code", "generation": 3, "requested_at": "2026-11-13T00:00:00Z"}
    plane.respond("/api/agent-worker/v1/probes/claim/", 200, {"probe": probe})

    assert PlaneClient(plane.origin, TOKEN).claim_probe(["claude_code"]) == probe
    assert json.loads(plane.requests[0]["body"]) == {"harnesses": ["claude_code"]}


def test_claim_without_a_pending_probe_returns_none(plane):
    plane.respond("/api/agent-worker/v1/probes/claim/", 200, {"probe": None})

    assert PlaneClient(plane.origin, TOKEN).claim_probe(["claude_code"]) is None


def test_report_conflict_raises_probe_rejected_with_the_code(plane):
    plane.respond("/api/agent-worker/v1/probes/p1/report/", 409, {"error": "probe_superseded"})

    with pytest.raises(ProbeRejected) as error:
        PlaneClient(plane.origin, TOKEN).report_probe("p1", {"version": 1})

    assert error.value.code == "probe_superseded"


def test_redirect_is_not_followed(plane):
    other = Recorder()
    other_server = start_server(other)
    try:
        target = f"http://127.0.0.1:{other_server.server_address[1]}/api/agent-worker/v1/heartbeat/"
        plane.respond("/api/agent-worker/v1/heartbeat/", 302, {}, {"Location": target})

        with pytest.raises(PlaneClientError) as error:
            PlaneClient(plane.origin, TOKEN).heartbeat()

        assert error.value.status == 302
        assert other.requests == []
    finally:
        other_server.shutdown()
        other_server.server_close()


def test_proxy_environment_is_ignored(plane, monkeypatch):
    for name in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.setenv(name, "http://127.0.0.1:9")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    plane.respond("/api/agent-worker/v1/heartbeat/", 200, {"worker": "mini"})
    client = PlaneClient(plane.origin, TOKEN)

    assert client.heartbeat() == {"worker": "mini"}
    # A default opener would carry the proxies from the environment above.
    assert urllib.request.build_opener().handlers[0].proxies
    assert not [h for h in client.opener.handlers if isinstance(h, urllib.request.ProxyHandler) and h.proxies]


def test_error_does_not_contain_the_token(plane):
    plane.respond("/api/agent-worker/v1/heartbeat/", 401, {"detail": "Invalid worker token."})

    with pytest.raises(PlaneClientError) as error:
        PlaneClient(plane.origin, TOKEN).heartbeat()

    assert error.value.status == 401
    assert TOKEN not in str(error.value)
    assert TOKEN not in repr(error.value)


def test_client_repr_does_not_contain_the_token(plane):
    assert TOKEN not in repr(PlaneClient(plane.origin, TOKEN))


def test_oversized_response_is_rejected(plane):
    plane.respond("/api/agent-worker/v1/heartbeat/", 200, b"[" + b"0," * MAX_RESPONSE_BYTES + b"0]")

    with pytest.raises(PlaneClientError, match="too large"):
        PlaneClient(plane.origin, TOKEN).heartbeat()


def test_unreachable_plane_raises_a_client_error():
    with pytest.raises(PlaneClientError):
        PlaneClient("http://127.0.0.1:9", TOKEN, timeout=2).heartbeat()
