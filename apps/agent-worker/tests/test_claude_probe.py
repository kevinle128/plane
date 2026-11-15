# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

from plane_agent_worker.conformance import REPORT_VERSION, run_probe
from plane_agent_worker.drivers.base import REQUIRED_CHECKS
from plane_agent_worker.drivers.claude import SUITE_VERSION, ClaudeDriver
from plane_agent_worker.process_registry import ProcessRegistry
from plane_agent_worker.sandbox import VM_SETTINGS, Sandboxes

FAKE = Path(__file__).parent / "fakes" / "fake_claude.py"
PROBE_SANDBOX = "plane-probe-claude-code"


def fake_claude(fake_sbx, scenario="ok", version="2.1.289"):
    """The fake ``claude`` on the PATH of the fake sandbox VM."""
    executable = fake_sbx.vm_bin / "claude"
    root = fake_sbx.state.parent
    executable.write_text(
        "#!/bin/sh\n"
        f"export FAKE_CLAUDE_SCENARIO={scenario}\n"
        f"export FAKE_CLAUDE_VERSION={version}\n"
        f'export FAKE_CLAUDE_ARGV_LOG="{root / "argv.jsonl"}"\n'
        f'export FAKE_CLAUDE_MIDTURN_LOG="{root / "midturn.jsonl"}"\n'
        f'env | cut -d= -f1 | sort > "{root / "harness-env.txt"}"\n'
        f'exec "{sys.executable}" "{FAKE}" "$@"\n'
    )
    executable.chmod(0o700)
    return executable


def probe(private_dir, token_file, fake_sbx, host_home, extra_env=None, sbx_path=None):
    checkout = private_dir / "plane"
    checkout.mkdir(exist_ok=True)
    run_root = private_dir / "runs"
    run_root.mkdir(exist_ok=True, mode=0o700)
    env = {"HOME": str(host_home), "PATH": os.environ["PATH"], "LANG": "C.UTF-8", **(extra_env or {})}
    driver = ClaudeDriver(
        sandboxes=Sandboxes(str(sbx_path or fake_sbx.path), host_home, base_env=env),
        run_root=run_root,
        registry=ProcessRegistry(run_root / ".processes"),
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


def scratch(private_dir):
    return Path(os.path.realpath(private_dir / "runs")) / "sandboxes" / "probe-claude_code" / "scratch"


def session_argv(private_dir):
    """The arguments of each stream session (not ``--version`` or ``auth status``)."""
    calls = [json.loads(line) for line in (private_dir / "argv.jsonl").read_text().splitlines()]
    return [args for args in calls if "-p" in args]


def test_fake_claude_passes_every_check(private_dir, token_file, fake_sbx, host_home):
    fake_claude(fake_sbx)
    report = probe(private_dir, token_file, fake_sbx, host_home)

    assert report["version"] == REPORT_VERSION
    assert [check["name"] for check in report["checks"]] == list(REQUIRED_CHECKS)
    assert all(check["passed"] for check in report["checks"]), report["checks"]
    assert report["harness_version"] == "2.1.289"
    assert report["blocking_issue"] is None
    assert report["location"] == f"sbx sandbox {PROBE_SANDBOX}"
    # The model list is the one recorded from Claude Code 2.1.289.
    assert [model["id"] for model in report["models"]] == ["default", "opus", "claude-fable-5-1[1m]", "sonnet", "haiku"]
    assert report["models"][4] == {
        "id": "haiku",
        "label": "Haiku",
        "description": "Haiku 4.5 · Fastest for quick answers · $1/$5 per Mtok",
        "source": "reported",
    }
    assert {model["source"] for model in report["models"]} == {"reported"}
    # Full permissions inside the sandbox: no permission prompt arrives.
    assert report["capabilities"] == {"midturn_input": False, "native_resume": True, "permission_prompt": False}
    assert report["suite"]["ran_now"] is True
    assert report["suite"]["cli_version"] == "2.1.289"
    assert report["suite"]["suite_version"] == SUITE_VERSION == 3
    assert datetime.fromisoformat(report["suite"]["verified_at"]).tzinfo is not None


def test_every_claude_process_runs_in_the_probe_sandbox_with_full_permissions(
    private_dir, token_file, fake_sbx, host_home
):
    fake_claude(fake_sbx)
    probe(private_dir, token_file, fake_sbx, host_home)

    sessions = session_argv(private_dir)
    # The model list of this Connect, then the suite: its own model list and sessions A to D.
    assert len(sessions) == 6
    for args in sessions:
        assert "--dangerously-skip-permissions" in args
        assert args[args.index("--settings") + 1].endswith(VM_SETTINGS)
        # The probe and the suite load no MCP server: strict MCP config without a config file.
        assert "--strict-mcp-config" in args and "--mcp-config" not in args
        assert args[args.index("--permission-prompt-tool") + 1] == "stdio"
    assert sessions[2][sessions[2].index("--tools") + 1] == "Bash"
    assert all("--tools" not in args for args in sessions[:2])

    claude_execs = [call for call in fake_sbx.commands("exec") if "claude" in call]
    assert claude_execs
    for call in claude_execs:
        assert call[call.index("-w") + 1].startswith(str(scratch(private_dir)))
        assert PROBE_SANDBOX in call
        # No environment passes: the scrub variable would turn off full permissions.
        assert "-e" not in call
    [create] = fake_sbx.commands("create")
    assert create[create.index("claude") + 1] == str(scratch(private_dir))
    assert f"{host_home / '.claude' / 'settings.json'}:{VM_SETTINGS}:ro" in create
    # The gateway token stays in the mounted settings file; no sbx call carries it.
    assert "gateway-secret-0001" not in json.dumps(fake_sbx.calls())


def test_cli_outside_bypass_mode_fails_the_permission_check(private_dir, token_file, fake_sbx, host_home):
    fake_claude(fake_sbx, scenario="no_bypass")
    report = probe(private_dir, token_file, fake_sbx, host_home)

    check = checks_of(report)["permission"]
    assert check["passed"] is False
    assert "bypassPermissions" in check["detail"]
    assert all(check["passed"] for name, check in checks_of(report).items() if name != "permission")


def test_permission_prompt_under_full_permissions_fails_the_permission_check(
    private_dir, token_file, fake_sbx, host_home
):
    fake_claude(fake_sbx, scenario="prompts_for_bash")
    report = probe(private_dir, token_file, fake_sbx, host_home)

    check = checks_of(report)["permission"]
    assert check["passed"] is False
    assert "permission request" in check["detail"]
    assert report["capabilities"]["permission_prompt"] is True


def test_missing_sbx_is_a_blocking_issue(private_dir, token_file, fake_sbx, host_home):
    report = probe(private_dir, token_file, fake_sbx, host_home, sbx_path=private_dir / "absent-sbx")

    assert report["blocking_issue"] == "harness_not_found"
    assert "sbx" in report["failure_hint"]
    assert all(not check["passed"] for check in report["checks"])


def test_missing_docker_sign_in_blocks_with_the_sign_in_action(private_dir, token_file, fake_sbx, host_home):
    fake_claude(fake_sbx)
    fake_sbx.set_scenario("signed_out")

    report = probe(private_dir, token_file, fake_sbx, host_home)

    assert report["blocking_issue"] == "sandbox_not_signed_in"
    assert "sbx login" in report["failure_hint"]
    assert fake_sbx.commands("create") == []


def test_unavailable_probe_sandbox_fails_with_its_reason(private_dir, token_file, fake_sbx, host_home):
    fake_claude(fake_sbx)
    fake_sbx.set_scenario("create_fails")

    report = probe(private_dir, token_file, fake_sbx, host_home)

    assert "sandbox" in report["failure_hint"]
    assert all(not check["passed"] for check in report["checks"])


def run_scenario(private_dir, token_file, fake_sbx, host_home, scenario="ok", version="2.1.289", **kwargs):
    fake_claude(fake_sbx, scenario=scenario, version=version)
    return probe(private_dir, token_file, fake_sbx, host_home, **kwargs)


def test_ignored_interrupt_fails_the_interruption_check(private_dir, token_file, fake_sbx, host_home):
    report = run_scenario(private_dir, token_file, fake_sbx, host_home, "no_interrupt")

    checks = checks_of(report)
    assert checks["interruption"]["passed"] is False
    assert all(check["passed"] for name, check in checks.items() if name != "interruption")


def test_interruption_sends_no_message_during_the_turn(private_dir, token_file, fake_sbx, host_home):
    report = run_scenario(private_dir, token_file, fake_sbx, host_home)

    assert checks_of(report)["interruption"]["passed"] is True
    assert not (private_dir / "midturn.jsonl").exists()


def test_midturn_input_is_not_reported_for_claude(private_dir, token_file, fake_sbx, host_home):
    # Send now for Claude stops the turn and sends the message as the next turn, so the
    # driver does not measure midturn input even when the CLI would take it.
    report = run_scenario(private_dir, token_file, fake_sbx, host_home, "midturn_replay")

    assert report["capabilities"]["midturn_input"] is False
    assert checks_of(report)["interruption"]["passed"] is True


def test_session_lost_after_a_crash_fails_the_recovery_check(private_dir, token_file, fake_sbx, host_home):
    report = run_scenario(private_dir, token_file, fake_sbx, host_home, "crash_not_resumable")

    checks = checks_of(report)
    assert checks["recovery"]["passed"] is False
    assert checks["follow_up"]["passed"] is True
    assert all(check["passed"] for name, check in checks.items() if name != "recovery")


def test_crash_is_a_kill_of_the_pidfile_inside_the_sandbox(private_dir, token_file, fake_sbx, host_home):
    report = run_scenario(private_dir, token_file, fake_sbx, host_home)

    assert checks_of(report)["recovery"]["passed"] is True
    kills = [call for call in fake_sbx.commands("exec") if call[-1].startswith("kill -KILL")]
    assert len(kills) == 1
    assert kills[0][1] == PROBE_SANDBOX
    assert "session-c.pid" in kills[0][-1]


def test_not_logged_in_fails_authentication_and_skips_the_rest(private_dir, token_file, fake_sbx, host_home):
    report = run_scenario(private_dir, token_file, fake_sbx, host_home, "not_logged_in")

    assert checks_of(report)["authentication"]["passed"] is False
    assert all(not check["passed"] for check in report["checks"])
    assert report["models"] == []
    assert "not logged in" in report["failure_hint"]
    assert report["suite"] is None


def test_empty_model_list_fails_the_model_report(private_dir, token_file, fake_sbx, host_home):
    report = run_scenario(private_dir, token_file, fake_sbx, host_home, "no_models")

    assert checks_of(report)["model_report"]["passed"] is False
    assert report["models"] == []


FALLBACK_IDS = ["opus", "sonnet", "haiku"]


def test_model_list_request_is_one_shot(private_dir, token_file, fake_sbx, host_home):
    # The CLI answers only after stdin closes, so the request must not wait with stdin open.
    report = run_scenario(private_dir, token_file, fake_sbx, host_home, "init_after_eof")

    assert checks_of(report)["model_report"]["passed"] is True
    assert {model["source"] for model in report["models"]} == {"reported"}


def test_failed_model_request_at_connect_gives_the_fallback_list_and_the_suite_result(
    private_dir, token_file, fake_sbx, host_home
):
    report = run_scenario(private_dir, token_file, fake_sbx, host_home, "no_initialize_at_connect")

    assert [model["id"] for model in report["models"]] == FALLBACK_IDS
    assert {model["source"] for model in report["models"]} == {"fallback"}
    assert all(check["passed"] for check in report["checks"]), report["checks"]
    assert report["suite"]["ran_now"] is True


def test_failed_model_request_on_a_verified_version_uses_the_cached_model_report(
    private_dir, token_file, fake_sbx, host_home
):
    run_scenario(private_dir, token_file, fake_sbx, host_home)

    report = run_scenario(private_dir, token_file, fake_sbx, host_home, "no_initialize")

    assert [model["id"] for model in report["models"]] == FALLBACK_IDS
    assert checks_of(report)["model_report"]["passed"] is True
    assert report["suite"]["ran_now"] is False


def test_suite_without_a_real_model_report_fails_the_model_report(private_dir, token_file, fake_sbx, host_home):
    report = run_scenario(private_dir, token_file, fake_sbx, host_home, "no_initialize")

    check = checks_of(report)["model_report"]
    assert check["passed"] is False
    assert "model" in check["detail"]
    assert report["suite"] is None
    assert not (private_dir / "runs" / "state" / "conformance.json").exists()


def test_lost_session_fails_follow_up_and_recovery(private_dir, token_file, fake_sbx, host_home):
    report = run_scenario(private_dir, token_file, fake_sbx, host_home, "no_resume")

    checks = checks_of(report)
    assert checks["follow_up"]["passed"] is False
    assert checks["recovery"]["passed"] is False
    assert report["capabilities"]["native_resume"] is False
    assert checks["progress"]["passed"] is True
    # The CLI error text stays in the Worker log; the report carries a fixed message.
    assert "No conversation found" not in json.dumps(report)


def test_missing_cli_in_the_sandbox_is_a_blocking_issue(private_dir, token_file, fake_sbx, host_home):
    report = probe(private_dir, token_file, fake_sbx, host_home)

    assert report["blocking_issue"] == "harness_not_found"
    assert all(not check["passed"] for check in report["checks"])


def test_unsupported_version_is_a_blocking_issue(private_dir, token_file, fake_sbx, host_home):
    report = run_scenario(private_dir, token_file, fake_sbx, host_home, version="3.0.0")

    assert report["blocking_issue"] == "unsupported_version"
    assert report["harness_version"] == "3.0.0"
    assert "3.0.0" in report["failure_hint"]


def test_claude_in_the_sandbox_gets_no_host_environment(private_dir, token_file, fake_sbx, host_home):
    secret_env = {
        "PLANE_AGENT_WORKER_TOKEN_FILE": str(token_file),
        "CLAUDECODE": "1",
        "CLAUDE_CODE_SESSION_ID": "outer-session",
        "AWS_SECRET_ACCESS_KEY": "do-not-pass",
        "ANTHROPIC_API_KEY": "operator-key",
        "ANTHROPIC_AUTH_TOKEN": "operator-token",
    }

    run_scenario(private_dir, token_file, fake_sbx, host_home, extra_env=secret_env)

    names = set((private_dir / "harness-env.txt").read_text().split())
    assert {"HOME", "PATH"} <= names
    assert not names & {*secret_env, "TMPDIR", "CLAUDE_CODE_TMPDIR", "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB"}


@pytest.mark.parametrize("scenario", ["ok", "no_interrupt", "crash_not_resumable", "no_bypass"])
def test_probe_leaves_no_process_record_or_probe_directory(private_dir, token_file, fake_sbx, host_home, scenario):
    run_scenario(private_dir, token_file, fake_sbx, host_home, scenario)

    assert list((private_dir / "runs" / ".processes").iterdir()) == []
    assert list(scratch(private_dir).iterdir()) == []


def probe_calls(private_dir):
    path = private_dir / "argv.jsonl"
    calls = [json.loads(line) for line in path.read_text().splitlines()]
    path.unlink()
    return calls


def test_second_probe_on_a_verified_version_runs_only_the_quick_check(private_dir, token_file, fake_sbx, host_home):
    first = run_scenario(private_dir, token_file, fake_sbx, host_home)
    probe_calls(private_dir)

    report = probe(private_dir, token_file, fake_sbx, host_home)

    assert report["suite"] == {**first["suite"], "ran_now": False}
    calls = probe_calls(private_dir)
    assert calls[0] == ["--version"]
    assert calls[1][-2:] == ["auth", "status"] and calls[1][calls[1].index("--settings") + 1].endswith(VM_SETTINGS)
    # One more process: the model list. No suite session runs.
    assert len(calls) == 3 and "-p" in calls[2] and "--tools" not in calls[2]
    assert all(check["passed"] for check in report["checks"]), report["checks"]
    assert report["capabilities"] == {"midturn_input": False, "native_resume": True, "permission_prompt": False}
    record = json.loads((private_dir / "runs" / "state" / "conformance.json").read_text())
    assert list(record["records"]) == [f"claude_code/2.1.289/{SUITE_VERSION}"]
    # The probe sandbox is created once and reused.
    assert len(fake_sbx.commands("create")) == 1


def test_failed_suite_runs_again_on_the_next_probe(private_dir, token_file, fake_sbx, host_home):
    run_scenario(private_dir, token_file, fake_sbx, host_home, "no_interrupt")
    probe_calls(private_dir)

    report = probe(private_dir, token_file, fake_sbx, host_home)

    assert len([args for args in probe_calls(private_dir) if "-p" in args]) == 6
    assert checks_of(report)["interruption"]["passed"] is False
    assert report["suite"] is None
    assert not (private_dir / "runs" / "state" / "conformance.json").exists()


def test_probe_on_a_new_cli_version_runs_the_suite_again(private_dir, token_file, fake_sbx, host_home):
    run_scenario(private_dir, token_file, fake_sbx, host_home)
    probe_calls(private_dir)

    report = run_scenario(private_dir, token_file, fake_sbx, host_home, version="2.1.290")

    assert len([args for args in probe_calls(private_dir) if "-p" in args]) == 6
    assert all(check["passed"] for check in report["checks"])
    record = json.loads((private_dir / "runs" / "state" / "conformance.json").read_text())
    assert sorted(record["records"]) == [f"claude_code/2.1.289/{SUITE_VERSION}", f"claude_code/2.1.290/{SUITE_VERSION}"]


@pytest.mark.native
@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("sbx"), reason="needs macOS and the sbx CLI")
def test_real_claude_probe_in_a_sandbox_passes_and_a_second_probe_uses_the_cached_suite(private_dir, token_file):
    checkout = Path(__file__).resolve().parents[3]
    run_root = private_dir / "runs"
    run_root.mkdir(mode=0o700)
    sandboxes = Sandboxes(shutil.which("sbx"), Path.home(), prefix="plane-test-")
    driver = ClaudeDriver(sandboxes=sandboxes, run_root=run_root, registry=ProcessRegistry(run_root / ".processes"))

    def connect(probe_key):
        started = time.monotonic()
        report = run_probe(
            driver,
            run_root=run_root,
            probe_key=probe_key,
            token_file=token_file,
            plane_checkout=checkout,
        )
        return report, time.monotonic() - started

    try:
        first, _ = connect("native-probe-1")
        second, second_seconds = connect("native-probe-2")
    finally:
        sandboxes.remove("plane-test-probe-claude-code")

    for report in (first, second):
        assert all(check["passed"] for check in report["checks"]), report["checks"]
        assert report["models"]
        assert report["capabilities"]["native_resume"] is True
    assert first["suite"]["ran_now"] is True
    assert second["suite"] == {**first["suite"], "ran_now": False}
    assert second_seconds < 20
    records = json.loads((run_root / "state" / "conformance.json").read_text())["records"]
    assert list(records) == [f"claude_code/{first['harness_version']}/{SUITE_VERSION}"]
