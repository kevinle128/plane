# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Q&A Runs in real sandboxes (``sbx`` signed in, ``sbx policy init deny-all``, host Claude settings).

Run with ``uv run pytest -m native tests/test_sandbox_native.py``. Every sandbox is named
``plane-test-*`` and is removed at the end.
"""

import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from plane_agent_worker.drivers.base import Deadline
from plane_agent_worker.drivers.claude import ClaudeDriver
from plane_agent_worker.mcp_server import PlaneMcpServer, turn_mcp_config
from plane_agent_worker.process_registry import ProcessRegistry
from plane_agent_worker.runs import RunExecutor
from plane_agent_worker.sandbox import Mount, Sandboxes, SandboxSpec, user_config_mounts
from plane_agent_worker.workspace import run_layout

pytestmark = [
    pytest.mark.native,
    pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("sbx"), reason="needs macOS and the sbx CLI"),
]

RUN_A = "aaaaaaaa-1111-4111-8111-111111111111"
RUN_B = "bbbbbbbb-2222-4222-8222-222222222222"


def claim(run_id):
    return {
        "id": run_id,
        "harness": "claude_code",
        "lease_generation": 1,
        "model": "haiku",
        "workspace": {"id": "native-test-workspace"},
        "repository": {
            "provider": "github",
            "host": "github.com",
            "clone_url": "https://github.com/acme/web.git",
            "full_name": "acme/web",
            "external_repository_id": "native-1",
            "default_branch": "main",
            "base_ref": "main",
            "credential_mode": "host",
            "ca_bundle": None,
        },
        "turn": {"index": 0},
    }


class RecordingPlane:
    def __init__(self, question):
        self.question = question
        self.results = {}
        self.events = []
        self.lock = threading.Lock()

    def renew_run(self, *args):
        return {}

    def report_clone(self, *args, **kwargs):
        return {}

    def run_context(self, run_id, generation):
        payload = {
            "workspace": {"id": "native-test-workspace", "slug": "native", "name": "Native"},
            "issue": {"id": "i-1", "identifier": f"NAT-{run_id[:4].upper()}", "title": "Native check", "state": {}},
            "agent": {"instructions": ""},
            "trigger_comment": {"id": "c-1", "author": {"display_name": "tester"}, "text": self.question},
            "comments": [],
        }
        return {"version": 1, "payload": payload, "omitted_comment_count": 0}

    def post_events(self, run_id, generation, turn_index, events):
        with self.lock:
            self.events.extend((run_id, event) for event in events)
        return []

    def post_result(self, run_id, generation, result):
        with self.lock:
            self.results[run_id] = result
        return {}


def local_clone(**kwargs):
    destination = kwargs["destination"]
    destination.mkdir()
    (destination / "README.md").write_text("The secret word of this repository is HERON.\n")


@pytest.fixture
def native(private_dir, token_file):
    run_root = Path(private_dir) / "runs"
    run_root.mkdir(mode=0o700)
    sandboxes = Sandboxes(shutil.which("sbx"), Path.home(), prefix="plane-test-")
    driver = ClaudeDriver(sandboxes=sandboxes, run_root=run_root, registry=ProcessRegistry(run_root / ".processes"))
    mcp = PlaneMcpServer(port=0)
    mcp.start()
    state = {"run_root": run_root, "sandboxes": sandboxes, "driver": driver, "mcp": mcp, "token_file": token_file}
    yield state
    mcp.stop()
    listed = subprocess.run([shutil.which("sbx"), "ls"], capture_output=True, text=True).stdout
    for line in listed.splitlines():
        name = line.split()[0] if line.split() else ""
        if name.startswith("plane-test-"):
            sandboxes.remove(name)


def executor(native, plane):
    return RunExecutor(
        client=plane,
        drivers={"claude_code": native["driver"]},
        sandboxes=native["sandboxes"],
        mcp=native["mcp"],
        run_root=native["run_root"],
        token_file=native["token_file"],
        plane_checkout=Path(__file__).resolve().parents[3],
        clone=local_clone,
    )


def test_two_concurrent_runs_answer_from_their_clone_and_the_plane_mcp_tool(native):
    plane = RecordingPlane(
        "Read README.md and call the plane_issue_context tool. Reply with exactly two words: the secret word "
        "from the README, then the work item identifier from the tool."
    )
    worker = executor(native, plane)

    threads = [threading.Thread(target=worker.execute, args=(claim(run_id),)) for run_id in (RUN_A, RUN_B)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=400)

    for run_id in (RUN_A, RUN_B):
        result = plane.results[run_id]
        assert result["status"] == "completed", result
        assert "HERON" in result["conclusion"]
        assert f"NAT-{run_id[:4].upper()}" in result["conclusion"]
        calls = [event for rid, event in plane.events if rid == run_id and event["kind"] == "tool_call"]
        assert any(event["payload"]["name"] == "mcp__plane__plane_issue_context" for event in calls)
    assert plane.results[RUN_A]["session_ref"] != plane.results[RUN_B]["session_ref"]


def qa_sandbox(native):
    layout = run_layout(native["run_root"], claim(RUN_A))
    layout.create()
    local_clone(destination=layout.clone)
    spec = SandboxSpec(
        name=native["sandboxes"].qa_name(layout.key),
        primary=layout.scratch,
        mounts=(Mount(str(layout.clones)), *user_config_mounts(Path.home())),
        allow=(f"localhost:{native['mcp'].port}",),
    )
    native["sandboxes"].ensure(spec)
    handle = native["mcp"].open_turn(run_id=RUN_A, turn_index=0, lease_generation=1, context={})
    (layout.run_scratch / "mcp.json").write_text(json.dumps(turn_mcp_config(native["mcp"].port, handle, {})))
    return layout, spec


def turn(native, layout, spec, prompt, on_message=lambda message: None):
    return native["driver"].run_turn(
        key=f"native-{RUN_A}",
        sandbox=spec.name,
        cwd=layout.clone,
        host_dir=layout.run_scratch,
        pidfile=layout.run_scratch / "agent.pid",
        prompt=prompt,
        mcp_config=layout.run_scratch / "mcp.json",
        model="haiku",
        deadline=Deadline(180),
        on_message=on_message,
    )


def test_a_write_to_the_clone_fails_and_a_write_to_the_scratch_folder_works(native):
    layout, spec = qa_sandbox(native)

    outcome = turn(
        native,
        layout,
        spec,
        "This is a sandbox boundary test. Use the Bash tool to run these two commands exactly, one at a time, "
        f"and report each output: `echo x > {layout.clone}/agent-was-here.txt` and "
        f"`echo y > {layout.run_scratch}/scratch-ok.txt`.",
    )

    assert outcome.succeeded, outcome.text
    assert not (layout.clone / "agent-was-here.txt").exists()
    assert (layout.run_scratch / "scratch-ok.txt").read_text().strip() == "y"


def test_pidfile_kill_ends_the_turn(native):
    layout, spec = qa_sandbox(native)
    state = {"killed": False}

    def kill_on_first_output(message):
        if message.get("type") == "stream_event" and not state["killed"]:
            state["killed"] = native["sandboxes"].kill(spec.name, layout.run_scratch / "agent.pid")

    outcome = turn(
        native,
        layout,
        spec,
        "Count from 1 to 300, one number per line, with no other text.",
        kill_on_first_output,
    )

    assert state["killed"] is True
    assert outcome.result is None and outcome.ended is True
