# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from plane_agent_worker.conformance import REPORT_VERSION, run_probe
from plane_agent_worker.drivers.base import REQUIRED_CHECKS
from plane_agent_worker.drivers.claude import ClaudeDriver, session_dir_name
from plane_agent_worker.process_registry import ProcessRegistry

FAKE = Path(__file__).parent / "fakes" / "fake_claude.py"


@pytest.fixture
def home(private_dir):
    path = private_dir / "home"
    (path / ".claude").mkdir(parents=True, mode=0o700)
    return path


def fake_claude(private_dir, scenario="ok", version="2.1.289", write_tool=""):
    executable = private_dir / "bin" / "claude"
    executable.parent.mkdir(exist_ok=True, mode=0o700)
    executable.write_text(
        "#!/bin/sh\n"
        f"export FAKE_CLAUDE_SCENARIO={scenario}\n"
        f"export FAKE_CLAUDE_VERSION={version}\n"
        f"export FAKE_CLAUDE_WRITE_TOOL={write_tool}\n"
        f'export FAKE_CLAUDE_ARGV_LOG="{private_dir / "argv.jsonl"}"\n'
        f'env | cut -d= -f1 | sort > "{private_dir / "harness-env.txt"}"\n'
        f'exec "{sys.executable}" "{FAKE}" "$@"\n'
    )
    executable.chmod(0o700)
    return executable


def probe(private_dir, token_file, home, executable, extra_env=None):
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
    )


def checks_of(report):
    return {check["name"]: check for check in report["checks"]}


def probe_cwd(private_dir):
    return Path(os.path.realpath(private_dir / "runs")) / "probes" / "probe-test" / "workspace"


def session_argv(private_dir):
    """The arguments of each stream session (not ``--version`` or ``auth status``)."""
    calls = [json.loads(line) for line in (private_dir / "argv.jsonl").read_text().splitlines()]
    return [args for args in calls if "-p" in args]


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
    # The boundary denies writes without asking, so no permission prompt arrives.
    assert report["capabilities"] == {"midturn_input": False, "native_resume": True, "permission_prompt": False}


def test_every_session_runs_with_the_worker_boundary_settings(private_dir, token_file, home, monkeypatch):
    captured = {}
    original = ClaudeDriver._session

    def capture(self, context, name, extra_args=()):
        captured.setdefault("settings", json.loads(Path(context["settings_file"]).read_text()))
        return original(self, context, name, extra_args)

    monkeypatch.setattr(ClaudeDriver, "_session", capture)
    probe(private_dir, token_file, home, fake_claude(private_dir))

    sessions = session_argv(private_dir)
    assert len(sessions) == 5
    for args in sessions:
        for flag in ("--safe-mode", "--restricted", "--strict-mcp-config", "--disable-slash-commands"):
            assert flag in args
        assert args[args.index("--setting-sources") + 1] == ""
        assert args[args.index("--permission-prompt-tool") + 1] == "stdio"
        assert args[args.index("--settings") + 1].endswith("/probes/probe-test/claude-settings.json")
    # Only the first session has tools: Bash and Write, to prove the two denials.
    assert sessions[1][sessions[1].index("--tools") + 1] == "Bash,Write"

    cwd = str(probe_cwd(private_dir))
    real = os.path.realpath
    settings = captured["settings"]
    sandbox = settings["sandbox"]
    assert sandbox["enabled"] is True
    assert sandbox["failIfUnavailable"] is True
    assert sandbox["allowUnsandboxedCommands"] is False
    assert sandbox["filesystem"]["denyWrite"] == [cwd]
    deny_read = set(sandbox["filesystem"]["denyRead"])
    assert {
        real(private_dir / "runs"),
        str(token_file),
        real(private_dir / "plane"),
        real(home / ".claude"),
        real(home / ".claude.json"),
        real(home / ".ssh"),
    } <= deny_read
    assert sandbox["filesystem"]["allowRead"] == [str(Path(cwd).parent)]
    permissions = settings["permissions"]
    assert f"Edit(/{cwd}/**)" in permissions["deny"]
    assert f"Read(/{token_file})" in permissions["deny"]
    assert f"Read(/{real(home / '.claude')}/**)" in permissions["deny"]
    assert permissions["blockReadsOutsideWorkingDirectories"] is True
    assert permissions["disableBypassPermissionsMode"] == "disable"
    assert settings["disableAllHooks"] is True


def test_settings_file_is_private_and_outside_the_working_directory(private_dir, token_file, home, monkeypatch):
    seen = {}
    original = ClaudeDriver._session

    def capture(self, context, name, extra_args=()):
        path = Path(context["settings_file"])
        seen.setdefault("mode", path.stat().st_mode & 0o777)
        seen.setdefault("parent", path.parent)
        return original(self, context, name, extra_args)

    monkeypatch.setattr(ClaudeDriver, "_session", capture)
    probe(private_dir, token_file, home, fake_claude(private_dir))

    assert seen["mode"] == 0o600
    assert seen["parent"] == probe_cwd(private_dir).parent


@pytest.mark.parametrize("tool", ["Write", "Bash"])
def test_write_despite_the_denial_fails_the_permission_check(private_dir, token_file, home, tool):
    executable = fake_claude(private_dir, scenario="writes_despite_denial", write_tool=tool)

    report = probe(private_dir, token_file, home, executable)

    checks = checks_of(report)
    assert checks["permission"]["passed"] is False
    assert tool in checks["permission"]["detail"]
    assert all(check["passed"] for name, check in checks.items() if name != "permission")


def test_permission_prompt_instead_of_a_rule_denial_fails_the_permission_check(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, fake_claude(private_dir, scenario="prompts_for_write"))

    checks = checks_of(report)
    assert checks["permission"]["passed"] is False
    assert "permission rule" in checks["permission"]["detail"]
    assert report["capabilities"]["permission_prompt"] is True


def test_ignored_interrupt_fails_the_interruption_check(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, fake_claude(private_dir, scenario="no_interrupt"))

    checks = checks_of(report)
    assert checks["interruption"]["passed"] is False
    assert all(check["passed"] for name, check in checks.items() if name != "interruption")


def test_session_lost_after_a_crash_fails_the_recovery_check(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, fake_claude(private_dir, scenario="crash_not_resumable"))

    checks = checks_of(report)
    assert checks["recovery"]["passed"] is False
    assert checks["follow_up"]["passed"] is True
    assert all(check["passed"] for name, check in checks.items() if name != "recovery")


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
    # The CLI error text stays in the Worker log; the report carries a fixed message.
    assert "No conversation found" not in json.dumps(report)


def test_missing_cli_is_a_blocking_issue(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, private_dir / "bin" / "absent-claude")

    assert report["blocking_issue"] == "harness_not_found"
    assert all(not check["passed"] for check in report["checks"])


def test_unsupported_version_is_a_blocking_issue(private_dir, token_file, home):
    report = probe(private_dir, token_file, home, fake_claude(private_dir, version="3.0.0"))

    assert report["blocking_issue"] == "unsupported_version"
    assert report["harness_version"] == "3.0.0"
    assert "3.0.0" in report["failure_hint"]


def test_location_shows_the_home_directory_as_a_tilde(private_dir, token_file, home):
    executable = home / ".local" / "bin" / "claude"
    executable.parent.mkdir(parents=True)
    shutil.copy(fake_claude(private_dir), executable)

    report = probe(private_dir, token_file, home, executable)

    assert report["location"] == "~/.local/bin/claude"


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
    assert {"HOME", "PATH", "TMPDIR", "CLAUDE_CODE_TMPDIR", "ANTHROPIC_API_KEY"} <= names
    forbidden = {"PLANE_AGENT_WORKER_TOKEN_FILE", "CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "AWS_SECRET_ACCESS_KEY"}
    assert not names & forbidden


@pytest.mark.parametrize("scenario", ["ok", "no_interrupt", "crash_not_resumable", "writes_despite_denial"])
def test_probe_leaves_no_process_record_probe_directory_or_session_directory(private_dir, token_file, home, scenario):
    probe(private_dir, token_file, home, fake_claude(private_dir, scenario=scenario, write_tool="Bash"))

    assert list((private_dir / "runs" / ".processes").iterdir()) == []
    assert not (private_dir / "runs" / "probes" / "probe-test").exists()
    sessions = home / ".claude" / "projects" / session_dir_name(probe_cwd(private_dir))
    assert (home / ".claude" / "projects").is_dir()
    assert not sessions.exists()


@pytest.mark.native
@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("claude"), reason="needs macOS and the claude CLI")
def test_real_claude_probe_passes_with_the_built_in_sandbox(private_dir, token_file):
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
    )

    assert all(check["passed"] for check in report["checks"]), report["checks"]
    assert report["models"]
    assert report["capabilities"]["native_resume"] is True
    assert not (run_root / "probes" / "native-probe").exists()
