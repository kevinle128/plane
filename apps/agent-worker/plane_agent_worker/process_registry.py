# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Records of the Harness process groups that the Worker starts.

Each Harness process starts in its own process group. The Worker writes one
private JSON record per group (PID, group ID and process start time). At start,
``reconcile`` stops the groups that a previous Worker left behind. It compares
the start time first, so a PID that the system gave to an unrelated process is
never signalled.
"""

import json
import os
import signal
import subprocess
import time
from pathlib import Path

STOP_GRACE_SECONDS = 2.0


def is_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # A zombie still answers signal 0; ``ps`` shows its state as Z.
    state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(state) and not state.startswith("Z")


def process_start_time(pid):
    """The start time that ``ps`` reports, or ``None`` when the process does not exist."""
    result = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True)
    value = result.stdout.strip()
    return value or None


def stop_group(pgid, grace_seconds=STOP_GRACE_SECONDS):
    """Send SIGTERM to the group, then SIGKILL to what is still running after the grace time."""
    # macOS answers EPERM for a group whose only member is an unreaped zombie, so EPERM means "exited" here.
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except (ProcessLookupError, PermissionError):
            return
        time.sleep(0.05)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        return


class ProcessRegistry:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.directory, 0o700)

    def _record_path(self, key):
        if not key or "/" in key or key.startswith("."):
            raise ValueError("A process key is a plain file name.")
        return self.directory / f"{key}.json"

    def _write_record(self, key, record):
        path = self._record_path(key)
        temporary = path.with_suffix(".tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            json.dump(record, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)

    def spawn(self, key, argv, **popen_kwargs):
        """Start ``argv`` in a new process group and record it under ``key``."""
        process = subprocess.Popen(argv, start_new_session=True, **popen_kwargs)
        try:
            self._write_record(
                key,
                {
                    "pid": process.pid,
                    "pgid": os.getpgid(process.pid),
                    "started": process_start_time(process.pid),
                    "argv0": os.path.basename(argv[0]),
                },
            )
        except BaseException:
            stop_group(process.pid)
            process.wait()
            raise
        return process

    def release(self, key, process, grace_seconds=STOP_GRACE_SECONDS):
        """Stop the whole group of ``process`` (children included), wait for it and remove the record."""
        stop_group(process.pid, grace_seconds)
        try:
            process.wait(timeout=grace_seconds + 5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        self._record_path(key).unlink(missing_ok=True)

    def reconcile(self):
        """Stop the recorded groups of a previous Worker. Returns the keys of the stopped groups."""
        stopped = []
        for path in sorted(self.directory.glob("*.json")):
            key = path.stem
            try:
                record = json.loads(path.read_text())
                pid, pgid, started = int(record["pid"]), int(record["pgid"]), record["started"]
            except (OSError, ValueError, KeyError, TypeError):
                path.unlink(missing_ok=True)
                continue
            if started and is_alive(pid) and process_start_time(pid) == started:
                stop_group(pgid)
                stopped.append(key)
            path.unlink(missing_ok=True)
        return stopped
