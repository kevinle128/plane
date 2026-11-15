# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Removal of the clone and scratch folders of Runs that had no activity for the retention time."""

import os
import time

from plane_agent_worker.runs import RunExecutor
from plane_agent_worker.workspace import run_layout

RUN_OLD = "11111111-1111-4111-8111-111111111111"
RUN_NEW = "22222222-2222-4222-8222-222222222222"
DAY = 24 * 3600


def claim(run_id):
    return {
        "id": run_id,
        "lease_generation": 1,
        "harness": "claude_code",
        "workspace": {"id": "w-1"},
        "repository": {
            "provider": "github",
            "host": "github.com",
            "external_repository_id": "42",
            "credential_mode": "host",
        },
    }


def make_folders(run_root, run_id, age_days):
    layout = run_layout(run_root, claim(run_id))
    layout.create()
    (layout.clone).mkdir()
    (layout.clone / "README.md").write_text("hello\n")
    (layout.run_scratch / "mcp.json").write_text("{}")
    stamp = time.time() - age_days * DAY
    for folder in (layout.clone.parent, layout.run_scratch):
        os.utime(folder, (stamp, stamp))
    return layout


def executor(run_root, **kwargs):
    return RunExecutor(
        client=None,
        drivers={"claude_code": None},
        sandboxes=None,
        mcp=None,
        run_root=run_root,
        token_file=None,
        plane_checkout=None,
        **kwargs,
    )


def test_folders_of_runs_idle_longer_than_the_retention_are_removed(private_dir):
    old = make_folders(private_dir, RUN_OLD, age_days=8)
    new = make_folders(private_dir, RUN_NEW, age_days=1)

    removed = executor(private_dir, run_folder_days=7).remove_stale_folders()

    assert removed == 1
    assert not old.clone.parent.exists() and not old.run_scratch.exists()
    assert new.clone.exists() and new.run_scratch.exists()
    assert old.scratch.is_dir() and old.clones.is_dir()


def test_retention_is_a_setting(private_dir):
    layout = make_folders(private_dir, RUN_OLD, age_days=8)

    assert executor(private_dir, run_folder_days=10).remove_stale_folders() == 0
    assert layout.clone.exists()


def test_only_run_folders_are_removed(private_dir):
    layout = make_folders(private_dir, RUN_OLD, age_days=8)
    other = layout.scratch / "notes"
    other.mkdir()
    (layout.scratch.parent / "sandbox.json").write_text("{}")
    stamp = time.time() - 30 * DAY
    for path in (other, layout.scratch.parent / "sandbox.json"):
        os.utime(path, (stamp, stamp))

    executor(private_dir, run_folder_days=7).remove_stale_folders()

    assert other.is_dir() and (layout.scratch.parent / "sandbox.json").is_file()


def test_folders_of_an_active_run_stay_and_its_end_counts_as_activity(private_dir):
    worker = executor(private_dir, run_folder_days=7)
    layout = make_folders(private_dir, RUN_OLD, age_days=8)
    during = []

    def work(run, *args):
        during.append(worker.remove_stale_folders())

    worker._work = work
    worker.execute(claim(RUN_OLD))

    assert during == [0]
    assert layout.clone.exists() and layout.run_scratch.exists()
    assert worker.remove_stale_folders() == 0
