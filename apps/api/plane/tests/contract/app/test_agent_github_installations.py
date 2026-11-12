# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.bgtasks.agent_git_catalog_task import refresh_catalog
from plane.db.models import AgentGitAccount, AgentGitConnection
from plane.tests.agent_git_fakes import json_response
from plane.tests.agent_git_fixtures import (
    GITHUB_ACCESS_TOKEN,
    GITHUB_REFRESH_TOKEN,
    accounts_url,
    connect_github,
    device_authorization_url,
    github_device_code_response,
    github_error_response,
    github_installation,
    github_installation_repositories_path,
    github_installations_response,
    github_repositories_page,
    github_repository,
    repositories_url,
)

CONNECTIONS_URL = "/api/workspaces/{slug}/agent-git/connections/"


def connected_with(session_client, workspace, fake_http, *installations):
    connect_github(session_client, workspace.slug, fake_http, installations=list(installations))
    return AgentGitConnection.objects.get(workspace=workspace, provider="github")


def attach(client, slug, account_id):
    return client.post(accounts_url(slug, account_id=account_id, action="attach"), {}, format="json")


@pytest.mark.contract
class TestInstallationSync:
    @pytest.mark.django_db
    def test_connect_lists_a_new_installation_once_as_candidate(
        self, session_client, workspace, fake_http, github_app_env
    ):
        connected_with(session_client, workspace, fake_http, github_installation(111, "plane-mini"))

        response = session_client.get(accounts_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert [(a["login"], a["state"], a["account_type"]) for a in response.data] == [
            ("plane-mini", "candidate", "Organization")
        ]

    @pytest.mark.django_db
    def test_repeated_sync_creates_no_duplicate_and_keeps_state(
        self, session_client, workspace, fake_http, github_app_env
    ):
        connected_with(session_client, workspace, fake_http, github_installation(111, "plane-mini"))
        fake_http.add(
            "GET",
            "api.github.com/user/installations",
            github_installations_response(github_installation(111, "plane-mini-renamed")),
        )

        first = session_client.post(accounts_url(workspace.slug, action="sync"), {}, format="json")
        second = session_client.post(accounts_url(workspace.slug, action="sync"), {}, format="json")

        assert first.status_code == second.status_code == status.HTTP_200_OK
        accounts = AgentGitAccount.objects.filter(workspace=workspace)
        assert accounts.count() == 1
        assert accounts.get().login == "plane-mini-renamed"
        assert accounts.get().state == "candidate"

    @pytest.mark.django_db
    def test_sync_keeps_an_attached_installation_attached(
        self, session_client, workspace, fake_http, github_app_env, mock_celery
    ):
        connected_with(session_client, workspace, fake_http, github_installation(111, "plane-mini"))
        account = AgentGitAccount.objects.get(workspace=workspace)
        attach(session_client, workspace.slug, account.id)

        session_client.post(accounts_url(workspace.slug, action="sync"), {}, format="json")

        account.refresh_from_db()
        assert account.state == "attached"

    @pytest.mark.django_db
    @pytest.mark.parametrize("outcome", ["cancel", "deny"])
    def test_cancelled_or_denied_organization_flow_leaves_installations_unchanged(
        self, outcome, session_client, workspace, fake_http, github_app_env
    ):
        connected_with(session_client, workspace, fake_http, github_installation(111, "plane-mini"))
        before = list(AgentGitAccount.objects.filter(workspace=workspace).values_list("external_id", "login", "state"))
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response(interval=0))
        fake_http.add("POST", "github.com/login/oauth/access_token", github_error_response("access_denied"))
        started = session_client.post(device_authorization_url(workspace.slug), {"kind": "organization"}, format="json")

        if outcome == "cancel":
            result = session_client.post(
                device_authorization_url(workspace.slug, started.data["id"], "cancel"), {}, format="json"
            )
            assert result.data["status"] == "cancelled"
        else:
            result = session_client.post(
                device_authorization_url(workspace.slug, started.data["id"], "poll"), {}, format="json"
            )
            assert result.data["status"] == "denied"

        after = list(AgentGitAccount.objects.filter(workspace=workspace).values_list("external_id", "login", "state"))
        assert after == before

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "body",
        [["not an object"], {"installations": "not a list"}, {"installations": [{"account": {"login": "no-id"}}]}],
        ids=["list-body", "string-installations", "missing-id"],
    )
    def test_malformed_installations_answer_returns_unexpected_response(
        self, body, session_client, workspace, fake_http, github_app_env
    ):
        connection = connected_with(session_client, workspace, fake_http, github_installation(111, "plane-mini"))
        fake_http.add("GET", "api.github.com/user/installations", json_response(200, body))

        response = session_client.post(accounts_url(workspace.slug, action="sync"), {}, format="json")

        assert response.status_code == status.HTTP_502_BAD_GATEWAY, response.data
        assert response.data["error"] == "github_unexpected_response"
        assert list(AgentGitAccount.objects.filter(connection=connection).values_list("external_id", flat=True)) == [
            "111"
        ]

    @pytest.mark.django_db
    def test_sync_without_connection_returns_provider_disconnected(self, session_client, workspace, fake_http):
        response = session_client.post(accounts_url(workspace.slug, action="sync"), {}, format="json")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["error"] == "provider_disconnected"
        assert response.data["provider"] == "github"

    @pytest.mark.django_db
    def test_connection_exposes_the_app_install_url(self, session_client, workspace, fake_http, github_app_env):
        connected_with(session_client, workspace, fake_http)

        listed = session_client.get(CONNECTIONS_URL.format(slug=workspace.slug))

        github = next(item for item in listed.data if item["provider"] == "github")
        assert github["install_url"] == "https://github.com/apps/plane-agents-test/installations/new"

    @pytest.mark.django_db
    def test_installation_sync_sends_no_token_in_logs(
        self, session_client, workspace, fake_http, github_app_env, agent_caplog
    ):
        connected_with(session_client, workspace, fake_http, github_installation(111, "plane-mini"))
        session_client.post(accounts_url(workspace.slug, action="sync"), {}, format="json")

        for record in agent_caplog.records:
            assert GITHUB_ACCESS_TOKEN not in record.getMessage()
            assert GITHUB_REFRESH_TOKEN not in record.getMessage()


@pytest.mark.contract
class TestInstallationAttach:
    @pytest.mark.django_db
    def test_candidate_installation_adds_no_repository(self, session_client, workspace, fake_http, github_app_env):
        connection = connected_with(session_client, workspace, fake_http, github_installation(111, "plane-mini"))

        refresh_catalog(connection.id)

        assert fake_http.count("GET", github_installation_repositories_path()) == 0
        assert session_client.get(repositories_url(workspace.slug)).data["results"] == []

    @pytest.mark.django_db
    def test_attach_enqueues_catalog_with_ids_only_and_lists_repositories(
        self,
        session_client,
        member_client,
        workspace,
        fake_http,
        github_app_env,
        mock_celery,
        django_capture_on_commit_callbacks,
    ):
        connection = connected_with(session_client, workspace, fake_http, github_installation(111, "plane-mini"))
        account = AgentGitAccount.objects.get(workspace=workspace)
        fake_http.add(
            "GET",
            github_installation_repositories_path(),
            github_repositories_page(
                github_repository(501, "plane-mini/api"), github_repository(502, "plane-mini/web", private=False)
            ),
        )

        with django_capture_on_commit_callbacks(execute=True):
            response = attach(session_client, workspace.slug, account.id)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["state"] == "attached"
        assert response.data["attached_by"] is not None
        delay_args = [call.args for call in mock_celery.call_args_list]
        assert (str(connection.id),) in delay_args
        for args in delay_args:
            for value in args:
                assert GITHUB_ACCESS_TOKEN not in str(value)
        refresh_catalog(connection.id)
        listed = member_client.get(repositories_url(workspace.slug))
        assert listed.status_code == status.HTTP_200_OK
        rows = {row["full_name"]: row for row in listed.data["results"]}
        assert set(rows) == {"plane-mini/api", "plane-mini/web"}
        assert rows["plane-mini/api"]["provider"] == "github"
        assert rows["plane-mini/api"]["private"] is True
        assert rows["plane-mini/web"]["private"] is False
        assert rows["plane-mini/api"]["account_login"] == "plane-mini"
        assert rows["plane-mini/api"]["default_branch"] == "main"
        assert "clone_url" not in rows["plane-mini/api"]

    @pytest.mark.django_db
    def test_member_cannot_attach_or_sync(self, session_client, member_client, workspace, fake_http, github_app_env):
        connected_with(session_client, workspace, fake_http, github_installation(111, "plane-mini"))
        account = AgentGitAccount.objects.get(workspace=workspace)

        assert attach(member_client, workspace.slug, account.id).status_code == status.HTTP_403_FORBIDDEN
        sync = member_client.post(accounts_url(workspace.slug, action="sync"), {}, format="json")
        assert sync.status_code == status.HTTP_403_FORBIDDEN
        account.refresh_from_db()
        assert account.state == "candidate"

    @pytest.mark.django_db
    def test_member_reads_accounts_and_repositories_guest_cannot(
        self, session_client, member_client, guest_client, workspace, fake_http, github_app_env
    ):
        connected_with(session_client, workspace, fake_http, github_installation(111, "plane-mini"))

        assert member_client.get(accounts_url(workspace.slug)).status_code == status.HTTP_200_OK
        assert member_client.get(repositories_url(workspace.slug)).status_code == status.HTTP_200_OK
        assert guest_client.get(accounts_url(workspace.slug)).status_code == status.HTTP_403_FORBIDDEN
        assert guest_client.get(repositories_url(workspace.slug)).status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_attach_of_another_workspace_account_returns_404(
        self, session_client, workspace, create_user, fake_http, github_app_env
    ):
        from plane.db.models import Workspace, WorkspaceMember

        other = Workspace.objects.create(name="Other", slug="other-ws", owner=create_user)
        WorkspaceMember.objects.create(workspace=other, member=create_user, role=20)
        connect_github(session_client, other.slug, fake_http, installations=[github_installation(222, "other-org")])
        foreign = AgentGitAccount.objects.get(workspace=other)

        assert attach(session_client, workspace.slug, foreign.id).status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_unknown_provider_in_path_returns_404(self, session_client, workspace):
        assert session_client.get(accounts_url(workspace.slug, provider="bitbucket")).status_code == 404


@pytest.mark.contract
class TestInstallationRemoval:
    def _two_attached(self, session_client, workspace, fake_http):
        connection = connected_with(
            session_client,
            workspace,
            fake_http,
            github_installation(111, "plane-mini"),
            github_installation(222, "kevinle128", account_type="User"),
        )
        AgentGitAccount.objects.filter(connection=connection).update(state="attached")
        return connection

    @pytest.mark.django_db
    def test_remove_detaches_only_the_target_installation(self, session_client, workspace, fake_http, github_app_env):
        connection = self._two_attached(session_client, workspace, fake_http)
        target = AgentGitAccount.objects.get(connection=connection, external_id="111")
        fake_http.add(
            "GET",
            github_installation_repositories_path(111),
            github_repositories_page(github_repository(501, "plane-mini/api")),
        )
        fake_http.add(
            "GET",
            github_installation_repositories_path(222),
            github_repositories_page(github_repository(601, "kevinle128/notes")),
        )
        refresh_catalog(connection.id)

        response = session_client.delete(accounts_url(workspace.slug, account_id=target.id))

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["state"] == "detached"
        assert response.data["removed_at"]
        assert response.data["settings_url"] == "https://github.com/organizations/plane-mini/settings/installations/111"
        states = dict(AgentGitAccount.objects.filter(connection=connection).values_list("external_id", "state"))
        assert states == {"111": "detached", "222": "attached"}
        listed = session_client.get(repositories_url(workspace.slug))
        assert [row["full_name"] for row in listed.data["results"]] == ["kevinle128/notes"]
        assert fake_http.count("DELETE") == 0

    @pytest.mark.django_db
    def test_user_installation_points_to_personal_settings(self, session_client, workspace, fake_http, github_app_env):
        connection = self._two_attached(session_client, workspace, fake_http)
        target = AgentGitAccount.objects.get(connection=connection, external_id="222")

        response = session_client.delete(accounts_url(workspace.slug, account_id=target.id))

        assert response.data["settings_url"] == "https://github.com/settings/installations/222"

    @pytest.mark.django_db
    def test_detached_installation_stays_detached_after_sync(
        self, session_client, workspace, fake_http, github_app_env
    ):
        connection = self._two_attached(session_client, workspace, fake_http)
        target = AgentGitAccount.objects.get(connection=connection, external_id="111")
        session_client.delete(accounts_url(workspace.slug, account_id=target.id))
        fake_http.add(
            "GET",
            "api.github.com/user/installations",
            github_installations_response(
                github_installation(111, "plane-mini"), github_installation(222, "kevinle128")
            ),
        )

        synced = session_client.post(accounts_url(workspace.slug, action="sync"), {}, format="json")

        assert synced.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.state == "detached"

    @pytest.mark.django_db
    def test_failed_removal_keeps_the_installation_and_returns_an_actionable_error(
        self, session_client, workspace, fake_http, github_app_env, mocker
    ):
        from django.db import DatabaseError

        connection = self._two_attached(session_client, workspace, fake_http)
        target = AgentGitAccount.objects.get(connection=connection, external_id="111")
        mocker.patch.object(AgentGitAccount, "save", side_effect=DatabaseError("forced failure"))

        response = session_client.delete(accounts_url(workspace.slug, account_id=target.id))

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["error"] == "account_remove_failed"
        mocker.stopall()
        target.refresh_from_db()
        assert target.state == "attached"

    @pytest.mark.django_db
    def test_member_cannot_remove(self, session_client, member_client, workspace, fake_http, github_app_env):
        connection = self._two_attached(session_client, workspace, fake_http)
        target = AgentGitAccount.objects.get(connection=connection, external_id="111")

        response = member_client.delete(accounts_url(workspace.slug, account_id=target.id))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        target.refresh_from_db()
        assert target.state == "attached"
