# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
import os
import sys
from pathlib import Path

import pytest


@pytest.fixture
def private_dir(tmp_path):
    """A directory tree owned by the current user with mode 0700, like a real Worker directory."""
    root = Path(os.path.realpath(tmp_path))
    root.chmod(0o700)
    return root


@pytest.fixture
def token_file(private_dir):
    path = private_dir / "secrets" / "worker-token"
    path.parent.mkdir(mode=0o700)
    path.write_text("plane_aw_test-token-value-0001\n")
    path.chmod(0o600)
    return path


FAKE_SBX = Path(__file__).parent / "fakes" / "fake_sbx.py"


@pytest.fixture
def host_home(private_dir):
    """A host home folder with ``~/.claude/settings.json`` that names a gateway and holds a token."""
    home = private_dir / "host-home"
    (home / ".claude").mkdir(parents=True, mode=0o700)
    settings = {
        "env": {"ANTHROPIC_BASE_URL": "http://gateway.test:8317", "ANTHROPIC_AUTH_TOKEN": "gateway-secret-0001"}
    }
    (home / ".claude" / "settings.json").write_text(json.dumps(settings))
    (home / ".claude" / "settings.json").chmod(0o600)
    return home


class FakeSbx:
    """A fake ``sbx`` executable and its state folder."""

    def __init__(self, root):
        self.state = root / "sbx-state"
        self.bin = root / "sbx-bin"
        self.vm_bin = root / "vm-bin"
        self.bin.mkdir(mode=0o700)
        self.vm_bin.mkdir(mode=0o700)
        self.scenario = "ok"
        self.path = self.bin / "sbx"
        self.path.write_text(
            "#!/bin/sh\n"
            f'export FAKE_SBX_STATE="{self.state}"\n'
            f'export FAKE_SBX_PATH="{self.vm_bin}:/usr/bin:/bin"\n'
            f'export FAKE_SBX_SCENARIO="$(cat "{root / "sbx-scenario"}" 2>/dev/null || echo ok)"\n'
            f'exec "{sys.executable}" "{FAKE_SBX}" "$@"\n'
        )
        self.path.chmod(0o700)
        self._scenario_file = root / "sbx-scenario"

    def set_scenario(self, scenario):
        self._scenario_file.write_text(scenario)

    def calls(self):
        path = self.state / "argv.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def commands(self, name):
        """The calls whose sub-command (after ``--no-input``) is ``name``."""
        return [call for call in self.calls() if [arg for arg in call if arg != "--no-input"][:1] == [name]]

    def sandbox(self, name):
        path = self.state / "sandboxes" / f"{name}.json"
        return json.loads(path.read_text()) if path.exists() else None


@pytest.fixture
def fake_sbx(private_dir):
    return FakeSbx(private_dir)
