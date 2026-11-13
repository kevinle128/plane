# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os
import shutil
import sys
from pathlib import Path

import pytest

from plane_agent_worker.conformance import REPORT_VERSION, run_probe
from plane_agent_worker.drivers.base import REQUIRED_CHECKS
from plane_agent_worker.drivers.claude import ClaudeDriver
from plane_agent_worker.process_registry import ProcessRegistry
from plane_agent_worker.sandbox_macos import MacOSSandbox

FAKE = Path(__file__).parent / "fakes" / "fake_claude.py"


class FakeSandbox:
    """Runs commands unchanged and reports the OS write boundary as the test asks."""

    def __init__(self, write_denied=True):
        self.write_denied = write_denied

    def wrap(self, argv, paths):
        return list(argv)

    def verify_write_denied(self, directory, paths):
        return self.write_denied, "" if self.write_denied else "a write in the workspace succeeded"


@pytest.fixture
def home(private_dir):
    path = private_dir / "home"
    (path / ".claude").mkdir(parents=True, mode=0o700)
    return path


def fake_claude(private_dir, scenario="ok", version="2.1.289"):
    executable = private_dir / "bin" / "claude"
    executable.parent.mkdir(exist_ok=True, mode=0o700)
    executable.write_text(
        "#!/bin/sh\n"
        f"export FAKE_CLAUDE_SCENARIO={scenario}\n"
        f"export FAKE_CLAUDE_VERSION={version}\n"
        f'env | cut -d= -f1 | sort > "{private_dir / "harness-env.txt"}"\n'
        f'exec "{sys.executable}" "{FAKE}" "$@"\n'
    )
    executable.chmod(0o700)
    return executable


def probe(private_dir, token_file, home, executable, sandbox=None, extra_env=None):
    checkout = private_dir / "plane"
    checkout.mkdir(exist_ok=True)
    run_root = private_dir / "runs"
    run_root.mkdir(exist_ok=True, mode=0o700)
    env = {"HOME": str(home), "PATH": os.environ["PATH"], "LANG": "C.UTF-8", **(extra_env or {})}
    driver = ClaudeDriver(
        executable=str(executable) if executable else None,
        registry=ProcessRegistry(run_root / ".processes"),
        base_env=env,
    )
    return run_probe(
        driver,
        run_root=run_root,
        probe_key="probe-test",
        token_file=token_file,
        plane_checkout=checkout,
        sandbox=sandbox or FakeSandbox(),
    )


def checks_of(report):
    return {check["name"]: check for check in report["checks"]}


def test_fake_claude_passes_every_check(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, fake_claude(private_dir))

    assert report["version"] == REPORT_VERSION
    assert [check["name"] for check in report["checks"]] == list(REQUIRED_CHECKS)
    assert all(check["passed"] for check in report["checks"]), report["checks"]
    assert report["harness_version"] == "2.1.289"
    assert report["blocking_issue"] is None
    # The model list is the one recorded from Claude Code 2.1.289.
    assert [model["id"] for model in report["models"]] == ["default", "opus", "claude-fable-5-1[1m]", "sonnet", "haiku"]
    assert report["models"][4] == {
        "id": "haiku",
        "label": "Haiku",
        "description": "Haiku 4.5 · Fastest for quick answers · $1/$5 per Mtok",
    }
    assert report["capabilities"] == {"midturn_input": False, "native_resume": True, "permission_prompt": True}


def test_missing_permission_prompt_fails_the_permission_check(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, fake_claude(private_dir, scenario="no_permission_prompt"))

    checks = checks_of(report)
    assert checks["permission"]["passed"] is False
    assert "permission prompt" in checks["permission"]["detail"]
    assert report["capabilities"]["permission_prompt"] is False
    assert all(check["passed"] for name, check in checks.items() if name != "permission")


def test_writable_os_boundary_fails_the_permission_check(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, fake_claude(private_dir), sandbox=FakeSandbox(write_denied=False))

    assert checks_of(report)["permission"]["passed"] is False
    assert "write" in checks_of(report)["permission"]["detail"]


def test_not_logged_in_fails_authentication_and_skips_the_rest(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, fake_claude(private_dir, scenario="not_logged_in"))

    assert checks_of(report)["authentication"]["passed"] is False
    assert all(not check["passed"] for check in report["checks"])
    assert report["models"] == []
    assert "not logged in" in report["failure_hint"]


def test_empty_model_list_fails_the_model_report(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, fake_claude(private_dir, scenario="no_models"))

    assert checks_of(report)["model_report"]["passed"] is False
    assert report["models"] == []


def test_lost_session_fails_follow_up_and_recovery(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, fake_claude(private_dir, scenario="no_resume"))

    checks = checks_of(report)
    assert checks["follow_up"]["passed"] is False
    assert checks["recovery"]["passed"] is False
    assert report["capabilities"]["native_resume"] is False
    assert checks["progress"]["passed"] is True


def test_missing_cli_is_a_blocking_issue(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, private_dir / "bin" / "absent-claude")

    assert report["blocking_issue"] == "harness_not_found"
    assert all(not check["passed"] for check in report["checks"])


def test_unsupported_version_is_a_blocking_issue(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, fake_claude(private_dir, version="3.0.0"))

    assert report["blocking_issue"] == "unsupported_version"
    assert report["harness_version"] == "3.0.0"
    assert "3.0.0" in report["failure_hint"]


def test_harness_gets_an_allowlisted_environment(private_dir, token_file, home):
    secret_env = {
        "PLANE_AGENT_WORKER_TOKEN_FILE": str(token_file),
        "CLAUDECODE": "1",
        "CLAUDE_CODE_SESSION_ID": "outer-session",
        "AWS_SECRET_ACCESS_KEY": "do-not-pass",
        "ANTHROPIC_API_KEY": "operator-key",
    }

    probe(private_dir, token_file, home, fake_claude(private_dir), extra_env=secret_env)

    names = set((private_dir / "harness-env.txt").read_text().split())
    assert {"HOME", "PATH", "TMPDIR", "ANTHROPIC_API_KEY"} <= names
    forbidden = {"PLANE_AGENT_WORKER_TOKEN_FILE", "CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "AWS_SECRET_ACCESS_KEY"}
    assert not names & forbidden


def test_probe_leaves_no_process_record_and_no_probe_directory(private_dir, token_file, home):
    probe(private_dir, token_file, home, fake_claude(private_dir))

    assert list((private_dir / "runs" / ".processes").iterdir()) == []
    assert not (private_dir / "runs" / "probes" / "probe-test").exists()


@pytest.mark.native
@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("claude"), reason="needs macOS and the claude CLI")
def test_real_claude_probe_passes_under_the_macos_boundary(private_dir, token_file):
    checkout = Path(__file__).resolve().parents[3]
    run_root = private_dir / "runs"
    run_root.mkdir(mode=0o700)
    driver = ClaudeDriver(executable=shutil.which("claude"), registry=ProcessRegistry(run_root / ".processes"))

    report = run_probe(
        driver,
        run_root=run_root,
        probe_key="native-probe",
        token_file=token_file,
        plane_checkout=checkout,
        sandbox=MacOSSandbox(),
    )

    assert all(check["passed"] for check in report["checks"]), report["checks"]
    assert report["models"]
    assert report["capabilities"]["permission_prompt"] is True
    assert report["capabilities"]["native_resume"] is True
