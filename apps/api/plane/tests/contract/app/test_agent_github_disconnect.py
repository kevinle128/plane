# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.agent.git_providers.base import ProviderError
from plane.agent.services import github_connection
from plane.db.models import AgentGitAccount, AgentGitConnection, WorkspaceMember
from plane.tests.agent_git_fakes import json_response
from plane.tests.agent_git_fixtures import (
    GITHUB_ACCESS_TOKEN,
    GITHUB_CLIENT_SECRET,
    accounts_url,
    connect_github,
    expire_connection_token,
    github_installation,
    github_token_response,
    repositories_url,
)

REVOKE_PATH = "api.github.com/applications/Iv1.testclientid/token"
GRANT_PATH = "api.github.com/applications/Iv1.testclientid/grant"


def connection_url(slug, provider="github"):
    return f"/api/workspaces/{slug}/agent-git/{provider}/connection/"


def connected(session_client, workspace, fake_http):
    connect_github(session_client, workspace.slug, fake_http, installations=[github_installation(111, "plane-mini")])
    return AgentGitConnection.objects.get(workspace=workspace, provider="github")


def revoke_calls(fake_http):
    return [call for call in fake_http.calls if call["host_path"] == REVOKE_PATH]


@pytest.mark.contract
class TestGithubDisconnect:
    @pytest.mark.django_db
    def test_disconnect_revokes_only_this_workspace_token_and_clears_it(
        self, session_client, workspace, fake_http, github_app_env
    ):
        connection = connected(session_client, workspace, fake_http)
        fake_http.add("DELETE", REVOKE_PATH, json_response(204))

        response = session_client.delete(connection_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["status"] == "disconnected"
        assert response.data["revoke_in_provider"] is False
        calls = revoke_calls(fake_http)
        assert len(calls) == 1
        assert calls[0]["method"] == "DELETE"
        assert calls[0]["json_body"] == {"access_token": GITHUB_ACCESS_TOKEN}
        assert calls[0]["auth"] == ("Iv1.testclientid", GITHUB_CLIENT_SECRET)
        assert fake_http.count(path=GRANT_PATH) == 0
        connection.refresh_from_db()
        assert connection.status == "disconnected"
        assert connection.access_token == ""
        assert connection.refresh_token == ""
        assert connection.account_login == "octo-admin"
        assert GITHUB_ACCESS_TOKEN not in response.content.decode()

    @pytest.mark.django_db
    def test_disconnected_connection_cannot_list_or_provide_a_token(
        self, session_client, workspace, fake_http, github_app_env
    ):
        connection = connected(session_client, workspace, fake_http)
        fake_http.add("DELETE", REVOKE_PATH, json_response(204))
        session_client.delete(connection_url(workspace.slug))

        assert session_client.get(repositories_url(workspace.slug)).data["results"] == []
        sync = session_client.post(accounts_url(workspace.slug, action="sync"), {}, format="json")
        assert sync.status_code == status.HTTP_409_CONFLICT
        assert sync.data == {"error": "provider_disconnected", "provider": "github"}
        with pytest.raises(ProviderError) as error:
            github_connection.usable_token(connection.id)
        assert (error.value.code, error.value.provider) == ("provider_disconnected", "github")
        assert AgentGitAccount.objects.filter(connection=connection).count() == 1

    @pytest.mark.django_db
    def test_expired_token_is_refreshed_before_revoke(self, session_client, workspace, fake_http, github_app_env):
        connection = connected(session_client, workspace, fake_http)
        expire_connection_token(connection)
        fake_http.add(
            "POST",
            "github.com/login/oauth/access_token",
            github_token_response(access_token="ghu_REFRESHED_FOR_REVOKE", refresh_token="ghr_REFRESHED_FOR_REVOKE"),
        )
        fake_http.add("DELETE", REVOKE_PATH, json_response(204))

        response = session_client.delete(connection_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert revoke_calls(fake_http)[0]["json_body"] == {"access_token": "ghu_REFRESHED_FOR_REVOKE"}

    @pytest.mark.django_db
    @pytest.mark.parametrize("github_status", [404, 422])
    def test_invalid_token_answer_counts_as_revoked(
        self, github_status, session_client, workspace, fake_http, github_app_env
    ):
        connection = connected(session_client, workspace, fake_http)
        fake_http.add("DELETE", REVOKE_PATH, json_response(github_status, {"message": "Not Found"}))

        response = session_client.delete(connection_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        connection.refresh_from_db()
        assert connection.status == "disconnected"
        assert connection.access_token == ""

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "failure",
        [
            json_response(502, {"message": "Bad gateway"}),
            ProviderError("github_url_unreachable", "github", "timeout", 502),
        ],
        ids=["server-error", "network-error"],
    )
    def test_github_failure_keeps_the_connection(self, failure, session_client, workspace, fake_http, github_app_env):
        connection = connected(session_client, workspace, fake_http)
        fake_http.add("DELETE", REVOKE_PATH, failure)

        response = session_client.delete(connection_url(workspace.slug))

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert response.data["error"] == "github_revoke_failed"
        connection.refresh_from_db()
        assert connection.status == "connected"
        assert connection.access_token != ""

    @pytest.mark.django_db
    def test_reconnect_required_after_admin_loss_clears_tokens_without_github_call(
        self, session_client, workspace, create_user, fake_http, github_app_env
    ):
        from plane.tests.agent_git_fixtures import client_for_user, make_workspace_user

        connection = connected(session_client, workspace, fake_http)
        other_admin = client_for_user(make_workspace_user(workspace, 20))
        WorkspaceMember.objects.filter(workspace=workspace, member=create_user).update(role=15)
        with pytest.raises(ProviderError):
            github_connection.usable_token(connection.id)
        calls_before = len(fake_http.calls)

        response = other_admin.delete(connection_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["revoke_in_provider"] is True
        assert len(fake_http.calls) == calls_before
        connection.refresh_from_db()
        assert connection.status == "disconnected"
        assert connection.access_token == ""
        assert connection.refresh_token == ""

    @pytest.mark.django_db
    def test_gitlab_connection_in_the_same_workspace_is_unchanged(
        self, session_client, workspace, fake_http, github_app_env
    ):
        connected(session_client, workspace, fake_http)
        gitlab = AgentGitConnection.objects.create(
            workspace=workspace,
            provider="gitlab",
            base_url="https://git.example.com",
            host="git.example.com",
            status="connected",
            access_token="gitlab-ciphertext",
        )
        fake_http.add("DELETE", REVOKE_PATH, json_response(204))

        session_client.delete(connection_url(workspace.slug))

        gitlab.refresh_from_db()
        assert gitlab.status == "connected"
        assert gitlab.access_token == "gitlab-ciphertext"
        assert all(call["host"] != "git.example.com" for call in fake_http.calls)

    @pytest.mark.django_db
    def test_member_cannot_disconnect(self, session_client, member_client, workspace, fake_http, github_app_env):
        connection = connected(session_client, workspace, fake_http)

        response = member_client.delete(connection_url(workspace.slug))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        connection.refresh_from_db()
        assert connection.status == "connected"

    @pytest.mark.django_db
    def test_disconnect_without_connection_returns_404(self, session_client, workspace, fake_http, github_app_env):
        assert session_client.delete(connection_url(workspace.slug)).status_code == status.HTTP_404_NOT_FOUND
