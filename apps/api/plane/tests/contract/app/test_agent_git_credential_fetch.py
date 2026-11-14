# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.db.models import AgentGitConnection, AgentRun
from plane.tests.agent_git_fixtures import GITLAB_TOKEN
from plane.tests.agent_run_fixtures import (
    RunSetup,
    bind_project,
    claim_run,
    connected_agent,
    create_run,
    make_issue,
    make_project,
    worker_run_url,
)


@pytest.fixture
def gitlab_setup(db, workspace, create_user, mock_celery):
    project = make_project(workspace, create_user, identifier="GLB")
    binding = bind_project(project, create_user, provider="gitlab")
    return RunSetup(workspace, create_user, connected_agent(workspace), project, make_issue(project), binding)


def fetch(worker_client, run_id, generation, purpose="fetch"):
    return worker_client.post(
        worker_run_url(run_id, "git-credential"), {"lease_generation": generation, "purpose": purpose}, format="json"
    )


def clone_report(worker_client, run_id, generation, **body):
    return worker_client.post(worker_run_url(run_id, "clone"), {"lease_generation": generation, **body}, format="json")


@pytest.mark.contract
class TestGitCredentialFetch:
    @pytest.mark.django_db
    def test_leased_gitlab_run_gets_the_token(self, session_client, worker_client, gitlab_setup, agent_caplog):
        run = create_run(session_client, gitlab_setup)
        claimed = claim_run(worker_client)

        response = fetch(worker_client, run.id, claimed["lease_generation"])

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"username": "oauth2", "password": GITLAB_TOKEN}
        assert GITLAB_TOKEN not in agent_caplog.text

    @pytest.mark.django_db
    def test_run_without_a_lease_is_refused(self, session_client, worker_client, gitlab_setup):
        run = create_run(session_client, gitlab_setup)

        response = fetch(worker_client, run.id, 1)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "password" not in response.data

    @pytest.mark.django_db
    def test_old_generation_is_refused(self, session_client, worker_client, gitlab_setup):
        run = create_run(session_client, gitlab_setup)
        claimed = claim_run(worker_client)
        AgentRun.objects.filter(pk=run.pk).update(lease_generation=claimed["lease_generation"] + 1)

        response = fetch(worker_client, run.id, claimed["lease_generation"])

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data == {"error": "lease_superseded"}

    @pytest.mark.django_db
    def test_github_run_with_host_credentials_is_refused(self, session_client, worker_client, run_setup):
        run = create_run(session_client, run_setup)
        claimed = claim_run(worker_client)

        response = fetch(worker_client, run.id, claimed["lease_generation"])

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {"error": "credential_mode_host"}

    @pytest.mark.django_db
    def test_other_purpose_is_refused(self, session_client, worker_client, gitlab_setup):
        run = create_run(session_client, gitlab_setup)
        claimed = claim_run(worker_client)

        response = fetch(worker_client, run.id, claimed["lease_generation"], purpose="push")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" not in response.data

    @pytest.mark.django_db
    def test_disconnected_connection_is_refused(self, session_client, worker_client, gitlab_setup):
        run = create_run(session_client, gitlab_setup)
        claimed = claim_run(worker_client)
        AgentGitConnection.objects.filter(workspace=gitlab_setup.workspace).update(
            status="disconnected", access_token=""
        )

        response = fetch(worker_client, run.id, claimed["lease_generation"])

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data == {"error": "provider_disconnected"}

    @pytest.mark.django_db
    def test_undecryptable_token_sets_reconnect_required(self, session_client, worker_client, gitlab_setup):
        run = create_run(session_client, gitlab_setup)
        claimed = claim_run(worker_client)
        AgentGitConnection.objects.filter(workspace=gitlab_setup.workspace).update(access_token="not-a-fernet-value")

        response = fetch(worker_client, run.id, claimed["lease_generation"])

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data == {"error": "provider_reconnect_required"}
        connection = AgentGitConnection.objects.get(workspace=gitlab_setup.workspace)
        assert (connection.status, connection.last_error) == ("reconnect_required", "token_decrypt_failed")


@pytest.mark.contract
class TestWorkerReachability:
    @pytest.mark.django_db
    def test_tls_failure_is_stored_and_a_later_successful_clone_clears_it(
        self, session_client, worker_client, gitlab_setup
    ):
        first = create_run(session_client, gitlab_setup)
        first_claim = claim_run(worker_client)

        failed = clone_report(
            worker_client,
            first.id,
            first_claim["lease_generation"],
            ok=False,
            error_code="git_tls_failed",
            error_detail="server certificate verification failed",
        )

        assert failed.status_code == status.HTTP_200_OK
        connection = AgentGitConnection.objects.get(workspace=gitlab_setup.workspace)
        assert connection.worker_last_error == "git_tls_failed"
        assert connection.worker_checked_at is not None
        checked_at = connection.worker_checked_at

        second = create_run(session_client, gitlab_setup, text="Try again")
        second_claim = claim_run(worker_client)
        ok = clone_report(
            worker_client, second.id, second_claim["lease_generation"], ok=True, clone_path=f"/runs/{second.id}/clone"
        )

        assert ok.status_code == status.HTTP_200_OK
        connection.refresh_from_db()
        assert connection.worker_last_error == ""
        assert connection.worker_checked_at > checked_at

    @pytest.mark.django_db
    def test_blocked_host_report_is_stored(self, session_client, worker_client, gitlab_setup):
        run = create_run(session_client, gitlab_setup)
        claimed = claim_run(worker_client)

        response = clone_report(
            worker_client,
            run.id,
            claimed["lease_generation"],
            ok=False,
            error_code="git_host_blocked",
            error_detail="git.test resolves to a private address",
        )

        assert response.status_code == status.HTTP_200_OK
        connection = AgentGitConnection.objects.get(workspace=gitlab_setup.workspace)
        assert connection.worker_last_error == "git_host_blocked"
