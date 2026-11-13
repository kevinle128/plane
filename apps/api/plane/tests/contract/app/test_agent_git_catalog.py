# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.agent.git_providers.base import ProviderError
from plane.bgtasks import agent_git_catalog_task
from plane.bgtasks.agent_git_catalog_task import refresh_agent_git_catalog, refresh_catalog
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


def gitlab_project(project_id, path, **overrides):
    project = {
        "id": project_id,
        "path_with_namespace": path,
        "namespace": {"full_path": path.rsplit("/", 1)[0]},
        "visibility": "private",
        "default_branch": "main",
        "http_url_to_repo": f"https://git.example.com/{path}.git",
        "web_url": f"https://git.example.com/{path}",
    }
    project.update(overrides)
    return project


@pytest.mark.contract
class TestCatalogUntrustedShapes:
    def _refreshed_once(self, session_client, workspace, fake_http):
        connection = connected_gitlab(session_client, workspace, fake_http)
        fake_http.add("GET", GITLAB_PROJECTS, gitlab_page("group_projects_page1.json"))
        refresh_catalog(connection.id)
        return connection

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "body",
        [
            {"message": "not a list"},
            ["not an object"],
            [{"id": 105, "http_url_to_repo": "https://git.example.com/platform/x.git"}],
            [gitlab_project(None, "platform/no-id")],
        ],
        ids=["object-body", "string-item", "missing-path", "missing-id"],
    )
    def test_malformed_gitlab_page_records_the_error_and_keeps_the_snapshot(
        self, body, session_client, workspace, fake_http, mock_celery
    ):
        connection = self._refreshed_once(session_client, workspace, fake_http)
        fake_http.add("GET", GITLAB_PROJECTS, json_response(200, body, headers={"X-Next-Page": ""}))

        refresh_catalog(connection.id)

        account = AgentGitAccount.objects.get(connection=connection, state="attached")
        assert account.catalog_error == "gitlab_unexpected_response"
        assert names(workspace) == ["platform/api", "platform/tools/cli"]

    @pytest.mark.django_db
    def test_value_longer_than_the_catalog_field_skips_only_that_project(
        self, session_client, workspace, fake_http, mock_celery
    ):
        connection = connected_gitlab(session_client, workspace, fake_http)
        long_path = "platform/" + "x" * 600
        fake_http.add(
            "GET",
            GITLAB_PROJECTS,
            json_response(
                200,
                [gitlab_project(201, "platform/ok"), gitlab_project(202, long_path)],
                headers={"X-Next-Page": ""},
            ),
        )

        refresh_catalog(connection.id)

        assert names(workspace) == ["platform/ok"]
        assert AgentGitAccount.objects.get(connection=connection, state="attached").catalog_error == ""

    @pytest.mark.django_db
    def test_any_failure_of_one_account_is_recorded_and_the_next_account_is_read(
        self, session_client, workspace, fake_http, github_app_env, mocker
    ):
        connection = attached_github(session_client, workspace, fake_http)
        second = AgentGitAccount.objects.create(
            connection=connection,
            workspace=workspace,
            provider="github",
            external_id="222",
            login="beta",
            account_type="Organization",
            state="attached",
        )
        first = AgentGitAccount.objects.get(connection=connection, external_id="111")
        fake_http.add(
            "GET",
            github_installation_repositories_path(222),
            github_repositories_page(github_repository(601, "beta/api")),
        )
        from plane.agent.git_providers.github import GithubClient

        real = GithubClient.list_repositories

        def broken_for_first(client, account, cursor=None, deadline=None):
            if account.pk == first.pk:
                raise RuntimeError("unexpected failure")
            return real(client, account, cursor, deadline=deadline)

        mocker.patch.object(GithubClient, "list_repositories", broken_for_first)

        refresh_catalog(connection.id)

        first.refresh_from_db()
        second.refresh_from_db()
        assert first.catalog_error == "github_unexpected_response"
        assert second.catalog_error == ""
        assert names(workspace) == ["beta/api"]

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "body",
        [
            ["not an object"],
            {"repositories": "not a list"},
            {"repositories": [{"clone_url": "https://github.com/a/b.git"}]},
        ],
        ids=["list-body", "string-repositories", "missing-id"],
    )
    def test_malformed_github_page_records_the_error(self, body, session_client, workspace, fake_http, github_app_env):
        connection = attached_github(session_client, workspace, fake_http)
        fake_http.add("GET", REPOS_PATH, json_response(200, body))

        refresh_catalog(connection.id)

        assert AgentGitAccount.objects.get(connection=connection).catalog_error == "github_unexpected_response"


def second_github_account(connection, workspace):
    return AgentGitAccount.objects.create(
        connection=connection,
        workspace=workspace,
        provider="github",
        external_id="222",
        login="beta",
        account_type="Organization",
        state="attached",
    )


@pytest.mark.contract
class TestCatalogTimeLimits:
    def test_task_has_soft_and_hard_time_limits_above_the_shared_budget(self):
        budget = agent_git_catalog_task.CATALOG_BUDGET_SECONDS
        soft = refresh_agent_git_catalog.soft_time_limit
        hard = refresh_agent_git_catalog.time_limit

        assert soft is not None and hard is not None
        assert budget < soft < hard
        # One account must not hold a worker for the old 200 pages x 30 s.
        assert hard <= 15 * 60

    @pytest.mark.django_db
    def test_all_pages_of_all_accounts_share_one_task_deadline(
        self, session_client, workspace, fake_http, github_app_env
    ):
        import time

        connection = attached_github(session_client, workspace, fake_http)
        second_github_account(connection, workspace)
        fake_http.add(
            "GET",
            REPOS_PATH,
            github_repositories_page(github_repository(501, "plane-mini/api"), next_page=2),
            github_repositories_page(github_repository(502, "plane-mini/web")),
        )
        second_path = github_installation_repositories_path(222)
        fake_http.add("GET", second_path, github_repositories_page(github_repository(601, "beta/api")))

        started = time.monotonic()
        refresh_catalog(connection.id)

        catalog_paths = {REPOS_PATH, second_path}
        catalog_calls = [call for call in fake_http.calls if catalog_paths & {call["path"], call["host_path"]}]
        deadlines = {call["deadline"] for call in catalog_calls}
        assert len(catalog_calls) == 3
        assert len(deadlines) == 1
        (deadline,) = deadlines
        assert deadline is not None
        assert deadline <= started + agent_git_catalog_task.CATALOG_BUDGET_SECONDS + 1

    @pytest.mark.django_db
    def test_soft_time_limit_records_the_timeout_and_stops_the_task(
        self, session_client, workspace, fake_http, github_app_env, mocker
    ):
        from celery.exceptions import SoftTimeLimitExceeded

        from plane.agent.git_providers.github import GithubClient

        connection = attached_github(session_client, workspace, fake_http)
        fake_http.add("GET", REPOS_PATH, github_repositories_page(github_repository(501, "plane-mini/api")))
        refresh_catalog(connection.id)
        second = second_github_account(connection, workspace)
        first = AgentGitAccount.objects.get(connection=connection, external_id="111")
        second_path = github_installation_repositories_path(222)
        fake_http.add("GET", second_path, github_repositories_page(github_repository(601, "beta/api")))
        mocker.patch.object(GithubClient, "list_repositories", side_effect=SoftTimeLimitExceeded())

        refresh_catalog(connection.id)

        assert GithubClient.list_repositories.call_count == 1
        read_account = GithubClient.list_repositories.call_args.args[0]
        errors = dict(AgentGitAccount.objects.filter(pk__in=[first.pk, second.pk]).values_list("pk", "catalog_error"))
        assert errors[read_account.pk] == "github_url_unreachable"
        assert [error for pk, error in errors.items() if pk != read_account.pk] == [""]
        assert names(workspace) == ["plane-mini/api"]
