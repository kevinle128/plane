# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import subprocess
import sys

import pytest

from plane_agent_worker.sandbox_macos import PROFILE_PATH, MacOSSandbox, SandboxPaths

pytestmark_darwin = pytest.mark.skipif(sys.platform != "darwin", reason="the macOS sandbox exists only on macOS")


@pytest.fixture
def paths(private_dir, token_file):
    run_root = private_dir / "runs"
    own = run_root / "probe-1"
    for directory in (own / "workspace", own / "tmp", private_dir / "sessions" / "own", private_dir / "plane"):
        directory.mkdir(parents=True, mode=0o700)
    (run_root / "probe-2").mkdir(mode=0o700)
    (run_root / "probe-2" / "secret.txt").write_text("other run")
    (private_dir / "sessions" / "other").mkdir(mode=0o700)
    (private_dir / "sessions" / "other" / "session.jsonl").write_text("other session")
    (private_dir / "plane" / "settings.py").write_text("checkout")
    (own / "workspace" / "readme.txt").write_text("own run")
    return SandboxPaths(
        run_root=run_root,
        own_dir=own,
        private_tmp=own / "tmp",
        session_root=private_dir / "sessions",
        session_dir=private_dir / "sessions" / "own",
        token_file=token_file,
        plane_checkout=private_dir / "plane",
    )


def run(sandbox, paths, script, *args):
    command = sandbox.wrap(["/bin/sh", "-c", script, "sh", *args], paths)
    return subprocess.run(command, capture_output=True, text=True, timeout=30)


def test_wrap_passes_every_path_as_a_profile_parameter(paths):
    command = MacOSSandbox().wrap(["/bin/echo", "hi"], paths)

    assert command[:3] == ["/usr/bin/sandbox-exec", "-f", str(PROFILE_PATH)]
    assert command[-2:] == ["/bin/echo", "hi"]
    parameters = dict(item.split("=", 1) for item in command[3:-2] if item != "-D")
    assert parameters == {
        "RUN_ROOT": str(paths.run_root),
        "OWN_DIR": str(paths.own_dir),
        "PRIVATE_TMP": str(paths.private_tmp),
        "SESSION_ROOT": str(paths.session_root),
        "SESSION_DIR": str(paths.session_dir),
        "TOKEN_FILE": str(paths.token_file),
        "PLANE_CHECKOUT": str(paths.plane_checkout),
    }


def test_profile_has_no_machine_specific_path():
    profile = PROFILE_PATH.read_text()

    assert "(deny file-write*)" in profile
    assert "/Users/" not in profile
    assert "/home/" not in profile


def test_relative_path_is_refused(paths):
    with pytest.raises(ValueError):
        MacOSSandbox().wrap(["/bin/true"], paths._replace(private_tmp=paths.private_tmp.relative_to("/")))


@pytestmark_darwin
@pytest.mark.native
class TestBoundary:
    def test_write_in_the_workspace_is_denied(self, paths):
        result = run(MacOSSandbox(), paths, 'echo x > "$1"', str(paths.own_dir / "workspace" / "new.txt"))

        assert result.returncode != 0
        assert not (paths.own_dir / "workspace" / "new.txt").exists()

    def test_write_outside_every_run_is_denied(self, paths, private_dir):
        result = run(MacOSSandbox(), paths, 'echo x > "$1"', str(private_dir / "outside.txt"))

        assert result.returncode != 0
        assert not (private_dir / "outside.txt").exists()

    def test_write_in_the_private_tmp_and_session_dir_is_allowed(self, paths):
        target = paths.private_tmp / "scratch.txt"
        session = paths.session_dir / "session.jsonl"

        assert run(MacOSSandbox(), paths, 'echo x > "$1" && echo y > "$2"', str(target), str(session)).returncode == 0
        assert target.read_text() == "x\n"

    def test_own_run_is_readable(self, paths):
        result = run(MacOSSandbox(), paths, 'cat "$1"', str(paths.own_dir / "workspace" / "readme.txt"))

        assert result.stdout == "own run"

    @pytest.mark.parametrize(
        "target",
        ["token", "other_run", "other_session", "checkout"],
    )
    def test_secret_and_foreign_paths_are_not_readable(self, paths, target):
        path = {
            "token": paths.token_file,
            "other_run": paths.run_root / "probe-2" / "secret.txt",
            "other_session": paths.session_root / "other" / "session.jsonl",
            "checkout": paths.plane_checkout / "settings.py",
        }[target]

        result = run(MacOSSandbox(), paths, 'cat "$1"', str(path))

        assert result.returncode != 0
        assert result.stdout == ""

    def test_verify_write_denied_reports_the_boundary(self, paths):
        denied, detail = MacOSSandbox().verify_write_denied(paths.own_dir / "workspace", paths)

        assert denied is True, detail
