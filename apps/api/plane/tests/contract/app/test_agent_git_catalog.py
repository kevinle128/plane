# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.agent.git_providers.base import ProviderError
from plane.bgtasks.agent_git_catalog_task import refresh_catalog
from plane.db.models import AgentGitAccount, AgentGitConnection, AgentGitRepository
from plane.tests.agent_git_fakes import json_response
from plane.tests.agent_git_fixtures import (
    connect_github,
    github_installation,
    github_installation_repositories_path,
    github_repositories_page,
    github_repository,
    repositories_url,
)

REPOS_PATH = github_installation_repositories_path()


def attached_github(session_client, workspace, fake_http):
    connect_github(session_client, workspace.slug, fake_http, installations=[github_installation(111, "plane-mini")])
    connection = AgentGitConnection.objects.get(workspace=workspace, provider="github")
    AgentGitAccount.objects.filter(connection=connection).update(state="attached")
    return connection


def names(workspace):
    return sorted(AgentGitRepository.objects.filter(workspace=workspace).values_list("full_name", flat=True))


@pytest.mark.contract
class TestGithubCatalogRefresh:
    @pytest.mark.django_db
    def test_two_pages_give_one_snapshot(self, session_client, workspace, fake_http, github_app_env):
        connection = attached_github(session_client, workspace, fake_http)
        fake_http.add(
            "GET",
            REPOS_PATH,
            github_repositories_page(github_repository(501, "plane-mini/api"), next_page=2),
            github_repositories_page(github_repository(502, "plane-mini/web")),
        )

        refresh_catalog(connection.id)

        assert names(workspace) == ["plane-mini/api", "plane-mini/web"]
        assert fake_http.count("GET", REPOS_PATH) == 2

    @pytest.mark.django_db
    def test_failure_on_a_later_page_keeps_the_previous_snapshot(
        self, session_client, workspace, fake_http, github_app_env
    ):
        connection = attached_github(session_client, workspace, fake_http)
        fake_http.add("GET", REPOS_PATH, github_repositories_page(github_repository(501, "plane-mini/api")))
        refresh_catalog(connection.id)
        ids_before = list(AgentGitRepository.objects.filter(workspace=workspace).values_list("id", flat=True))
        fake_http.add(
            "GET",
            REPOS_PATH,
            github_repositories_page(github_repository(503, "plane-mini/new"), next_page=2),
            ProviderError("github_url_unreachable", "github", "timeout", http_status=502),
        )

        refresh_catalog(connection.id)

        assert names(workspace) == ["plane-mini/api"]
        assert list(AgentGitRepository.objects.filter(workspace=workspace).values_list("id", flat=True)) == ids_before
        account = AgentGitAccount.objects.get(workspace=workspace)
        assert account.catalog_error == "github_url_unreachable"

    @pytest.mark.django_db
    def test_full_refresh_removes_repositories_no_longer_granted_and_keeps_row_ids(
        self, session_client, workspace, fake_http, github_app_env
    ):
        connection = attached_github(session_client, workspace, fake_http)
        fake_http.add(
            "GET",
            REPOS_PATH,
            github_repositories_page(
                github_repository(501, "plane-mini/api"), github_repository(502, "plane-mini/web")
            ),
        )
        refresh_catalog(connection.id)
        api_row_id = AgentGitRepository.objects.get(full_name="plane-mini/api").id
        fake_http.add(
            "GET",
            REPOS_PATH,
            github_repositories_page(github_repository(501, "plane-mini/api", default_branch="trunk")),
        )

        refresh_catalog(connection.id)

        row = AgentGitRepository.objects.get(full_name="plane-mini/api")
        assert names(workspace) == ["plane-mini/api"]
        assert row.id == api_row_id
        assert row.default_branch == "trunk"

    @pytest.mark.django_db
    def test_github_401_sets_reconnect_required_and_keeps_snapshot(
        self, session_client, workspace, fake_http, github_app_env
    ):
        connection = attached_github(session_client, workspace, fake_http)
        fake_http.add("GET", REPOS_PATH, json_response(401, {"message": "Bad credentials"}))

        refresh_catalog(connection.id)

        connection.refresh_from_db()
        assert connection.status == "reconnect_required"
        assert connection.last_error == "github_token_invalid"

    @pytest.mark.django_db
    def test_disconnected_connection_makes_no_provider_call(self, session_client, workspace, fake_http, github_app_env):
        connection = attached_github(session_client, workspace, fake_http)
        AgentGitConnection.objects.filter(pk=connection.pk).update(status="disconnected")
        calls_before = len(fake_http.calls)

        refresh_catalog(connection.id)

        assert len(fake_http.calls) == calls_before

    @pytest.mark.django_db
    def test_repository_list_filters_by_search_and_owner(self, session_client, workspace, fake_http, github_app_env):
        connection = attached_github(session_client, workspace, fake_http)
        fake_http.add(
            "GET",
            REPOS_PATH,
            github_repositories_page(
                github_repository(501, "plane-mini/api"), github_repository(502, "plane-mini/web")
            ),
        )
        refresh_catalog(connection.id)

        searched = session_client.get(repositories_url(workspace.slug), {"search": "WEB"})
        by_owner = session_client.get(repositories_url(workspace.slug), {"owner": "someone-else"})
        by_provider = session_client.get(repositories_url(workspace.slug), {"provider": "gitlab"})

        assert [row["full_name"] for row in searched.data["results"]] == ["plane-mini/web"]
        assert by_owner.data["results"] == []
        assert by_provider.data["results"] == []

    @pytest.mark.django_db
    def test_repository_list_hides_rows_of_a_disconnected_connection(
        self, session_client, workspace, fake_http, github_app_env
    ):
        connection = attached_github(session_client, workspace, fake_http)
        fake_http.add("GET", REPOS_PATH, github_repositories_page(github_repository(501, "plane-mini/api")))
        refresh_catalog(connection.id)
        AgentGitConnection.objects.filter(pk=connection.pk).update(status="disconnected")

        assert session_client.get(repositories_url(workspace.slug)).data["results"] == []


GITLAB_PROJECTS = "git.example.com/api/v4/groups/19/projects"


def connected_gitlab(session_client, workspace, fake_http):
    from plane.tests.agent_git_fixtures import add_gitlab_connect_routes, gitlab_connect_payload, gitlab_connection_url

    add_gitlab_connect_routes(fake_http)
    response = session_client.post(gitlab_connection_url(workspace.slug), gitlab_connect_payload(), format="json")
    assert response.status_code == 201, response.data
    return AgentGitConnection.objects.get(workspace=workspace, provider="gitlab")


def gitlab_page(name, next_page=""):
    from plane.tests.agent_git_fixtures import gitlab_fixture

    return json_response(200, gitlab_fixture(name), headers={"X-Next-Page": next_page})


@pytest.mark.contract
class TestGitlabCatalogRefresh:
    @pytest.mark.django_db
    def test_connect_enqueues_the_catalog_with_ids_only(
        self, session_client, workspace, fake_http, mock_celery, django_capture_on_commit_callbacks
    ):
        from plane.tests.agent_git_fixtures import GITLAB_TOKEN

        with django_capture_on_commit_callbacks(execute=True):
            connection = connected_gitlab(session_client, workspace, fake_http)

        assert (str(connection.id),) in [call.args for call in mock_celery.call_args_list]
        for call in mock_celery.call_args_list:
            assert GITLAB_TOKEN not in repr(call)

    @pytest.mark.django_db
    def test_two_pages_give_one_snapshot_with_subgroup_projects(
        self, session_client, workspace, fake_http, mock_celery
    ):
        connection = connected_gitlab(session_client, workspace, fake_http)
        fake_http.add(
            "GET",
            GITLAB_PROJECTS,
            gitlab_page("group_projects_page1.json", next_page="2"),
            gitlab_page("group_projects_page2.json"),
        )

        refresh_catalog(connection.id)

        rows = {row.full_name: row for row in AgentGitRepository.objects.filter(workspace=workspace, provider="gitlab")}
        assert sorted(rows) == ["platform/api", "platform/docs", "platform/tools/cli"]
        assert rows["platform/tools/cli"].owner_login == "platform/tools"
        assert rows["platform/tools/cli"].private is True
        assert rows["platform/docs"].private is False
        assert rows["platform/docs"].default_branch == "trunk"
        assert rows["platform/api"].clone_url == "https://git.example.com/platform/api.git"
        calls = [call for call in fake_http.calls if call["host_path"] == GITLAB_PROJECTS]
        assert [call["params"]["page"] for call in calls] == [1, 2]
        for call in calls:
            assert call["params"]["include_subgroups"] == "true"
            assert call["params"]["with_shared"] == "false"
            assert call["params"]["archived"] == "false"
            assert call["params"]["per_page"] == 100

    @pytest.mark.django_db
    def test_project_on_another_host_is_not_listed(
        self, session_client, workspace, fake_http, mock_celery, agent_caplog
    ):
        connection = connected_gitlab(session_client, workspace, fake_http)
        fake_http.add("GET", GITLAB_PROJECTS, gitlab_page("group_projects_page2.json"))

        refresh_catalog(connection.id)

        assert names(workspace) == ["platform/docs"]
        assert any("104" in record.getMessage() for record in agent_caplog.records)

    @pytest.mark.django_db
    def test_failure_on_page_two_keeps_the_previous_snapshot(self, session_client, workspace, fake_http, mock_celery):
        connection = connected_gitlab(session_client, workspace, fake_http)
        fake_http.add("GET", GITLAB_PROJECTS, gitlab_page("group_projects_page1.json"))
        refresh_catalog(connection.id)
        fake_http.add(
            "GET",
            GITLAB_PROJECTS,
            gitlab_page("group_projects_page2.json", next_page="2"),
            ProviderError("gitlab_url_unreachable", "gitlab", "timeout", http_status=502),
        )

        refresh_catalog(connection.id)

        assert names(workspace) == ["platform/api", "platform/tools/cli"]

    @pytest.mark.django_db
    def test_member_reads_the_gitlab_catalog_and_guest_cannot(
        self, session_client, member_client, guest_client, workspace, fake_http, mock_celery
    ):
        connection = connected_gitlab(session_client, workspace, fake_http)
        fake_http.add("GET", GITLAB_PROJECTS, gitlab_page("group_projects_page1.json"))
        refresh_catalog(connection.id)

        listed = member_client.get(repositories_url(workspace.slug), {"provider": "gitlab"})

        assert listed.status_code == 200
        row = next(item for item in listed.data["results"] if item["full_name"] == "platform/api")
        assert (row["provider"], row["host"], row["account_login"], row["account_type"]) == (
            "gitlab",
            "git.example.com",
            "platform",
            "Group",
        )
        assert guest_client.get(repositories_url(workspace.slug)).status_code == 403

    @pytest.mark.django_db
    def test_expired_token_sets_reconnect_required_without_a_call(
        self, session_client, workspace, fake_http, mock_celery
    ):
        from datetime import timedelta

        from django.utils import timezone

        connection = connected_gitlab(session_client, workspace, fake_http)
        AgentGitConnection.objects.filter(pk=connection.pk).update(token_expires_at=timezone.now() - timedelta(days=1))
        calls_before = len(fake_http.calls)

        refresh_catalog(connection.id)

        connection.refresh_from_db()
        assert (connection.status, connection.last_error) == ("reconnect_required", "gitlab_token_invalid")
        assert len(fake_http.calls) == calls_before
