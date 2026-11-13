# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os

import pytest

from plane_agent_worker.config import ConfigError, load_config


def env_for(private_dir, token_file, **overrides):
    checkout = private_dir / "plane"
    checkout.mkdir(exist_ok=True)
    env = {
        "PLANE_AGENT_WORKER_API_ORIGIN": "http://localhost:8000",
        "PLANE_AGENT_WORKER_TOKEN_FILE": str(token_file),
        "PLANE_AGENT_WORKER_RUN_ROOT": str(private_dir / "runs"),
        "PLANE_AGENT_WORKER_PLANE_CHECKOUT": str(checkout),
    }
    env.update(overrides)
    return env


def test_valid_config_loads_and_creates_a_private_run_root(private_dir, token_file):
    config = load_config(env_for(private_dir, token_file))

    assert config.api_origin == "http://localhost:8000"
    assert config.run_root == private_dir / "runs"
    assert (os.stat(config.run_root).st_mode & 0o777) == 0o700
    assert config.read_token() == "plane_aw_test-token-value-0001"


def test_token_is_not_in_the_config_repr(private_dir, token_file):
    config = load_config(env_for(private_dir, token_file))

    assert "plane_aw_test-token-value-0001" not in repr(config)


@pytest.mark.parametrize("origin", ["http://localhost:8000", "https://127.0.0.1:8443", "http://[::1]:8000"])
def test_localhost_origins_are_accepted(private_dir, token_file, origin):
    assert load_config(env_for(private_dir, token_file, PLANE_AGENT_WORKER_API_ORIGIN=origin)).api_origin == origin


@pytest.mark.parametrize(
    "origin",
    [
        "https://plane.example.com",
        "http://10.0.0.5:8000",
        "http://localhost.example.com:8000",
        "http://user:secret@localhost:8000",
        "http://localhost:8000/api",
        "http://localhost:8000?next=1",
        "http://localhost:8000#top",
        "ftp://localhost",
        "localhost:8000",
    ],
)
def test_non_localhost_or_unclean_origin_is_rejected(private_dir, token_file, origin):
    with pytest.raises(ConfigError, match="PLANE_AGENT_WORKER_API_ORIGIN"):
        load_config(env_for(private_dir, token_file, PLANE_AGENT_WORKER_API_ORIGIN=origin))


def test_token_file_inside_the_run_root_is_rejected(private_dir, token_file):
    run_root = private_dir / "runs"
    run_root.mkdir(mode=0o700)
    inside = run_root / "worker-token"
    inside.write_text("plane_aw_x\n")
    inside.chmod(0o600)

    with pytest.raises(ConfigError, match="outside the Run root"):
        load_config(env_for(private_dir, token_file, PLANE_AGENT_WORKER_TOKEN_FILE=str(inside)))


def test_token_file_readable_by_others_is_rejected(private_dir, token_file):
    token_file.chmod(0o644)

    with pytest.raises(ConfigError, match="0600"):
        load_config(env_for(private_dir, token_file))


def test_token_file_symlink_is_rejected(private_dir, token_file):
    link = private_dir / "token-link"
    link.symlink_to(token_file)

    with pytest.raises(ConfigError, match="symbolic link"):
        load_config(env_for(private_dir, token_file, PLANE_AGENT_WORKER_TOKEN_FILE=str(link)))


def test_empty_token_file_is_rejected(private_dir, token_file):
    token_file.write_text("\n")

    with pytest.raises(ConfigError, match="empty"):
        load_config(env_for(private_dir, token_file))


def test_missing_token_file_is_rejected(private_dir, token_file):
    with pytest.raises(ConfigError, match="does not exist"):
        load_config(env_for(private_dir, token_file, PLANE_AGENT_WORKER_TOKEN_FILE=str(private_dir / "missing")))


def test_run_root_inside_the_plane_checkout_is_rejected(private_dir, token_file):
    checkout = private_dir / "plane"
    checkout.mkdir()

    with pytest.raises(ConfigError, match="outside the Plane checkout"):
        load_config(env_for(private_dir, token_file, PLANE_AGENT_WORKER_RUN_ROOT=str(checkout / "runs")))


def test_plane_checkout_inside_the_run_root_is_rejected(private_dir, token_file):
    run_root = private_dir / "runs"
    (run_root / "plane").mkdir(parents=True, mode=0o700)
    run_root.chmod(0o700)

    with pytest.raises(ConfigError, match="outside the Plane checkout"):
        load_config(env_for(private_dir, token_file, PLANE_AGENT_WORKER_PLANE_CHECKOUT=str(run_root / "plane")))


def test_run_root_writable_by_others_is_rejected(private_dir, token_file):
    run_root = private_dir / "runs"
    run_root.mkdir()
    run_root.chmod(0o777)

    with pytest.raises(ConfigError, match="private"):
        load_config(env_for(private_dir, token_file))


def test_relative_paths_are_rejected(private_dir, token_file):
    with pytest.raises(ConfigError, match="absolute"):
        load_config(env_for(private_dir, token_file, PLANE_AGENT_WORKER_RUN_ROOT="runs"))


def test_missing_origin_is_rejected(private_dir, token_file):
    env = env_for(private_dir, token_file)
    del env["PLANE_AGENT_WORKER_API_ORIGIN"]

    with pytest.raises(ConfigError, match="PLANE_AGENT_WORKER_API_ORIGIN"):
        load_config(env)


@pytest.mark.parametrize("value", ["0", "61", "fast"])
def test_poll_interval_out_of_range_is_rejected(private_dir, token_file, value):
    with pytest.raises(ConfigError, match="PLANE_AGENT_WORKER_POLL_SECONDS"):
        load_config(env_for(private_dir, token_file, PLANE_AGENT_WORKER_POLL_SECONDS=value))
