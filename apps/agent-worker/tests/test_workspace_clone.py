# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane_agent_worker.workspace import run_layout, sandbox_key

RUN_ID = "11111111-1111-4111-8111-111111111111"


def claim(run_id=RUN_ID, workspace_id="w-1", host="github.com"):
    return {
        "id": run_id,
        "workspace": {"id": workspace_id},
        "repository": {"provider": "github", "host": host, "external_repository_id": "42"},
    }


def test_clone_path_comes_from_the_run_id_inside_the_run_root(private_dir):
    layout = run_layout(private_dir / "runs", claim())

    key = sandbox_key("w-1", "github", "github.com", "42")
    root = private_dir / "runs" / "sandboxes" / key
    assert layout.key == key and len(key) == 16
    assert layout.clone == root / "clones" / RUN_ID / "clone"
    assert layout.run_scratch == root / "scratch" / RUN_ID
    assert layout.host_dir == private_dir / "runs" / RUN_ID
    assert private_dir / "plane" not in layout.clone.parents


def test_key_separates_workspaces_hosts_and_repositories():
    keys = {
        sandbox_key("w-1", "github", "github.com", "42"),
        sandbox_key("w-2", "github", "github.com", "42"),
        sandbox_key("w-1", "gitlab", "github.com", "42"),
        sandbox_key("w-1", "github", "git.test", "42"),
        sandbox_key("w-1", "github", "github.com", "43"),
    }
    assert len(keys) == 5


@pytest.mark.parametrize("run_id", ["../../etc", "", "ABCDEF00-1111-4111-8111-111111111111", "11111111/1111"])
def test_unsafe_run_id_is_refused(private_dir, run_id):
    with pytest.raises(ValueError):
        run_layout(private_dir / "runs", claim(run_id=run_id))


def test_create_makes_private_folders_but_not_the_clone(private_dir):
    layout = run_layout(private_dir / "runs", claim())

    layout.create()

    assert layout.clone.parent.is_dir() and not layout.clone.exists()
    for folder in (layout.scratch, layout.clones, layout.run_scratch, layout.host_dir):
        assert folder.is_dir() and folder.stat().st_mode & 0o777 == 0o700
