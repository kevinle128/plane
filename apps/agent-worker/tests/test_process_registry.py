# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
import os
import subprocess
import sys
import time

from plane_agent_worker.process_registry import ProcessRegistry, is_alive

# A parent that starts a child in its own process group and waits; both must stop together.
TREE = (
    "import subprocess, sys, time; "
    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); time.sleep(60)"
)


def wait_dead(pid, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not is_alive(pid):
            return True
        time.sleep(0.05)
    return False


def child_pids(pid):
    output = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True).stdout
    return [int(line) for line in output.split()]


def test_spawn_records_the_process_and_release_stops_its_group(private_dir):
    registry = ProcessRegistry(private_dir / "processes")
    process = registry.spawn("probe-1", [sys.executable, "-c", TREE])
    time.sleep(0.5)
    children = child_pids(process.pid)

    record = json.loads((private_dir / "processes" / "probe-1.json").read_text())
    assert record["pid"] == process.pid
    assert record["pgid"] == os.getpgid(process.pid)

    registry.release("probe-1", process)

    assert wait_dead(process.pid)
    assert children and all(wait_dead(pid) for pid in children)
    assert not (private_dir / "processes" / "probe-1.json").exists()


def test_registry_directory_is_private(private_dir):
    ProcessRegistry(private_dir / "processes")

    assert (os.stat(private_dir / "processes").st_mode & 0o777) == 0o700


def test_reconcile_stops_a_recorded_process_left_by_a_previous_worker(private_dir):
    first = ProcessRegistry(private_dir / "processes")
    process = first.spawn("probe-2", [sys.executable, "-c", "import time; time.sleep(60)"])

    stopped = ProcessRegistry(private_dir / "processes").reconcile()

    assert stopped == ["probe-2"]
    process.wait(timeout=5)
    assert not (private_dir / "processes" / "probe-2.json").exists()


def test_reconcile_does_not_stop_a_process_that_reused_the_pid(private_dir):
    registry = ProcessRegistry(private_dir / "processes")
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    try:
        record = {"pid": process.pid, "pgid": process.pid, "started": "Thu Jan  1 00:00:00 1970", "argv0": "python"}
        (private_dir / "processes" / "stale.json").write_text(json.dumps(record))

        assert registry.reconcile() == []

        assert process.poll() is None
        assert not (private_dir / "processes" / "stale.json").exists()
    finally:
        process.kill()
        process.wait()


def test_reconcile_removes_the_record_of_a_finished_process(private_dir):
    registry = ProcessRegistry(private_dir / "processes")
    process = registry.spawn("done", [sys.executable, "-c", "pass"])
    process.wait(timeout=5)

    assert registry.reconcile() == []
    assert not (private_dir / "processes" / "done.json").exists()


def test_reconcile_removes_recorded_folders_inside_the_cleanup_roots(private_dir):
    sessions = private_dir / "projects"
    left = sessions / "-runs-probes-p1-1-workspace"
    left.mkdir(parents=True)
    outside = private_dir / "keep"
    outside.mkdir()
    registry = ProcessRegistry(private_dir / "processes")
    process = registry.spawn("probe-3", [sys.executable, "-c", "pass"], cleanup_paths=[str(left), str(outside)])
    process.wait(timeout=5)

    ProcessRegistry(private_dir / "processes").reconcile(cleanup_roots=[sessions])

    assert not left.exists()
    assert outside.exists()
    assert not (private_dir / "processes" / "probe-3.json").exists()


def test_release_keeps_no_record_and_reconcile_removes_nothing_after_it(private_dir):
    session = private_dir / "projects" / "-own"
    session.mkdir(parents=True)
    registry = ProcessRegistry(private_dir / "processes")
    process = registry.spawn("probe-4", [sys.executable, "-c", "pass"], cleanup_paths=[str(session)])
    process.wait(timeout=5)
    registry.release("probe-4", process)

    registry.reconcile(cleanup_roots=[private_dir / "projects"])

    assert session.exists()
