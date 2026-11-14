# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
import os
import subprocess

import pytest

from plane_agent_worker.sandbox import (
    KIT_ALLOW_LIST,
    VM_SETTINGS,
    VM_USER_CLAUDE,
    Mount,
    SandboxError,
    Sandboxes,
    SandboxSpec,
    gateway_rule,
    skill_mounts,
    user_config_mounts,
)


def sandboxes(fake_sbx, host_home, memory=None):
    return Sandboxes(str(fake_sbx.path), host_home, memory=memory, base_env={"PATH": os.environ["PATH"]})


def spec(private_dir, host_home, name="plane-test-a", allow=()):
    primary = private_dir / "sandboxes" / name / "scratch"
    return SandboxSpec(name=name, primary=primary, mounts=user_config_mounts(host_home), allow=allow)


def test_signed_in_check_passes_and_fails_with_the_sign_in_hint(fake_sbx, host_home):
    sandboxes(fake_sbx, host_home).check_signed_in()

    fake_sbx.set_scenario("signed_out")
    with pytest.raises(SandboxError) as error:
        sandboxes(fake_sbx, host_home).check_signed_in()
    assert error.value.code == "sandbox_not_signed_in"
    assert "sbx login" in error.value.detail


def test_missing_sbx_is_reported(private_dir, host_home):
    with pytest.raises(SandboxError) as error:
        Sandboxes(str(private_dir / "no-sbx"), host_home).check_signed_in()
    assert error.value.code == "sandbox_cli_missing"


def test_first_use_creates_the_sandbox_with_read_only_config_and_network_rules(private_dir, fake_sbx, host_home):
    box = spec(private_dir, host_home, allow=("host.docker.internal:7450",))

    created = sandboxes(fake_sbx, host_home, memory="4g").ensure(box)

    assert created is True
    [create] = fake_sbx.commands("create")
    assert create[:9] == [
        "--no-input",
        "create",
        "--name",
        "plane-test-a",
        "--static-mcp",
        "none",
        "--memory",
        "4g",
        "claude",
    ]
    assert create[9] == str(box.primary)
    assert f"{host_home / '.claude' / 'settings.json'}:{VM_SETTINGS}:ro" in create
    assert all(argument.endswith(":ro") for argument in create[10:])
    rules = fake_sbx.sandbox("plane-test-a")["rules"]
    assert rules == [["allow", "gateway.test:8317"], ["allow", "host.docker.internal:7450"], ["deny", KIT_ALLOW_LIST]]
    assert box.primary.is_dir()


def test_second_use_only_checks_health(private_dir, fake_sbx, host_home):
    box = spec(private_dir, host_home)
    sandboxes(fake_sbx, host_home).ensure(box)

    created = sandboxes(fake_sbx, host_home).ensure(box)

    assert created is False
    assert len(fake_sbx.commands("create")) == 1
    health = fake_sbx.commands("exec")[-1]
    assert health == ["exec", "plane-test-a", "sh", "-c", f"test -r {VM_SETTINGS}"]


def test_missing_sandbox_is_created_again(private_dir, fake_sbx, host_home):
    box = spec(private_dir, host_home)
    sandboxes(fake_sbx, host_home).ensure(box)
    (fake_sbx.state / "sandboxes" / "plane-test-a.json").unlink()

    assert sandboxes(fake_sbx, host_home).ensure(box) is True
    assert len(fake_sbx.commands("create")) == 2


def test_stopped_sandbox_is_started_by_the_health_check(private_dir, fake_sbx, host_home):
    box = spec(private_dir, host_home)
    sandboxes(fake_sbx, host_home).ensure(box)
    subprocess.run([str(fake_sbx.path), "stop", "plane-test-a"], check=True)

    assert sandboxes(fake_sbx, host_home).ensure(box) is False
    assert fake_sbx.sandbox("plane-test-a")["running"] is True


def test_stale_settings_mount_stops_the_sandbox_once_and_continues(private_dir, fake_sbx, host_home):
    box = spec(private_dir, host_home)
    sandboxes(fake_sbx, host_home).ensure(box)
    fake_sbx.set_scenario("stale_settings")

    assert sandboxes(fake_sbx, host_home).ensure(box) is False
    assert fake_sbx.commands("stop") == [["stop", "plane-test-a"]]
    assert len(fake_sbx.commands("create")) == 1


def test_other_health_failure_is_sandbox_unavailable(private_dir, fake_sbx, host_home):
    box = spec(private_dir, host_home)
    sandboxes(fake_sbx, host_home).ensure(box)
    fake_sbx.set_scenario("broken")

    with pytest.raises(SandboxError) as error:
        sandboxes(fake_sbx, host_home).ensure(box)
    assert error.value.code == "sandbox_unavailable"
    assert "daemon failed" in error.value.detail


def test_failed_create_is_sandbox_unavailable(private_dir, fake_sbx, host_home):
    fake_sbx.set_scenario("create_fails")

    with pytest.raises(SandboxError) as error:
        sandboxes(fake_sbx, host_home).ensure(spec(private_dir, host_home))
    assert error.value.code == "sandbox_unavailable"


def test_changed_skill_link_targets_recreate_the_sandbox(private_dir, fake_sbx, host_home):
    sandboxes(fake_sbx, host_home).ensure(spec(private_dir, host_home))
    repo_skill = private_dir / "repo" / "skills" / "new-skill"
    repo_skill.mkdir(parents=True)
    (host_home / ".claude" / "skills").mkdir()
    (host_home / ".claude" / "skills" / "new-skill").symlink_to(repo_skill)

    assert sandboxes(fake_sbx, host_home).ensure(spec(private_dir, host_home)) is True
    assert fake_sbx.commands("rm")[-1] == ["rm", "--force", "plane-test-a"]
    assert f"{repo_skill}:ro" in fake_sbx.commands("create")[-1]


def test_skills_and_every_link_target_are_mounted_read_only(private_dir, host_home):
    skills = host_home / ".claude" / "skills"
    agents = host_home / ".agents" / "skills"
    (skills / "local-skill").mkdir(parents=True)
    (agents / "a").mkdir(parents=True)
    (agents / "b").mkdir()
    outside = private_dir / "repos" / "pack" / "skills" / "c"
    outside.mkdir(parents=True)
    under_home = host_home / "work" / "pack" / "d"
    under_home.mkdir(parents=True)
    (skills / "a").symlink_to("../../.agents/skills/a")
    (skills / "b").symlink_to(agents / "b")
    (skills / "c").symlink_to(outside)
    (skills / "d").symlink_to("../../work/pack/d")
    (skills / "gone").symlink_to(private_dir / "missing")

    mounts = skill_mounts(host_home)

    assert mounts == [
        Mount(str(skills), f"{VM_USER_CLAUDE}/.claude/skills"),
        Mount(str(agents), f"{VM_USER_CLAUDE}/.agents/skills"),
        Mount(str(agents)),
        Mount(str(outside), str(outside)),
        Mount(str(under_home), f"{VM_USER_CLAUDE}/work/pack/d"),
    ]


def test_hooks_are_mounted_at_their_host_path(host_home):
    (host_home / ".claude" / "hooks").mkdir()

    mounts = user_config_mounts(host_home)

    assert mounts[0] == Mount(str(host_home / ".claude" / "settings.json"), VM_SETTINGS)
    assert Mount(str(host_home / ".claude" / "hooks")) in mounts
    assert mounts[1].argument() == f"{host_home / '.claude' / 'hooks'}:ro"


def test_gateway_rule_reads_only_the_base_url(host_home):
    assert gateway_rule(host_home) == "gateway.test:8317"
    (host_home / ".claude" / "settings.json").write_text(json.dumps({"env": {"ANTHROPIC_BASE_URL": "https://gw.test"}}))
    assert gateway_rule(host_home) == "gw.test:443"
    (host_home / ".claude" / "settings.json").write_text("{}")
    assert gateway_rule(host_home) is None


def test_no_gateway_in_settings_adds_no_allow_rule(private_dir, fake_sbx, host_home):
    (host_home / ".claude" / "settings.json").write_text("{}")

    sandboxes(fake_sbx, host_home).ensure(spec(private_dir, host_home))

    assert fake_sbx.sandbox("plane-test-a")["rules"] == [["deny", KIT_ALLOW_LIST]]


def test_gateway_token_is_never_in_an_sbx_argv(private_dir, fake_sbx, host_home):
    box = spec(private_dir, host_home)
    box.primary.mkdir(parents=True)
    worker = sandboxes(fake_sbx, host_home)
    worker.ensure(box)
    subprocess.run(worker.exec_argv(box.name, box.primary, ["true"], interactive=False), check=True)

    assert "gateway-secret-0001" not in json.dumps(fake_sbx.calls())


def test_exec_argv_writes_a_pidfile_and_passes_no_environment(private_dir, fake_sbx, host_home):
    argv = sandboxes(fake_sbx, host_home).exec_argv(
        "plane-test-a", "/work/clone", ["claude", "-p"], pidfile="/s/r 1/agent.pid"
    )

    assert argv == [
        str(fake_sbx.path),
        "exec",
        "-i",
        "-w",
        "/work/clone",
        "plane-test-a",
        "sh",
        "-c",
        "echo $$ > '/s/r 1/agent.pid'; exec \"$@\"",
        "sh",
        "claude",
        "-p",
    ]


def test_pidfile_kill_stops_the_process_inside(private_dir, fake_sbx, host_home):
    box = spec(private_dir, host_home)
    worker = sandboxes(fake_sbx, host_home)
    worker.ensure(box)
    pidfile = box.primary / "sleep.pid"
    process = subprocess.Popen(
        worker.exec_argv(box.name, box.primary, ["sleep", "30"], pidfile=pidfile), stdin=subprocess.PIPE
    )
    for _ in range(100):
        if pidfile.exists() and pidfile.read_text().strip():
            break
        subprocess.run(["sleep", "0.05"])

    assert worker.kill(box.name, pidfile) is True
    assert process.wait(timeout=5) != 0
    assert fake_sbx.commands("exec")[-1] == ["exec", "plane-test-a", "sh", "-c", f'kill -KILL "$(cat {pidfile})"']


def test_client_environment_has_no_credentials(fake_sbx, host_home):
    worker = Sandboxes(
        str(fake_sbx.path),
        host_home,
        base_env={"HOME": "/h", "PATH": "/bin", "ANTHROPIC_AUTH_TOKEN": "x", "PLANE_AGENT_WORKER_TOKEN_FILE": "/t"},
    )

    assert worker.client_env == {"HOME": "/h", "PATH": "/bin"}
