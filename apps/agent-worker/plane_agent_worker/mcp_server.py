# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The Plane MCP server of the Worker, over HTTP on host loopback.

Claude runs inside a sandbox VM that does not have the Worker package, so the
Worker serves the Plane tools itself: a small MCP endpoint (JSON-RPC over HTTP,
JSON answers only) on ``127.0.0.1:<PLANE_AGENT_MCP_PORT>``. The VM reaches it at
``host.docker.internal:<port>`` through one sandbox allow rule.

Each turn gets a random handle in its MCP config (``Authorization: Bearer``). The
handle maps to one (Run, turn, lease generation) and its context snapshot, and is
dropped when the turn ends; an unknown or dropped handle gets 401. The handle is
visible inside the sandbox and carries no Worker or provider token, so a leaked
handle gives only the Plane tools of that turn while it runs.

The operator can list more MCP servers by name (``PLANE_AGENT_IMPORT_MCP_SERVERS``,
for example the Archon server); their definitions come from ``mcpServers`` in the
host ``~/.claude.json`` and go into each turn's MCP config. An HTTP server gets a
sandbox allow rule for its host.
"""

import json
import logging
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from plane_agent_worker.config import ConfigError

SERVER_NAME = "plane"
VM_HOST = "host.docker.internal"
DEFAULT_PROTOCOL_VERSION = "2025-06-18"
MAX_REQUEST_BYTES = 1024 * 1024
ISSUE_CONTEXT_TOOL = {
    "name": "plane_issue_context",
    "description": "The Plane work item of this Run: workspace, project, title, description, state, repository, "
    "requester, the comment to answer and earlier comments.",
    "inputSchema": {"type": "object", "properties": {}},
}

logger = logging.getLogger("plane_agent_worker.mcp_server")


def turn_mcp_config(port, handle, imported):
    """The MCP config file of one turn: the Plane server with the turn handle, then the listed servers."""
    servers = {
        SERVER_NAME: {
            "type": "http",
            "url": f"http://{VM_HOST}:{port}/mcp",
            "headers": {"Authorization": f"Bearer {handle}"},
        }
    }
    servers.update(imported)
    return {"mcpServers": servers}


def load_imported_servers(names, home):
    """The listed server definitions from ``mcpServers`` in ``~/.claude.json``. An unknown name is a config error."""
    if not names:
        return {}
    try:
        document = json.loads((Path(home) / ".claude.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ConfigError(
            f"~/.claude.json cannot be read for the listed MCP servers ({type(error).__name__})."
        ) from error
    servers = document.get("mcpServers") if isinstance(document, dict) else None
    servers = servers if isinstance(servers, dict) else {}
    missing = [name for name in names if not isinstance(servers.get(name), dict)]
    if missing:
        raise ConfigError(f"MCP servers not found in ~/.claude.json mcpServers: {', '.join(missing)}")
    return {name: servers[name] for name in names}


def imported_allow_rules(servers):
    """``host:port`` of each listed HTTP or SSE server; stdio servers run inside the VM and need none."""
    rules = []
    for definition in servers.values():
        url = urlsplit(str(definition.get("url") or ""))
        if definition.get("type") in ("http", "sse") and url.hostname and url.scheme in ("http", "https"):
            rules.append(f"{url.hostname}:{url.port or (443 if url.scheme == 'https' else 80)}")
    return tuple(dict.fromkeys(rules))


class PlaneMcpServer:
    def __init__(self, port, host="127.0.0.1"):
        self._turns = {}
        self._lock = threading.Lock()
        self._httpd = ThreadingHTTPServer((host, port), self._handler_class())
        self._httpd.daemon_threads = True
        self.port = self._httpd.server_address[1]
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        self._httpd.shutdown()
        self._httpd.server_close()

    def open_turn(self, *, run_id, turn_index, lease_generation, context):
        handle = secrets.token_urlsafe(32)
        with self._lock:
            self._turns[handle] = {
                "run_id": run_id,
                "turn_index": turn_index,
                "lease_generation": lease_generation,
                "context": context,
            }
        return handle

    def close_turn(self, handle):
        with self._lock:
            self._turns.pop(handle, None)

    def _turn(self, handle):
        with self._lock:
            return self._turns.get(handle)

    def answer(self, turn, request):
        """The JSON-RPC answer to ``request``, or ``None`` for a notification."""
        if "id" not in request:
            return None
        method = request.get("method")
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        if method == "initialize":
            result = {
                "protocolVersion": params.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": "1"},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [ISSUE_CONTEXT_TOOL]}
        elif method == "tools/call" and params.get("name") == ISSUE_CONTEXT_TOOL["name"]:
            text = json.dumps(turn["context"], ensure_ascii=False)
            result = {"content": [{"type": "text", "text": text}]}
        elif method == "tools/call":
            return {"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32602, "message": "Unknown tool"}}
        else:
            return {"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32601, "message": "Method not found"}}
        return {"jsonrpc": "2.0", "id": request["id"], "result": result}

    def _handler_class(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def _send(self, status, body=None):
                raw = json.dumps(body).encode() if body is not None else b""
                self.send_response(status)
                if body is not None:
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                scheme, _, handle = self.headers.get("Authorization", "").partition(" ")
                turn = server._turn(handle.strip()) if scheme == "Bearer" else None
                if turn is None:
                    self._send(401, {"error": "unknown handle"})
                    return
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                    if length > MAX_REQUEST_BYTES:
                        raise ValueError("request too large")
                    request = json.loads(self.rfile.read(length) or b"{}")
                    if not isinstance(request, dict):
                        raise ValueError("not an object")
                except ValueError:
                    self._send(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
                    return
                answer = server.answer(turn, request)
                self._send(202) if answer is None else self._send(200, answer)

            def do_GET(self):
                # No server-to-client stream.
                self._send(405)

            def log_message(self, *args):
                pass

        return Handler
