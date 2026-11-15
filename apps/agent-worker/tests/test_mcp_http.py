# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
import urllib.error
import urllib.request

import pytest

from plane_agent_worker.config import ConfigError
from plane_agent_worker.mcp_server import (
    PlaneMcpServer,
    imported_allow_rules,
    load_imported_servers,
    turn_mcp_config,
)

CONTEXT = {"issue": {"identifier": "WEB-12", "title": "Login page is slow"}}


@pytest.fixture
def server():
    mcp = PlaneMcpServer(port=0)
    mcp.start()
    yield mcp
    mcp.stop()


def call(server, body, handle):
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.port}/mcp",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        | ({"Authorization": f"Bearer {handle}"} if handle else {}),
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        return error.code, None


def test_issue_context_tool_answers_for_a_live_handle(server):
    handle = server.open_turn(run_id="r-1", turn_index=0, lease_generation=3, context=CONTEXT)

    status, init = call(
        server, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}, handle
    )
    assert status == 200
    assert init["result"]["serverInfo"]["name"] == "plane"
    assert init["result"]["protocolVersion"] == "2025-06-18"

    status, _ = call(server, {"jsonrpc": "2.0", "method": "notifications/initialized"}, handle)
    assert status == 202

    _, listed = call(server, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, handle)
    assert [tool["name"] for tool in listed["result"]["tools"]] == ["plane_issue_context"]

    _, called = call(
        server,
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "plane_issue_context", "arguments": {}}},
        handle,
    )
    assert json.loads(called["result"]["content"][0]["text"]) == CONTEXT


def test_unknown_or_ended_handle_gets_401(server):
    handle = server.open_turn(run_id="r-1", turn_index=0, lease_generation=1, context=CONTEXT)
    server.close_turn(handle)

    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    assert call(server, body, handle)[0] == 401
    assert call(server, body, "not-a-handle")[0] == 401
    assert call(server, body, None)[0] == 401


def test_unknown_tool_is_an_error(server):
    handle = server.open_turn(run_id="r-1", turn_index=0, lease_generation=1, context=CONTEXT)

    _, answer = call(server, {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "nope"}}, handle)

    assert answer["error"]["code"] == -32602


def test_handles_are_random_and_differ_per_turn(server):
    first = server.open_turn(run_id="r-1", turn_index=0, lease_generation=1, context=CONTEXT)
    second = server.open_turn(run_id="r-2", turn_index=0, lease_generation=1, context=CONTEXT)

    assert first != second and len(first) >= 32


def test_turn_config_has_the_plane_server_with_the_handle_and_no_token():
    config = turn_mcp_config(port=7450, handle="h" * 40, imported={})

    assert config == {
        "mcpServers": {
            "plane": {
                "type": "http",
                "url": "http://host.docker.internal:7450/mcp",
                "headers": {"Authorization": f"Bearer {'h' * 40}"},
            }
        }
    }


def test_turn_config_adds_the_listed_servers():
    archon = {"type": "http", "url": "https://archon.test:8051/mcp"}

    config = turn_mcp_config(port=7450, handle="h", imported={"archon": archon})

    assert config["mcpServers"]["archon"] == archon
    assert set(config["mcpServers"]) == {"plane", "archon"}


def write_claude_json(home, servers):
    (home / ".claude.json").write_text(json.dumps({"mcpServers": servers, "other": "ignored"}))


def test_listed_servers_load_from_the_user_config(private_dir):
    archon = {"type": "http", "url": "https://archon.test:8051/mcp"}
    write_claude_json(private_dir, {"archon": archon, "local": {"command": "python3", "args": ["s.py"]}})

    assert load_imported_servers(["archon"], private_dir) == {"archon": archon}
    assert load_imported_servers([], private_dir) == {}


def test_unknown_listed_server_fails_the_worker_start(private_dir):
    write_claude_json(private_dir, {"archon": {"type": "http", "url": "https://archon.test/mcp"}})

    with pytest.raises(ConfigError, match="missing"):
        load_imported_servers(["archon", "missing"], private_dir)


def test_http_servers_get_an_allow_rule_and_stdio_servers_none():
    rules = imported_allow_rules(
        {
            "archon": {"type": "http", "url": "https://archon.test:8051/mcp"},
            "docs": {"type": "sse", "url": "http://docs.test/sse"},
            "local": {"command": "python3"},
        }
    )

    assert rules == ("archon.test:8051", "docs.test:80")
