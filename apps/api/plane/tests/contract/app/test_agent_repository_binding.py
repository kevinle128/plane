# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import threading

import pytest
from django.db import connection as db_connection
from rest_framework import status

from plane.agent.services.git_connection import binding_availability
from plane.db.models import (
    AgentGitAccount,
    AgentGitConnection,
    Project,
    ProjectRepositoryBinding,
    Workspace,
    WorkspaceMember,
)
from plane.tests.agent_git_fixtures import (
    client_for_user,
    make_catalog,
    project_payload,
    projects_url,
    repositories_url,
)


def catalog(workspace, user, repositories=((501, "plane-mini/api"), (502, "plane-mini/web"))):
    return make_catalog(workspace, user, repositories=list(repositories))


@pytest.mark.contract
class TestBindOnCreate:
    @pytest.mark.django_db
    def test_bind_copies_the_catalog_row_and_defaults_base_ref(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        _, _, rows = catalog(workspace, create_user)
        api = rows[0]
        payload = project_payload(
            "Agents",
            "AGT",
            {
                "repository_id": str(api.id),
                "clone_url": "https://evil.example/attacker.git",
                "full_name": "attacker/repo",
                "provider": "gitlab",
                "host": "evil.example",
            },
        )

        response = session_client.post(projects_url(workspace.slug), payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        binding = ProjectRepositoryBinding.objects.get(project_id=response.data["id"])
        assert (binding.provider, binding.host, binding.external_repository_id) == ("github", "github.com", "501")
        assert binding.full_name == "plane-mini/api"
        assert binding.clone_url == "https://github.com/plane-mini/api.git"
        assert binding.web_url == "https://github.com/plane-mini/api"
        assert binding.default_branch == "main"
        assert binding.base_ref == "main"
        assert binding.account_id == api.account_id
        assert response.data["repository"]["full_name"] == "plane-mini/api"
        assert response.data["repository"]["provider"] == "github"
        assert response.data["repository"]["base_ref"] == "main"
        assert response.data["repository"]["available"] is True
        assert ProjectRepositoryBinding.objects.filter(workspace=workspace).count() == 1

    @pytest.mark.django_db
    def test_explicit_base_ref_is_stored(self, session_client, workspace, create_user, fake_http, mock_celery):
        _, _, rows = catalog(workspace, create_user)
        payload = project_payload("Agents", "AGT", {"repository_id": str(rows[0].id), "base_ref": "release/2.0"})

        response = session_client.post(projects_url(workspace.slug), payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert ProjectRepositoryBinding.objects.get(project_id=response.data["id"]).base_ref == "release/2.0"

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "base_ref",
        [
            "-upload-pack=evil",
            "feature..main",
            "main@{1}",
            "has space",
            "ctrl\x07char",
            "x" * 256,
            "a/.hidden",
            "end.lock",
        ],
    )
    def test_invalid_base_ref_returns_400_and_creates_nothing(
        self, base_ref, session_client, workspace, create_user, fake_http, mock_celery
    ):
        _, _, rows = catalog(workspace, create_user)
        payload = project_payload("Agents", "AGT", {"repository_id": str(rows[0].id), "base_ref": base_ref})

        response = session_client.post(projects_url(workspace.slug), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "invalid_base_ref"
        assert not Project.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    def test_duplicate_bind_returns_409(self, session_client, workspace, create_user, fake_http, mock_celery):
        _, _, rows = catalog(workspace, create_user)
        first = session_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        second = session_client.post(
            projects_url(workspace.slug),
            project_payload("Two", "TWO", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        assert first.status_code == status.HTTP_201_CREATED
        assert second.status_code == status.HTTP_409_CONFLICT
        assert second.data["error"] == "repository_already_bound"
        assert not Project.objects.filter(workspace=workspace, name="Two").exists()

    @pytest.mark.django_db
    def test_repository_of_a_detached_account_returns_409(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        _, account, rows = catalog(workspace, create_user)
        AgentGitAccount.objects.filter(pk=account.pk).update(state="detached")

        response = session_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["error"] == "repository_unavailable"
        assert not Project.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    def test_disconnected_provider_rejects_the_bind(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        connection, _, rows = catalog(workspace, create_user)
        AgentGitConnection.objects.filter(pk=connection.pk).update(status="disconnected")

        response = session_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data == {"error": "provider_disconnected", "provider": "github"}
        assert not Project.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    def test_catalog_row_of_another_workspace_returns_404(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        other = Workspace.objects.create(name="Other", slug="other-ws", owner=create_user)
        WorkspaceMember.objects.create(workspace=other, member=create_user, role=20)
        _, _, rows = catalog(other, create_user)

        response = session_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"] == "repository_not_found"
        assert not Project.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    @pytest.mark.parametrize("repository", ["not-a-dict", {"repository_id": "not-a-uuid"}, {}])
    def test_malformed_repository_returns_400(self, repository, session_client, workspace, fake_http, mock_celery):
        response = session_client.post(
            projects_url(workspace.slug), project_payload("One", "ONE", repository), format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "invalid_repository"

    @pytest.mark.django_db
    def test_bind_makes_no_provider_call_and_creates_no_clone(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        _, _, rows = catalog(workspace, create_user)

        session_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        assert fake_http.calls == []
        task_names = {call.args[0] if call.args else None for call in mock_celery.call_args_list}
        assert all("catalog" not in str(name) for name in task_names)

    @pytest.mark.django_db
    def test_guest_create_stays_forbidden(self, guest_client, workspace, create_user, fake_http, mock_celery):
        _, _, rows = catalog(workspace, create_user)

        response = guest_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not ProjectRepositoryBinding.objects.exists()

    @pytest.mark.django_db
    def test_catalog_marks_a_bound_repository_unavailable(
        self, session_client, member_client, workspace, create_user, fake_http, mock_celery
    ):
        _, _, rows = catalog(workspace, create_user)
        created = session_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        listed = member_client.get(repositories_url(workspace.slug))

        by_name = {row["full_name"]: row for row in listed.data["results"]}
        assert by_name["plane-mini/api"]["available"] is False
        assert by_name["plane-mini/api"]["bound_project"]["id"] == str(created.data["id"])
        assert by_name["plane-mini/api"]["bound_project"]["name"] == "One"
        assert by_name["plane-mini/web"]["available"] is True
        assert by_name["plane-mini/web"]["bound_project"] is None


@pytest.mark.contract
class TestBindingAvailability:
    def _bound(self, session_client, workspace, create_user):
        connection, account, rows = catalog(workspace, create_user)
        response = session_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id)}),
            format="json",
        )
        return connection, account, ProjectRepositoryBinding.objects.get(project_id=response.data["id"])

    @pytest.mark.django_db
    def test_removed_installation_keeps_the_binding_unavailable(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        _, account, binding = self._bound(session_client, workspace, create_user)

        session_client.delete(f"/api/workspaces/{workspace.slug}/agent-git/github/accounts/{account.id}/")

        binding.refresh_from_db()
        assert binding_availability(binding) == {"available": False, "reason": "repository_unavailable"}
        assert binding.full_name == "plane-mini/api"

    @pytest.mark.django_db
    def test_disconnect_keeps_the_binding_unavailable(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        connection, _, binding = self._bound(session_client, workspace, create_user)
        AgentGitConnection.objects.filter(pk=connection.pk).update(status="disconnected", access_token="")

        binding.refresh_from_db()
        assert binding_availability(binding) == {"available": False, "reason": "provider_disconnected"}
        assert ProjectRepositoryBinding.objects.filter(pk=binding.pk).exists()

    @pytest.mark.django_db
    def test_binding_on_another_host_is_unavailable(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        connection, _, binding = self._bound(session_client, workspace, create_user)
        AgentGitConnection.objects.filter(pk=connection.pk).update(host="github.example.com")

        binding.refresh_from_db()
        assert binding_availability(binding) == {"available": False, "reason": "repository_unavailable"}

    @pytest.mark.django_db
    def test_bound_and_attached_binding_is_available(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        _, _, binding = self._bound(session_client, workspace, create_user)

        assert binding_availability(binding) == {"available": True, "reason": ""}


@pytest.mark.contract
class TestConnectingAdminRuleOnBind:
    @pytest.mark.django_db
    def test_bind_after_the_connecting_admin_left_returns_reconnect_required(
        self, workspace, create_user, fake_http, mock_celery
    ):
        connection, _, rows = catalog(workspace, create_user)
        WorkspaceMember.objects.filter(workspace=workspace, member=create_user).update(role=15)
        member = client_for_user(create_user)

        response = member.post(
            projects_url(workspace.slug),
            project_payload("Late", "LATE", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT, response.data
        assert response.data["error"] == "provider_reconnect_required"
        assert not Project.objects.filter(workspace=workspace, name="Late").exists()
        connection.refresh_from_db()
        assert (connection.status, connection.last_error) == ("reconnect_required", "connected_admin_lost")
        assert fake_http.calls == []

    @pytest.mark.django_db
    def test_availability_after_the_connecting_admin_left_is_false(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        _, _, rows = catalog(workspace, create_user)
        created = session_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id)}),
            format="json",
        )
        binding = ProjectRepositoryBinding.objects.get(project_id=created.data["id"])
        WorkspaceMember.objects.filter(workspace=workspace, member=create_user).update(is_active=False)

        assert binding_availability(binding) == {"available": False, "reason": "provider_reconnect_required"}

    @pytest.mark.django_db
    def test_gitlab_bind_does_not_depend_on_the_connecting_member(self, workspace, create_user, fake_http, mock_celery):
        _, _, rows = gitlab_catalog(workspace, create_user)
        WorkspaceMember.objects.filter(workspace=workspace, member=create_user).update(role=15)

        response = client_for_user(create_user).post(
            projects_url(workspace.slug),
            project_payload("Lab", "LAB", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data


@pytest.mark.contract
class TestBindConstraintRace:
    @pytest.mark.django_db
    def test_unique_constraint_conflict_returns_409_and_rolls_back_the_project(
        self, session_client, workspace, create_user, fake_http, mock_celery, mocker
    ):
        """The pre-check misses a binding committed by another request, so the database constraint decides."""
        from plane.agent.services import git_connection
        from plane.db.models import ProjectMember, State

        _, _, rows = catalog(workspace, create_user)
        fields = git_connection.resolve_binding_request(workspace, {"repository_id": str(rows[0].id)})
        other = session_client.post(projects_url(workspace.slug), project_payload("Other", "OTH"), format="json")
        assert other.status_code == status.HTTP_201_CREATED, other.data
        ProjectRepositoryBinding.objects.create(project_id=other.data["id"], **fields)
        mocker.patch("plane.app.views.project.base.git_connection.resolve_binding_request", return_value=dict(fields))
        counts = (Project.objects.count(), ProjectMember.objects.count(), State.objects.count())

        response = session_client.post(
            projects_url(workspace.slug),
            project_payload("Race", "RACE", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT, response.data
        assert response.data == {"error": "repository_already_bound", "provider": "github"}
        assert (Project.objects.count(), ProjectMember.objects.count(), State.objects.count()) == counts
        assert ProjectRepositoryBinding.objects.filter(workspace=workspace).count() == 1


@pytest.mark.contract
class TestConcurrentBind:
    @pytest.mark.django_db(transaction=True)
    def test_concurrent_binds_give_one_201_and_one_409_and_no_orphan_project(
        self, workspace, create_user, fake_http, mock_celery
    ):
        _, _, rows = catalog(workspace, create_user)
        repository = {"repository_id": str(rows[0].id)}
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def create(name, identifier):
            try:
                client = client_for_user(create_user)
                barrier.wait(timeout=30)
                response = client.post(
                    projects_url(workspace.slug), project_payload(name, identifier, repository), format="json"
                )
                results.append(response.status_code)
            except Exception as exc:  # surfaced through the errors list
                errors.append(exc)
            finally:
                db_connection.close()

        threads = [
            threading.Thread(target=create, args=("First", "FST")),
            threading.Thread(target=create, args=("Second", "SND")),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
            assert not thread.is_alive()

        assert not errors, errors
        assert sorted(results) == [201, 409]
        assert Project.objects.filter(workspace=workspace).count() == 1
        project = Project.objects.get(workspace=workspace)
        assert ProjectRepositoryBinding.objects.get().project_id == project.id


def gitlab_catalog(workspace, user, repositories=((101, "platform/api"), (102, "platform/tools/cli"))):
    return make_catalog(workspace, user, provider="gitlab", host="git.example.com", repositories=list(repositories))


@pytest.mark.contract
class TestGitlabBind:
    @pytest.mark.django_db
    def test_bind_copies_the_gitlab_catalog_row(self, session_client, workspace, create_user, fake_http, mock_celery):
        _, _, rows = gitlab_catalog(workspace, create_user)
        payload = project_payload(
            "Tools",
            "TLS",
            {"repository_id": str(rows[1].id), "provider": "github", "clone_url": "https://evil.example/x.git"},
        )

        response = session_client.post(projects_url(workspace.slug), payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        binding = ProjectRepositoryBinding.objects.get(project_id=response.data["id"])
        assert (binding.provider, binding.host, binding.external_repository_id) == ("gitlab", "git.example.com", "102")
        assert binding.full_name == "platform/tools/cli"
        assert binding.clone_url == "https://git.example.com/platform/tools/cli.git"
        assert binding.base_ref == "main"
        assert binding.host == binding.account.connection.host
        assert response.data["repository"]["provider"] == "gitlab"

    @pytest.mark.django_db
    def test_same_numeric_id_on_both_providers_binds_twice(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        _, _, github_rows = catalog(workspace, create_user, repositories=((777, "plane-mini/api"),))
        _, _, gitlab_rows = gitlab_catalog(workspace, create_user, repositories=((777, "platform/api"),))

        first = session_client.post(
            projects_url(workspace.slug),
            project_payload("Hub", "HUB", {"repository_id": str(github_rows[0].id)}),
            format="json",
        )
        second = session_client.post(
            projects_url(workspace.slug),
            project_payload("Lab", "LAB", {"repository_id": str(gitlab_rows[0].id)}),
            format="json",
        )

        assert (first.status_code, second.status_code) == (201, 201)
        assert sorted(ProjectRepositoryBinding.objects.values_list("provider", flat=True)) == ["github", "gitlab"]

    @pytest.mark.django_db
    def test_duplicate_gitlab_bind_returns_409(self, session_client, workspace, create_user, fake_http, mock_celery):
        _, _, rows = gitlab_catalog(workspace, create_user)
        repository = {"repository_id": str(rows[0].id)}
        session_client.post(projects_url(workspace.slug), project_payload("One", "ONE", repository), format="json")

        response = session_client.post(
            projects_url(workspace.slug), project_payload("Two", "TWO", repository), format="json"
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert (response.data["error"], response.data["provider"]) == ("repository_already_bound", "gitlab")

    @pytest.mark.django_db
    @pytest.mark.parametrize("base_ref", ["-x", "a..b", "bad\x01ref"])
    def test_invalid_base_ref_on_gitlab_returns_400(
        self, base_ref, session_client, workspace, create_user, fake_http, mock_celery
    ):
        _, _, rows = gitlab_catalog(workspace, create_user)

        response = session_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id), "base_ref": base_ref}),
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Project.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    def test_gitlab_row_of_another_workspace_returns_404(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        other = Workspace.objects.create(name="Other", slug="other-ws", owner=create_user)
        WorkspaceMember.objects.create(workspace=other, member=create_user, role=20)
        _, _, rows = gitlab_catalog(other, create_user)

        response = session_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_disconnected_gitlab_rejects_the_bind(self, session_client, workspace, create_user, fake_http, mock_celery):
        connection, _, rows = gitlab_catalog(workspace, create_user)
        AgentGitConnection.objects.filter(pk=connection.pk).update(status="disconnected")

        response = session_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        assert response.data == {"error": "provider_disconnected", "provider": "gitlab"}

    @pytest.mark.django_db
    def test_guest_cannot_bind_a_gitlab_repository(self, guest_client, workspace, create_user, fake_http, mock_celery):
        _, _, rows = gitlab_catalog(workspace, create_user)

        response = guest_client.post(
            projects_url(workspace.slug),
            project_payload("One", "ONE", {"repository_id": str(rows[0].id)}),
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db(transaction=True)
    def test_concurrent_gitlab_binds_give_one_201_and_one_409(self, workspace, create_user, fake_http, mock_celery):
        _, _, rows = gitlab_catalog(workspace, create_user)
        repository = {"repository_id": str(rows[0].id)}
        barrier = threading.Barrier(2)
        results = []

        def create(name, identifier):
            try:
                client = client_for_user(create_user)
                barrier.wait(timeout=30)
                results.append(
                    client.post(
                        projects_url(workspace.slug), project_payload(name, identifier, repository), format="json"
                    ).status_code
                )
            finally:
                db_connection.close()

        threads = [threading.Thread(target=create, args=args) for args in (("First", "FST"), ("Second", "SND"))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
            assert not thread.is_alive()

        assert sorted(results) == [201, 409]
        assert Project.objects.filter(workspace=workspace).count() == 1
