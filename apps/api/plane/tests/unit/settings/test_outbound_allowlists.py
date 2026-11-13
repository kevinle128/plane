# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Operator allowlists for outbound requests (webhooks and Git providers) parse the same way."""

import importlib
import ipaddress

import pytest

from plane.settings import common


@pytest.fixture
def load_settings(monkeypatch):
    def _load(**env):
        for key in ("WEBHOOK_ALLOWED_IPS", "WEBHOOK_ALLOWED_HOSTS", "AGENT_GIT_ALLOWED_IPS", "AGENT_GIT_ALLOWED_HOSTS"):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return importlib.reload(common)

    yield _load
    monkeypatch.undo()
    importlib.reload(common)


@pytest.mark.unit
class TestWebhookAllowlists:
    def test_ips_keep_cidrs_and_skip_invalid_entries(self, load_settings):
        settings = load_settings(WEBHOOK_ALLOWED_IPS=" 10.0.0.0/8, not-an-ip ,192.168.1.5,,fd00::/8")

        assert settings.WEBHOOK_ALLOWED_IPS == [
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("192.168.1.5/32"),
            ipaddress.ip_network("fd00::/8"),
        ]

    def test_hosts_are_normalized(self, load_settings):
        settings = load_settings(WEBHOOK_ALLOWED_HOSTS="Silo., internal.lan ,, API.Example.com")

        assert settings.WEBHOOK_ALLOWED_HOSTS == ["silo", "internal.lan", "api.example.com"]

    def test_unset_gives_empty_lists(self, load_settings):
        settings = load_settings()

        assert settings.WEBHOOK_ALLOWED_IPS == []
        assert settings.WEBHOOK_ALLOWED_HOSTS == []


@pytest.mark.unit
class TestAgentGitAllowlists:
    def test_agent_git_allowlists_use_the_webhook_parse_rules(self, load_settings):
        settings = load_settings(
            AGENT_GIT_ALLOWED_IPS="10.20.0.0/16, bad-entry, 172.16.0.9",
            AGENT_GIT_ALLOWED_HOSTS="Git.Internal., gitlab.lan",
        )

        assert settings.AGENT_GIT_ALLOWED_IPS == [
            ipaddress.ip_network("10.20.0.0/16"),
            ipaddress.ip_network("172.16.0.9/32"),
        ]
        assert settings.AGENT_GIT_ALLOWED_HOSTS == ["git.internal", "gitlab.lan"]

    def test_agent_git_and_webhook_allowlists_are_independent(self, load_settings):
        settings = load_settings(WEBHOOK_ALLOWED_HOSTS="silo")

        assert settings.AGENT_GIT_ALLOWED_HOSTS == []
        assert settings.AGENT_GIT_ALLOWED_IPS == []
