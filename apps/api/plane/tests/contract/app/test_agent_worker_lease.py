# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import threading
from datetime import timedelta

import pytest
from django.db import connection as db_connection
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status

from plane.db.models import AgentConnection, AgentRun, AgentRunTurn
from plane.tests.agent_run_fixtures import (
    TEST_CA_BUNDLE,
    RunSetup,
    bind_project,
    claim,
    claim_run,
    connected_agent,
    create_run,
    make_issue,
    make_project,
    worker_run_url,
)
from plane.tests.agent_settings_fixtures import make_worker, worker_client_for


def renew(worker_client, run_id, generation):
    return worker_client.post(worker_run_url(run_id, "renew"), {"lease_generation": generation}, format="json")


@pytest.mark.contract
class TestClaim:
    @pytest.mark.django_db
    def test_no_created_run_gives_null(self, worker_client, run_setup):
        assert claim(worker_client).data == {"run": None}

    @pytest.mark.django_db
    def test_claim_leases_the_run_and_returns_the_clone_spec(
        self, session_client, worker_client, run_setup, agent_worker
    ):
        run = create_run(session_client, run_setup)
        before = timezone.now()

        response = claim(worker_client)

        assert response.status_code == status.HTTP_200_OK
        body = response.data["run"]
        assert body["id"] == str(run.id)
        assert body["short_id"] == run.short_id
        assert body["harness"] == "claude_code"
        assert body["lease_generation"] == 1
        assert body["lease_seconds"] == 300
        assert (body["model"], body["instructions"]) == ("", "")
        assert body["agent"] == {"id": str(run_setup.agent.id), "name": "Claude Code", "handle": "Claude"}
        assert body["workspace"] == {"id": str(run_setup.workspace.id), "slug": run_setup.workspace.slug}
        assert body["issue"] == {"id": str(run_setup.issue.id), "identifier": f"AGT-{run_setup.issue.sequence_id}"}
        assert body["repository"] == {
            "provider": "github",
            "host": "github.com",
            "clone_url": run_setup.binding.clone_url,
            "full_name": run_setup.binding.full_name,
            "external_repository_id": run_setup.binding.external_repository_id,
            "default_branch": "main",
            "base_ref": "main",
            "credential_mode": "host",
            "ca_bundle": None,
        }
        assert body["turn"] == {"index": 0}
        run.refresh_from_db()
        assert run.status == "in_progress"
        assert run.started_at >= before
        assert run.lease_worker_id == agent_worker[0].id
        assert run.lease_expires_at >= before + timedelta(seconds=299)
        turn = AgentRunTurn.objects.get(run=run)
        assert (turn.index, turn.status, turn.lease_generation) == (0, "running", 1)
        assert claim(worker_client).data == {"run": None}

    @pytest.mark.django_db
    def test_gitlab_run_uses_a_plane_token_and_the_ca_bundle(
        self, session_client, worker_client, workspace, create_user, mock_celery
    ):
        project = make_project(workspace, create_user, identifier="GLB")
        binding = bind_project(project, create_user, provider="gitlab")
        agent = connected_agent(workspace)
        issue = make_issue(project)

        create_run(session_client, RunSetup(workspace, create_user, agent, project, issue, binding))

        repository = claim_run(worker_client)["repository"]

        assert repository["provider"] == "gitlab"
        assert repository["credential_mode"] == "plane_token"
        assert repository["ca_bundle"] == TEST_CA_BUNDLE

    @pytest.mark.django_db
    def test_oldest_run_is_claimed_first(self, session_client, worker_client, run_setup):
        first = create_run(session_client, run_setup)
        second = create_run(session_client, run_setup, text="Second question")

        assert claim_run(worker_client)["id"] == str(first.id)
        assert claim_run(worker_client)["id"] == str(second.id)

    @pytest.mark.django_db
    def test_unlisted_harness_is_not_claimed(self, session_client, worker_client, run_setup):
        create_run(session_client, run_setup)

        assert claim(worker_client, harnesses=["codex"]).data == {"run": None}

    @pytest.mark.django_db
    def test_run_of_an_agent_that_is_no_longer_connected_is_not_claimed(self, session_client, worker_client, run_setup):
        create_run(session_client, run_setup)
        AgentConnection.objects.filter(agent=run_setup.agent).update(state="failed")

        assert claim(worker_client).data == {"run": None}


@pytest.mark.contract
class TestClaimRace:
    @pytest.mark.django_db(transaction=True)
    def test_concurrent_claims_lease_one_run_once(self, session_client, run_setup):
        run = create_run(session_client, run_setup)
        clients = [worker_client_for(make_worker(name=f"mini-{index}")[1]) for index in range(4)]
        barrier = threading.Barrier(len(clients))
        results = []
        errors = []

        def worker(client):
            try:
                barrier.wait()
                results.append(claim(client).data["run"])
            except Exception as error:  # noqa: BLE001 - collected and asserted below
                errors.append(error)
            finally:
                db_connection.close()

        threads = [threading.Thread(target=worker, args=(client,)) for client in clients]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        claimed = [body for body in results if body is not None]
        assert [body["id"] for body in claimed] == [str(run.id)]
        assert AgentRunTurn.objects.filter(run=run).count() == 1
        assert AgentRun.objects.get(pk=run.pk).lease_generation == 1


@pytest.mark.contract
class TestRenew:
    @pytest.mark.django_db
    def test_renew_extends_the_lease(self, session_client, worker_client, run_setup):
        run = create_run(session_client, run_setup)
        claimed = claim_run(worker_client)
        AgentRun.objects.filter(pk=run.pk).update(lease_expires_at=timezone.now() + timedelta(seconds=10))

        response = renew(worker_client, run.id, claimed["lease_generation"])

        assert response.status_code == status.HTTP_200_OK
        assert parse_datetime(str(response.data["lease_expires_at"])) >= timezone.now() + timedelta(seconds=290)

    @pytest.mark.django_db
    def test_old_generation_gets_409(self, session_client, worker_client, run_setup):
        run = create_run(session_client, run_setup)
        claimed = claim_run(worker_client)
        AgentRun.objects.filter(pk=run.pk).update(lease_generation=claimed["lease_generation"] + 1)

        response = renew(worker_client, run.id, claimed["lease_generation"])

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data == {"error": "lease_superseded"}

    @pytest.mark.django_db
    def test_another_worker_gets_409(self, session_client, worker_client, run_setup):
        run = create_run(session_client, run_setup)
        claimed = claim_run(worker_client)
        other = worker_client_for(make_worker(name="other")[1])

        response = renew(other, run.id, claimed["lease_generation"])

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data == {"error": "lease_superseded"}

    @pytest.mark.django_db
    def test_finished_run_gets_409(self, session_client, worker_client, run_setup):
        run = create_run(session_client, run_setup)
        claimed = claim_run(worker_client)
        AgentRun.objects.filter(pk=run.pk).update(status="completed")

        response = renew(worker_client, run.id, claimed["lease_generation"])

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data == {"error": "run_finished"}

    @pytest.mark.django_db
    def test_unknown_run_gets_404(self, worker_client, run_setup):
        response = renew(worker_client, run_setup.issue.id, 1)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_member_session_cannot_call_the_worker_api(self, session_client, run_setup):
        run = create_run(session_client, run_setup)

        response = renew(session_client, run.id, 1)

        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.contract
class TestCloneReport:
    @pytest.mark.django_db
    def test_successful_clone_stores_the_clone_path(self, session_client, worker_client, run_setup):
        run = create_run(session_client, run_setup)
        claimed = claim_run(worker_client)
        clone_path = f"/var/plane/runs/sandboxes/k/clones/{run.id}/clone"

        response = worker_client.post(
            worker_run_url(run.id, "clone"),
            {"lease_generation": claimed["lease_generation"], "ok": True, "clone_path": clone_path},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {}
        run.refresh_from_db()
        assert run.clone_path == clone_path

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "body",
        [
            {"ok": True, "clone_path": "relative/clone"},
            {"ok": True},
            {"ok": False},
            {"ok": False, "error_code": "git_exploded"},
            {"ok": "yes", "clone_path": "/abs"},
        ],
    )
    def test_invalid_report_gets_400(self, session_client, worker_client, run_setup, body):
        run = create_run(session_client, run_setup)
        claimed = claim_run(worker_client)

        response = worker_client.post(
            worker_run_url(run.id, "clone"), {"lease_generation": claimed["lease_generation"], **body}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
