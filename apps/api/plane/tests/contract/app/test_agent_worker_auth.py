# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import hashlib
import io
import os
import stat

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import AgentWorker
from plane.tests.agent_settings_fixtures import make_worker, worker_client_for

HEARTBEAT_URL = "/api/agent-worker/v1/heartbeat/"


@pytest.mark.contract
class TestWorkerTokenAuthentication:
    @pytest.mark.django_db
    def test_heartbeat_with_the_worker_token_records_last_seen(self, agent_worker, worker_client):
        worker, _ = agent_worker

        response = worker_client.post(HEARTBEAT_URL, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["worker"] == "mini"
        worker.refresh_from_db()
        assert worker.last_seen_at is not None

    @pytest.mark.django_db
    def test_120_calls_in_one_minute_are_not_throttled(self, worker_client):
        codes = {worker_client.post(HEARTBEAT_URL, {}, format="json").status_code for _ in range(120)}

        assert codes == {status.HTTP_200_OK}

    @pytest.mark.django_db
    def test_revoked_token_returns_401(self):
        _, token = make_worker(revoked_at=timezone.now())

        response = worker_client_for(token).post(HEARTBEAT_URL, {}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_unknown_token_returns_401(self):
        response = worker_client_for("plane_aw_unknown").post(HEARTBEAT_URL, {}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_missing_token_returns_401(self):
        assert APIClient().post(HEARTBEAT_URL, {}, format="json").status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_worker_token_in_x_api_key_is_rejected(self, agent_worker):
        _, token = agent_worker
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=token)

        assert client.post(HEARTBEAT_URL, {}, format="json").status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_session_user_cannot_call_worker_endpoints(self, create_user):
        client = APIClient()
        client.force_login(create_user)

        assert client.post(HEARTBEAT_URL, {}, format="json").status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_user_principal_is_refused_even_when_authenticated(self, session_client):
        assert session_client.post(HEARTBEAT_URL, {}, format="json").status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_worker_request_is_not_sent_to_the_api_activity_log(self, worker_client, mocker):
        process_logs = mocker.patch("plane.middleware.logger.process_logs")

        response = worker_client.post(HEARTBEAT_URL, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        process_logs.delay.assert_not_called()

    @pytest.mark.django_db
    def test_worker_token_does_not_open_member_endpoints(self, worker_client, workspace):
        response = worker_client.get(f"/api/workspaces/{workspace.slug}/agents/")

        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.contract
class TestCreateAgentWorkerCommand:
    @pytest.mark.django_db
    def test_command_writes_a_private_token_file_and_stores_only_the_hash(self, tmp_path):
        token_file = tmp_path / "worker-token"
        stdout, stderr = io.StringIO(), io.StringIO()

        call_command(
            "create_agent_worker", "--name", "mini", "--token-file", str(token_file), stdout=stdout, stderr=stderr
        )

        token = token_file.read_text().strip()
        assert token
        assert stat.S_IMODE(os.stat(token_file).st_mode) == 0o600
        worker = AgentWorker.objects.get(name="mini")
        assert worker.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert token not in stdout.getvalue()
        assert token not in stderr.getvalue()
        assert str(token_file) in stdout.getvalue()

    @pytest.mark.django_db
    def test_token_from_the_command_authenticates(self, tmp_path):
        token_file = tmp_path / "worker-token"
        call_command("create_agent_worker", "--name", "mini", "--token-file", str(token_file), stdout=io.StringIO())

        response = worker_client_for(token_file.read_text().strip()).post(HEARTBEAT_URL, {}, format="json")

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_existing_token_file_is_not_overwritten(self, tmp_path):
        token_file = tmp_path / "worker-token"
        token_file.write_text("keep me")

        with pytest.raises(CommandError):
            call_command("create_agent_worker", "--name", "mini", "--token-file", str(token_file), stdout=io.StringIO())

        assert token_file.read_text() == "keep me"
        assert not AgentWorker.objects.exists()

    @pytest.mark.django_db
    def test_duplicate_name_is_rejected_and_writes_no_file(self, tmp_path):
        make_worker(name="mini")
        token_file = tmp_path / "worker-token"

        with pytest.raises(CommandError):
            call_command("create_agent_worker", "--name", "mini", "--token-file", str(token_file), stdout=io.StringIO())

        assert not token_file.exists()
        assert AgentWorker.objects.count() == 1
