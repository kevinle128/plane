# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.agent.git_providers.base import ProviderError
from plane.agent.services import gitlab_connection
from plane.agent.services.git_connection import binding_availability
from plane.bgtasks.agent_git_catalog_task import refresh_catalog
from plane.db.models import AgentGitAccount, AgentGitConnection, AgentGitRepository, ProjectRepositoryBinding
from plane.tests.agent_git_fakes import json_response
from plane.tests.agent_git_fixtures import (
    GITLAB_TOKEN,
    accounts_url,
    add_gitlab_connect_routes,
    gitlab_connect_payload,
    gitlab_connection_url,
    gitlab_fixture,
    make_catalog,
    project_payload,
    projects_url,
    repositories_url,
)

PROJECTS_PATH = "git.example.com/api/v4/groups/19/projects"


def connected(session_client, workspace, fake_http):
    add_gitlab_connect_routes(fake_http)
    response = session_client.post(gitlab_connection_url(workspace.slug), gitlab_connect_payload(), format="json")
    assert response.status_code == 201, response.data
    return AgentGitConnection.objects.get(workspace=workspace, provider="gitlab")


def bound_project(session_client, workspace, connection, name="Api", identifier="API"):
    account = AgentGitAccount.objects.get(connection=connection, state="attached")
    row = AgentGitRepository.objects.create(
        account=account,
        workspace=workspace,
        provider="gitlab",
        external_id="101",
        full_name="platform/api",
        owner_login="platform",
        default_branch="main",
        clone_url=f"{connection.base_url}/platform/api.git",
    )
    response = session_client.post(
        projects_url(workspace.slug), project_payload(name, identifier, {"repository_id": str(row.id)}), format="json"
    )
    assert response.status_code == 201, response.data
    return ProjectRepositoryBinding.objects.get(project_id=response.data["id"])


@pytest.mark.contract
class TestGitlabDisconnect:
    @pytest.mark.django_db
    def test_disconnect_clears_the_token_without_any_gitlab_call(
        self, session_client, workspace, fake_http, mock_celery
    ):
        connection = connected(session_client, workspace, fake_http)
        binding = bound_project(session_client, workspace, connection)
        calls_before = len(fake_http.calls)

        response = session_client.delete(gitlab_connection_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK, response.data
        assert len(fake_http.calls) == calls_before
        assert response.data["status"] == "disconnected"
        assert response.data["revoke_in_provider"] is True
        assert response.data["revoke_url"] == "https://git.example.com/groups/platform/-/settings/access_tokens"
        assert GITLAB_TOKEN not in response.content.decode()
        connection.refresh_from_db()
        assert (connection.status, connection.access_token) == ("disconnected", "")
        binding.refresh_from_db()
        assert binding_availability(binding) == {"available": False, "reason": "provider_disconnected"}

    @pytest.mark.django_db
    def test_disconnected_gitlab_cannot_list_or_provide_a_token_and_github_is_unchanged(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        github, _, _ = make_catalog(workspace, create_user, repositories=[(501, "plane-mini/api")])
        connection = connected(session_client, workspace, fake_http)
        session_client.delete(gitlab_connection_url(workspace.slug))
        calls_before = len(fake_http.calls)

        refresh_catalog(connection.id)

        assert len(fake_http.calls) == calls_before
        with pytest.raises(ProviderError) as raised:
            gitlab_connection.usable_token(connection.id)
        assert (raised.value.code, raised.value.provider) == ("provider_disconnected", "gitlab")
        listed = session_client.get(repositories_url(workspace.slug))
        assert {row["provider"] for row in listed.data["results"]} == {"github"}
        github.refresh_from_db()
        assert github.status == "connected"

    @pytest.mark.django_db
    def test_reconnect_with_another_base_url_keeps_old_bindings_unavailable(
        self, session_client, workspace, fake_http, mock_celery
    ):
        connection = connected(session_client, workspace, fake_http)
        old_binding = bound_project(session_client, workspace, connection)
        session_client.delete(gitlab_connection_url(workspace.slug))
        fake_http.routes.clear()
        new_host = "gitlab.new.example"
        for path, body in (
            ("personal_access_tokens/self", gitlab_fixture("token_self_active.json")),
            ("version", gitlab_fixture("version.json")),
            ("user", gitlab_fixture("user_bot.json")),
            ("groups/platform", gitlab_fixture("group.json")),
            ("groups/19/members/all/77", gitlab_fixture("member_developer.json")),
        ):
            fake_http.add("GET", f"{new_host}/api/v4/{path}", json_response(200, body))

        response = session_client.post(
            gitlab_connection_url(workspace.slug),
            gitlab_connect_payload(base_url=f"https://{new_host}"),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        connection.refresh_from_db()
        assert connection.host == new_host
        old_binding.refresh_from_db()
        assert binding_availability(old_binding) == {"available": False, "reason": "repository_unavailable"}
        AgentGitRepository.objects.all().delete()
        new_binding = bound_project(session_client, workspace, connection, name="New", identifier="NEW")
        assert new_binding.host == new_host
        assert binding_availability(new_binding)["available"] is True

    @pytest.mark.django_db
    def test_after_reconnect_a_403_keeps_the_connection_and_a_401_needs_reconnect(
        self, session_client, workspace, fake_http, mock_celery
    ):
        connection = connected(session_client, workspace, fake_http)
        session_client.delete(gitlab_connection_url(workspace.slug))
        add_gitlab_connect_routes(fake_http)
        session_client.post(gitlab_connection_url(workspace.slug), gitlab_connect_payload(), format="json")

        fake_http.add("GET", PROJECTS_PATH, json_response(403, {"message": "403 Forbidden"}))
        refresh_catalog(connection.id)
        connection.refresh_from_db()
        assert connection.status == "connected"
        assert AgentGitAccount.objects.get(connection=connection, state="attached").catalog_error == (
            "gitlab_unexpected_response"
        )

        fake_http.add("GET", PROJECTS_PATH, json_response(401, {"message": "401 Unauthorized"}))
        refresh_catalog(connection.id)
        connection.refresh_from_db()
        assert (connection.status, connection.last_error) == ("reconnect_required", "gitlab_token_invalid")

    @pytest.mark.django_db
    def test_gitlab_group_cannot_be_removed_on_its_own(self, session_client, workspace, fake_http, mock_celery):
        connection = connected(session_client, workspace, fake_http)
        group = AgentGitAccount.objects.get(connection=connection)

        response = session_client.delete(accounts_url(workspace.slug, provider="gitlab", account_id=group.id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "account_remove_not_supported"
        group.refresh_from_db()
        assert group.state == "attached"

    @pytest.mark.django_db
    def test_member_cannot_disconnect(self, session_client, member_client, workspace, fake_http, mock_celery):
        connection = connected(session_client, workspace, fake_http)

        response = member_client.delete(gitlab_connection_url(workspace.slug))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        connection.refresh_from_db()
        assert connection.status == "connected"
