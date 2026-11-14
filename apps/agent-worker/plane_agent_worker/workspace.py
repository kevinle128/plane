# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Folders of a Q&A Run on the Worker machine.

One Q&A sandbox serves each (workspace, provider, host, repository); its key is the
first 16 hex characters of a SHA-256 of those values, so session history and
scratch never cross workspaces. Under ``<run_root>/sandboxes/<key>/``:

- ``scratch/`` is the sandbox's writable primary mount, with one ``<run_id>/``
  sub-folder per Run (the turn's MCP config and pidfile);
- ``clones/`` is a read-only mount with one ``<run_id>/clone`` per Run, made on the
  host after the sandbox exists (the mount is live). Claude starts in that clone.

``<run_root>/<run_id>/`` is host-only (the CA bundle of the clone); no sandbox mounts it.

The modification time of ``clones/<run_id>`` and ``scratch/<run_id>`` is the last activity
of the Run on this Worker: the Worker sets it when a Run ends, and removes both folders
when it is older than the retention (``RunExecutor.remove_stale_folders``).
"""

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def sandbox_key(workspace_id, provider, host, repository_id):
    joined = "\0".join(str(value) for value in (workspace_id, provider, host, repository_id))
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class RunLayout:
    key: str
    scratch: Path
    clones: Path
    run_scratch: Path
    clone: Path
    host_dir: Path

    def create(self):
        """Create the folders, except the clone itself (git creates it)."""
        for folder in (self.scratch, self.clones, self.run_scratch, self.clone.parent, self.host_dir):
            folder.mkdir(mode=0o700, parents=True, exist_ok=True)

    def touch(self):
        """Record activity now on the Run's clone and scratch folders (when they exist)."""
        for folder in (self.clone.parent, self.run_scratch):
            try:
                os.utime(folder)
            except FileNotFoundError:
                pass


def run_layout(run_root, run):
    """The folders of ``run`` (a claim). The Run ID must be a UUID, so no path can leave the Run root."""
    run_id = str(run.get("id") or "")
    if not RUN_ID_PATTERN.match(run_id):
        raise ValueError("A Run ID must be a lower-case UUID.")
    repository = run["repository"]
    key = sandbox_key(
        (run.get("workspace") or {}).get("id"),
        repository.get("provider"),
        repository.get("host"),
        repository.get("external_repository_id"),
    )
    root = Path(run_root) / "sandboxes" / key
    return RunLayout(
        key=key,
        scratch=root / "scratch",
        clones=root / "clones",
        run_scratch=root / "scratch" / run_id,
        clone=root / "clones" / run_id / "clone",
        host_dir=Path(run_root) / run_id,
    )


def run_folders(run_root):
    """``{run_id: [folder, ...]}``: the clone and scratch folders of each Run under ``run_root``."""
    folders = {}
    for kind in ("clones", "scratch"):
        for folder in Path(run_root).glob(f"sandboxes/*/{kind}/*"):
            if RUN_ID_PATTERN.match(folder.name) and folder.is_dir() and not folder.is_symlink():
                folders.setdefault(folder.name, []).append(folder)
    return folders
