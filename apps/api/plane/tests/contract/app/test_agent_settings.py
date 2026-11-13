# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import threading

import pytest
from django.db import connection as db_connection
from rest_framework import status

from plane.db.models import Agent, AgentConnection, User
from plane.tests.agent_git_fixtures import client_for_user
from plane.tests.agent_settings_fixtures import agents_url

HARNESS_ORDER = ["claude_code", "codex", "grok", "omp"]


@pytest.mark.contract
class TestWorkspaceAgents:
    @pytest.mark.django_db
    def test_first_read_creates_four_agents_with_bot_users(self, session_client, workspace):
        response = session_client.get(agents_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert [agent["harness"] for agent in response.data] == HARNESS_ORDER
        assert [agent["name"] for agent in response.data] == ["Claude Code", "Codex CLI", "Grok CLI", "Omp"]
        assert [agent["handle"] for agent in response.data] == ["Claude", "Codex", "Grok", "Omp"]
        for agent in response.data:
            assert agent["connection"]["state"] == "not_connected"
            assert agent["connection"]["models"] == []
            assert agent["mentionable"] is True
            assert agent["available_for_mentions"] is False
        agents = Agent.objects.filter(workspace=workspace).select_related("bot_user")
        assert agents.count() == 4
        for agent in agents:
            assert agent.bot_user.is_bot is True
            assert agent.bot_user.bot_type == "AGENT"
            assert agent.bot_user.display_name == agent.name
            assert not agent.bot_user.has_usable_password()
            assert not workspace.workspace_member.filter(member=agent.bot_user).exists()
        assert AgentConnection.objects.filter(agent__workspace=workspace).count() == 4

    @pytest.mark.django_db
    def test_second_read_creates_nothing(self, session_client, workspace):
        session_client.get(agents_url(workspace.slug))
        users_before = User.objects.count()

        response = session_client.get(agents_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert Agent.objects.filter(workspace=workspace).count() == 4
        assert User.objects.count() == users_before

    @pytest.mark.django_db
    def test_member_reads_agents(self, member_client, workspace):
        response = member_client.get(agents_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 4

    @pytest.mark.django_db
    def test_guest_cannot_read_agents(self, guest_client, workspace):
        assert guest_client.get(agents_url(workspace.slug)).status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_detail_returns_one_harness(self, session_client, workspace):
        response = session_client.get(agents_url(workspace.slug, "claude_code"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["harness"] == "claude_code"
        assert response.data["connection"]["state"] == "not_connected"

    @pytest.mark.django_db
    def test_unknown_harness_returns_404(self, session_client, workspace):
        assert session_client.get(agents_url(workspace.slug, "aider")).status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_bot_users_do_not_leak_into_the_payload(self, session_client, workspace):
        response = session_client.get(agents_url(workspace.slug, "claude_code"))

        assert "bot_user" not in response.data
        assert "email" not in str(response.data)


@pytest.mark.contract
class TestConcurrentFirstRead:
    @pytest.mark.django_db(transaction=True)
    def test_two_concurrent_first_reads_create_one_agent_per_harness(self, workspace, create_user):
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def read():
            try:
                client = client_for_user(create_user)
                barrier.wait(timeout=30)
                response = client.get(agents_url(workspace.slug))
                results.append((response.status_code, [agent["id"] for agent in response.data]))
            except Exception as exc:  # surfaced through the errors list
                errors.append(exc)
            finally:
                db_connection.close()

        threads = [threading.Thread(target=read) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
            assert not thread.is_alive()

        assert not errors, errors
        assert [code for code, _ in results] == [200, 200]
        assert results[0][1] == results[1][1]
        assert Agent.objects.filter(workspace=workspace).count() == 4
        assert AgentConnection.objects.filter(agent__workspace=workspace).count() == 4
        assert User.objects.filter(is_bot=True, bot_type="AGENT").count() == 4
