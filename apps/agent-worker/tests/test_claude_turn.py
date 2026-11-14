# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A Q&A Run end to end on the Worker, with a fake Plane, the fake ``sbx`` and the fake ``claude``."""

import json
import os
import sys
import threading
from pathlib import Path

import pytest

from plane_agent_worker.conformance import suite_cache
from plane_agent_worker.drivers.claude import SUITE_VERSION, ClaudeDriver
from plane_agent_worker.git_transport import GitTransportError
from plane_agent_worker.mcp_server import PlaneMcpServer
from plane_agent_worker.plane_client import Conflict
from plane_agent_worker.process_registry import ProcessRegistry
from plane_agent_worker.runs import RunExecutor
from plane_agent_worker.sandbox import KIT_ALLOW_LIST, VM_SETTINGS, Sandboxes
from plane_agent_worker.workspace import run_layout

FAKE_CLAUDE = Path(__file__).parent / "fakes" / "fake_claude.py"
RUN_A = "11111111-1111-4111-8111-111111111111"
RUN_B = "22222222-2222-4222-8222-222222222222"
CONTEXT = {
    "workspace": {"id": "w-1", "slug": "acme", "name": "Acme"},
    "issue": {"id": "i-1", "identifier": "WEB-1", "title": "Slow login", "description": "", "state": {}},
    "agent": {"instructions": ""},
    "trigger_comment": {"id": "c-1", "author": {"id": "u-1", "display_name": "dana"}, "text": "@Claude why?"},
    "comments": [],
}


def claim(run_id=RUN_A, workspace_id="w-1", provider="github", credential_mode="host", model=""):
    return {
        "id": run_id,
        "short_id": "R-ABC123",
        "harness": "claude_code",
        "lease_generation": 1,
        "lease_seconds": 300,
        "model": model,
        "instructions": "",
        "agent": {"id": "a-1", "name": "Claude", "handle": "claude"},
        "workspace": {"id": workspace_id, "slug": "acme"},
        "issue": {"id": "i-1", "identifier": "WEB-1"},
        "repository": {
            "provider": provider,
            "host": "github.com" if provider == "github" else "git.test",
            "clone_url": "https://github.com/acme/web.git",
            "full_name": "acme/web",
            "external_repository_id": "42",
            "default_branch": "main",
            "base_ref": "main",
            "credential_mode": credential_mode,
            "ca_bundle": None,
        },
        "turn": {"index": 0},
    }


class FakePlane:
    def __init__(self):
        self.events = []
        self.results = []
        self.clones = []
        self.credentials = 0
        self.renew_conflict = False
        self.lock = threading.Lock()

    def renew_run(self, run_id, generation):
        if self.renew_conflict:
            raise Conflict(409, "lease_superseded")
        return {}

    def report_clone(self, run_id, generation, **body):
        self.clones.append((run_id, body))

    def git_credential(self, run_id, generation):
        self.credentials += 1
        return "glpat-secret-0001"

    def run_context(self, run_id, generation):
        return {"version": 1, "payload": CONTEXT, "omitted_comment_count": 0}

    def post_events(self, run_id, generation, turn_index, events):
        with self.lock:
            self.events.extend((run_id, event) for event in events)
        return []

    def post_result(self, run_id, generation, result):
        with self.lock:
            self.results.append((run_id, result))
        return {}

    def kinds(self, run_id=RUN_A):
        return [event["kind"] for rid, event in self.events if rid == run_id]

    def statuses(self, run_id=RUN_A):
        return [event["payload"]["code"] for rid, event in self.events if rid == run_id and event["kind"] == "status"]

    def result(self, run_id=RUN_A):
        return next(result for rid, result in self.results if rid == run_id)


def fake_clone(record):
    def clone(**kwargs):
        record.append(kwargs)
        destination = kwargs["destination"]
        destination.mkdir()
        (destination / "README.md").write_text("hello\n")

    return clone


class World:
    def __init__(self, private_dir, fake_sbx, host_home, token_file, scenario="ok", version="2.1.325", imported=None):
        self.private_dir = private_dir
        self.fake_sbx = fake_sbx
        self.run_root = private_dir / "runs"
        self.run_root.mkdir(exist_ok=True, mode=0o700)
        self.plane = FakePlane()
        self.clone_calls = []
        self.set_claude(scenario, version)
        self.sandboxes = Sandboxes(str(fake_sbx.path), host_home, base_env={"PATH": os.environ["PATH"]})
        self.driver = ClaudeDriver(
            sandboxes=self.sandboxes, run_root=self.run_root, registry=ProcessRegistry(self.run_root / ".processes")
        )
        self.mcp = PlaneMcpServer(port=0)
        self.mcp.start()
        self.executor = RunExecutor(
            client=self.plane,
            drivers={"claude_code": self.driver},
            sandboxes=self.sandboxes,
            mcp=self.mcp,
            run_root=self.run_root,
            token_file=token_file,
            plane_checkout=private_dir / "plane",
            imported_servers=imported or {},
            clone=fake_clone(self.clone_calls),
            first_output_seconds=2,
        )

    def set_claude(self, scenario, version):
        executable = self.fake_sbx.vm_bin / "claude"
        executable.write_text(
            "#!/bin/sh\n"
            f"export FAKE_CLAUDE_SCENARIO={scenario}\n"
            f"export FAKE_CLAUDE_VERSION={version}\n"
            f'export FAKE_CLAUDE_ARGV_LOG="{self.private_dir / "argv.jsonl"}"\n'
            f'env | cut -d= -f1 | sort > "{self.private_dir / "harness-env.txt"}"\n'
            f'exec "{sys.executable}" "{FAKE_CLAUDE}" "$@"\n'
        )
        executable.chmod(0o700)

    def verify(self, version="2.1.325"):
        """Store a passing suite record, as a Connect on this version would."""
        suite_cache(self.run_root).put(
            {
                "harness": "claude_code",
                "cli_version": version,
                "suite_version": SUITE_VERSION,
                "verified_at": "2026-11-14T00:00:00+00:00",
                "checks": [
                    {"name": name, "passed": True, "detail": ""}
                    for name in ("model_report", "follow_up", "progress", "interruption", "permission", "recovery")
                ],
                "capabilities": {"midturn_input": False, "native_resume": True, "permission_prompt": False},
            }
        )

    def claude_calls(self):
        path = self.private_dir / "argv.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def turn_calls(self):
        return [args for args in self.claude_calls() if "-p" in args and "--mcp-config" in args]


@pytest.fixture
def world(private_dir, fake_sbx, host_home, token_file):
    created = []

    def make(**kwargs):
        instance = World(private_dir, fake_sbx, host_home, token_file, **kwargs)
        created.append(instance)
        return instance

    yield make
    for instance in created:
        instance.mcp.stop()


def test_run_clones_starts_claude_in_the_clone_and_posts_the_answer(world, fake_sbx, host_home):
    w = world()
    w.verify()

    w.executor.execute(claim())

    layout = run_layout(w.run_root, claim())
    result = w.plane.result()
    assert result["status"] == "completed"
    assert result["conclusion"] == "OK"
    assert result["session_ref"]
    assert w.plane.clones == [(RUN_A, {"ok": True, "clone_path": str(layout.clone)})]
    assert w.clone_calls[0]["destination"] == layout.clone
    assert w.clone_calls[0]["credential_mode"] == "host"
    assert w.plane.statuses() == ["cloning", "sandbox_starting", "turn_started"]
    assert "message" in w.plane.kinds()

    [turn] = w.turn_calls()
    assert "--dangerously-skip-permissions" in turn and "--strict-mcp-config" in turn
    assert turn[turn.index("--add-dir") + 1].endswith("/opt/user-claude")
    assert turn[turn.index("--settings") + 1].endswith(VM_SETTINGS)
    assert turn[turn.index("--mcp-config") + 1] == str(layout.run_scratch / "mcp.json")

    name = f"plane-qa-{layout.key}"
    [create] = fake_sbx.commands("create")
    assert create[create.index("--name") + 1] == name and "--static-mcp" in create
    assert create[create.index("claude") + 1] == str(layout.scratch)
    assert f"{layout.clones}:ro" in create
    rules = fake_sbx.sandbox(name)["rules"]
    assert ["allow", f"localhost:{w.mcp.port}"] in rules and ["allow", "gateway.test:8317"] in rules
    assert ["deny", KIT_ALLOW_LIST] in rules
    turn_exec = next(call for call in fake_sbx.commands("exec") if "--mcp-config" in call)
    assert turn_exec[turn_exec.index("-w") + 1] == str(layout.clone)
    assert "gateway-secret-0001" not in json.dumps(fake_sbx.calls())


def test_turn_mcp_config_has_the_plane_server_and_the_handle_ends_with_the_turn(world):
    w = world()
    w.verify()

    w.executor.execute(claim())

    config = json.loads((run_layout(w.run_root, claim()).run_scratch / "mcp.json").read_text())
    assert list(config["mcpServers"]) == ["plane"]
    plane = config["mcpServers"]["plane"]
    assert plane["url"] == f"http://host.docker.internal:{w.mcp.port}/mcp"
    handle = plane["headers"]["Authorization"].removeprefix("Bearer ")
    assert w.mcp._turn(handle) is None
    assert "plane_aw_test-token-value-0001" not in json.dumps(config)
    assert "glpat" not in json.dumps(config)


def test_listed_mcp_server_is_in_the_config_and_allowed_before_the_first_turn(world, fake_sbx):
    archon = {"type": "http", "url": "https://archon.test:8051/mcp"}
    w = world(imported={"archon": archon})
    w.verify()

    w.executor.execute(claim())

    layout = run_layout(w.run_root, claim())
    config = json.loads((layout.run_scratch / "mcp.json").read_text())
    assert config["mcpServers"]["archon"] == archon
    assert ["allow", "archon.test:8051"] in fake_sbx.sandbox(f"plane-qa-{layout.key}")["rules"]


def test_second_run_of_the_repository_uses_the_same_sandbox_and_another_clone(world, fake_sbx):
    w = world()
    w.verify()

    w.executor.execute(claim(RUN_A))
    w.executor.execute(claim(RUN_B))

    assert len(fake_sbx.commands("create")) == 1
    clones = [call["destination"] for call in w.clone_calls]
    assert clones[0] != clones[1] and clones[0].parent.parent == clones[1].parent.parent
    cwds = [call[call.index("-w") + 1] for call in fake_sbx.commands("exec") if "--mcp-config" in call]
    assert cwds == [str(clones[0]), str(clones[1])]


def test_other_workspace_with_the_same_repository_gets_another_sandbox(world, fake_sbx):
    w = world()
    w.verify()

    w.executor.execute(claim(RUN_A, workspace_id="w-1"))
    w.executor.execute(claim(RUN_B, workspace_id="w-2"))

    names = [call[call.index("--name") + 1] for call in fake_sbx.commands("create")]
    assert len(set(names)) == 2


def test_two_concurrent_runs_have_their_own_cwd_and_events(world, fake_sbx):
    w = world()
    w.verify()

    threads = [threading.Thread(target=w.executor.execute, args=(claim(run_id),)) for run_id in (RUN_A, RUN_B)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert {rid for rid, _ in w.plane.results} == {RUN_A, RUN_B}
    assert all(result["status"] == "completed" for _, result in w.plane.results)
    turns = [call for call in fake_sbx.commands("exec") if "--mcp-config" in call]
    expected = {str(run_layout(w.run_root, claim(run_id)).clone) for run_id in (RUN_A, RUN_B)}
    assert {call[call.index("-w") + 1] for call in turns} == expected
    pidfiles = {call[call.index("-c") + 1] for call in turns}
    assert len(pidfiles) == 2
    for run_id in (RUN_A, RUN_B):
        assert "message" in w.plane.kinds(run_id)


def test_cached_version_starts_no_suite(world):
    w = world()
    w.verify()

    w.executor.execute(claim())

    assert not [args for args in w.claude_calls() if "--tools" in args]
    assert "checking_version" not in w.plane.statuses()


def test_new_version_runs_the_suite_first_then_the_turn(world):
    w = world()

    w.executor.execute(claim())

    assert w.plane.statuses() == ["cloning", "sandbox_starting", "checking_version", "turn_started"]
    calls = w.claude_calls()
    suite_index = next(index for index, args in enumerate(calls) if "--tools" in args)
    turn_index = next(index for index, args in enumerate(calls) if "--mcp-config" in args)
    assert suite_index < turn_index
    assert w.plane.result()["status"] == "completed"
    assert suite_cache(w.run_root).get("claude_code", "2.1.325", SUITE_VERSION)


def test_failed_suite_fails_the_run_and_starts_no_turn(world):
    w = world(scenario="no_interrupt")

    w.executor.execute(claim())

    result = w.plane.result()
    assert result["status"] == "failed"
    assert result["failure_code"] == "harness_version_unverified"
    assert result["harness_version"] == "2.1.325"
    assert result["failed_check"] == "interruption"
    assert w.turn_calls() == []


def test_two_runs_on_one_new_version_start_one_suite(world):
    w = world()

    threads = [threading.Thread(target=w.executor.execute, args=(claim(run_id),)) for run_id in (RUN_A, RUN_B)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)

    suite_sessions = [
        args for args in w.claude_calls() if "--tools" in args and args[args.index("--tools") + 1] == "Bash"
    ]
    assert len(suite_sessions) == 1
    assert [result["status"] for _, result in w.plane.results] == ["completed", "completed"]


def test_authentication_failure_fails_the_run_with_its_reason(world):
    w = world(scenario="auth_error")
    w.verify()

    w.executor.execute(claim())

    result = w.plane.result()
    assert result["status"] == "failed"
    assert result["failure_code"] == "harness_auth_failed"
    assert "401" in result["failure_message"]
    clone = run_layout(w.run_root, claim()).clone
    assert sorted(path.name for path in clone.iterdir()) == ["README.md"]


def test_no_model_output_in_time_fails_the_turn_with_a_gateway_hint(world):
    w = world(scenario="no_answer")
    w.verify()

    w.executor.execute(claim())

    result = w.plane.result()
    assert result["failure_code"] == "harness_no_response"
    assert "gateway" in result["failure_message"]
    assert list((w.run_root / ".processes").iterdir()) == []


def test_unavailable_sandbox_fails_the_run(world, fake_sbx):
    w = world()
    w.verify()
    fake_sbx.set_scenario("create_fails")

    w.executor.execute(claim())

    result = w.plane.result()
    assert result["failure_code"] == "sandbox_unavailable"
    assert w.turn_calls() == []


def test_missing_sandbox_is_created_again_before_the_turn(world, fake_sbx):
    w = world()
    w.verify()
    w.executor.execute(claim(RUN_A))
    for path in (fake_sbx.state / "sandboxes").glob("*.json"):
        path.unlink()

    w.executor.execute(claim(RUN_B))

    assert len(fake_sbx.commands("create")) == 2
    assert w.plane.result(RUN_B)["status"] == "completed"


def test_stopped_sandbox_starts_without_an_error_event(world, fake_sbx):
    w = world()
    w.verify()
    w.executor.execute(claim(RUN_A))
    layout = run_layout(w.run_root, claim(RUN_A))
    os.system(f'"{fake_sbx.path}" stop plane-qa-{layout.key}')

    w.executor.execute(claim(RUN_B))

    assert "error" not in w.plane.kinds(RUN_B)
    assert w.plane.result(RUN_B)["status"] == "completed"


def test_clone_failure_is_reported_and_fails_the_run(world):
    w = world()
    w.verify()

    def failing_clone(**kwargs):
        raise GitTransportError("git_tls_failed", "server certificate verification failed")

    w.executor.clone = failing_clone
    w.executor.execute(claim())

    assert w.plane.clones == [
        (RUN_A, {"ok": False, "error_code": "git_tls_failed", "error_detail": "server certificate verification failed"})
    ]
    result = w.plane.result()
    assert result["failure_code"] == "git_tls_failed"
    assert "github.com" in result["failure_message"]
    assert w.turn_calls() == []


def test_gitlab_run_fetches_the_token_only_through_the_clone(world):
    w = world()
    w.verify()

    w.executor.execute(claim(provider="gitlab", credential_mode="plane_token"))

    [call] = w.clone_calls
    assert call["credential_mode"] == "plane_token"
    assert w.plane.credentials == 0
    assert call["fetch_token"]() == "glpat-secret-0001"
    names = set((w.private_dir / "harness-env.txt").read_text().split())
    assert not any("TOKEN" in name for name in names)
    assert "glpat-secret-0001" not in json.dumps(w.plane.events)


def test_selected_model_is_passed_to_the_turn(world):
    w = world()
    w.verify()

    w.executor.execute(claim(model="sonnet"))

    [turn] = w.turn_calls()
    assert turn[turn.index("--model") + 1] == "sonnet"


def test_lost_lease_posts_no_result(world):
    w = world(scenario="no_answer")
    w.verify()
    w.plane.renew_conflict = True
    w.executor.renew_seconds = 0.2

    w.executor.execute(claim())

    assert w.plane.results == []


def test_claim_with_an_unsafe_run_id_is_refused(world):
    w = world()

    w.executor.execute({**claim(), "id": "../../etc"})

    assert w.plane.results == [] and w.clone_calls == []
