# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import threading
import time
from datetime import timedelta

import pytest
from django.db import connection as db_connection
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status

from plane.agent.git_providers.base import ProviderError
from plane.agent.services import github_connection
from plane.db.models import AgentGitConnection, AgentGithubDeviceAuthorization, WorkspaceMember
from plane.license.models import InstanceConfiguration
from plane.license.utils.encryption import decrypt_data, encrypt_data
from plane.tests.agent_git_fixtures import (
    GITHUB_ACCESS_TOKEN,
    GITHUB_CLIENT_SECRET,
    GITHUB_DEVICE_CODE,
    GITHUB_REFRESH_TOKEN,
    add_github_connect_routes,
    client_for_user,
    connect_github,
    device_authorization_url,
    expire_connection_token,
    github_device_code_response,
    github_error_response,
    github_token_response,
    github_user_response,
    make_workspace_user,
)

CONNECTIONS_URL = "/api/workspaces/{slug}/agent-git/connections/"


def start(client, slug, kind="user"):
    return client.post(device_authorization_url(slug), {"kind": kind}, format="json")


def poll(client, slug, auth_id):
    return client.post(device_authorization_url(slug, auth_id, "poll"), {}, format="json")


@pytest.mark.contract
class TestDeviceFlowStart:
    @pytest.mark.django_db
    def test_start_returns_code_and_never_returns_device_code(
        self, session_client, workspace, fake_http, github_app_env
    ):
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response())

        response = start(session_client, workspace.slug)

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data["user_code"] == "WDJB-MJHT"
        assert response.data["verification_uri"] == "https://github.com/login/device"
        assert response.data["status"] == "pending"
        assert response.data["expires_at"]
        assert "device_code" not in response.data
        lifetime = parse_datetime(response.data["expires_at"]) - parse_datetime(response.data["created_at"])
        assert abs(lifetime.total_seconds() - 900) < 5
        row = AgentGithubDeviceAuthorization.objects.get(pk=response.data["id"])
        assert row.device_code != GITHUB_DEVICE_CODE
        assert decrypt_data(row.device_code) == GITHUB_DEVICE_CODE

    @pytest.mark.django_db
    def test_start_without_app_credentials_returns_actionable_error(
        self, session_client, workspace, fake_http, monkeypatch
    ):
        for key in ("GITHUB_APP_CLIENT_ID", "GITHUB_APP_CLIENT_SECRET", "GITHUB_APP_SLUG"):
            monkeypatch.delenv(key, raising=False)

        response = start(session_client, workspace.slug)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "github_app_not_configured"
        assert fake_http.calls == []

    @pytest.mark.django_db
    def test_start_when_device_flow_is_disabled_returns_hint(
        self, session_client, workspace, fake_http, github_app_env
    ):
        fake_http.add("POST", "github.com/login/device/code", github_error_response("device_flow_disabled"))

        response = start(session_client, workspace.slug)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "device_flow_disabled"

    @pytest.mark.django_db
    def test_created_at_is_set_by_the_server_and_not_writable(
        self, session_client, workspace, fake_http, github_app_env
    ):
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response())

        response = session_client.post(
            device_authorization_url(workspace.slug),
            {"kind": "user", "created_at": "2000-01-01T00:00:00Z"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created_at = parse_datetime(response.data["created_at"])
        assert abs((timezone.now() - created_at).total_seconds()) < 60
        row = AgentGithubDeviceAuthorization.objects.get(pk=response.data["id"])
        assert row.created_at == created_at

    @pytest.mark.django_db
    def test_start_rejects_unknown_kind(self, session_client, workspace, fake_http, github_app_env):
        response = start(session_client, workspace.slug, kind="team")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert fake_http.calls == []


@pytest.mark.contract
class TestDeviceFlowPoll:
    @pytest.mark.django_db
    def test_pending_poll_creates_no_connection(self, session_client, workspace, fake_http, github_app_env):
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response(interval=0))
        fake_http.add("POST", "github.com/login/oauth/access_token", github_error_response("authorization_pending"))
        auth_id = start(session_client, workspace.slug).data["id"]

        response = poll(session_client, workspace.slug, auth_id)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "pending"
        assert not AgentGitConnection.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    def test_poll_faster_than_interval_makes_no_github_call(self, session_client, workspace, fake_http, github_app_env):
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response(interval=5))
        fake_http.add("POST", "github.com/login/oauth/access_token", github_error_response("authorization_pending"))
        auth_id = start(session_client, workspace.slug).data["id"]

        poll(session_client, workspace.slug, auth_id)
        response = poll(session_client, workspace.slug, auth_id)

        assert response.data["status"] == "pending"
        assert fake_http.count("POST", "github.com/login/oauth/access_token") == 1

    @pytest.mark.django_db
    def test_slow_down_increases_the_interval(self, session_client, workspace, fake_http, github_app_env):
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response(interval=0))
        fake_http.add("POST", "github.com/login/oauth/access_token", github_error_response("slow_down"))
        auth_id = start(session_client, workspace.slug).data["id"]

        response = poll(session_client, workspace.slug, auth_id)

        assert response.data["status"] == "pending"
        assert response.data["interval"] == 5

    @pytest.mark.django_db
    def test_success_stores_encrypted_connection_and_shows_identity(
        self, session_client, workspace, create_user, fake_http, github_app_env
    ):
        response = connect_github(session_client, workspace.slug, fake_http)

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["status"] == "completed"
        connection = AgentGitConnection.objects.get(workspace=workspace, provider="github")
        assert connection.status == "connected"
        assert connection.account_login == "octo-admin"
        assert connection.connected_by_id == create_user.id
        assert connection.host == "github.com"
        assert connection.access_token != GITHUB_ACCESS_TOKEN
        assert decrypt_data(connection.access_token) == GITHUB_ACCESS_TOKEN
        assert decrypt_data(connection.refresh_token) == GITHUB_REFRESH_TOKEN
        assert connection.token_expires_at > timezone.now()

        listed = session_client.get(CONNECTIONS_URL.format(slug=workspace.slug))
        assert listed.status_code == status.HTTP_200_OK
        github = next(item for item in listed.data if item["provider"] == "github")
        assert github["status"] == "connected"
        assert github["account_login"] == "octo-admin"
        assert str(github["connected_by_detail"]["id"]) == str(create_user.id)

    @pytest.mark.django_db
    def test_expired_code_from_github_creates_no_connection(self, session_client, workspace, fake_http, github_app_env):
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response(interval=0))
        fake_http.add("POST", "github.com/login/oauth/access_token", github_error_response("expired_token"))
        auth_id = start(session_client, workspace.slug).data["id"]

        response = poll(session_client, workspace.slug, auth_id)

        assert response.data["status"] == "expired"
        assert not AgentGitConnection.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    def test_locally_expired_code_makes_no_github_call(self, session_client, workspace, fake_http, github_app_env):
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response(interval=0))
        auth_id = start(session_client, workspace.slug).data["id"]
        AgentGithubDeviceAuthorization.objects.filter(pk=auth_id).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        response = poll(session_client, workspace.slug, auth_id)

        assert response.data["status"] == "expired"
        assert fake_http.count("POST", "github.com/login/oauth/access_token") == 0

    @pytest.mark.django_db
    def test_denied_authorization_creates_no_connection(self, session_client, workspace, fake_http, github_app_env):
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response(interval=0))
        fake_http.add("POST", "github.com/login/oauth/access_token", github_error_response("access_denied"))
        auth_id = start(session_client, workspace.slug).data["id"]

        response = poll(session_client, workspace.slug, auth_id)

        assert response.data["status"] == "denied"
        assert not AgentGitConnection.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    def test_cancel_creates_no_connection_and_later_poll_stays_cancelled(
        self, session_client, workspace, fake_http, github_app_env
    ):
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response(interval=0))
        auth_id = start(session_client, workspace.slug).data["id"]

        cancelled = session_client.post(device_authorization_url(workspace.slug, auth_id, "cancel"), {}, format="json")
        polled = poll(session_client, workspace.slug, auth_id)

        assert cancelled.status_code == status.HTTP_200_OK
        assert cancelled.data["status"] == "cancelled"
        assert polled.data["status"] == "cancelled"
        assert fake_http.count("POST", "github.com/login/oauth/access_token") == 0
        assert not AgentGitConnection.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    def test_poll_of_another_workspace_authorization_returns_404(
        self, session_client, workspace, create_user, fake_http, github_app_env
    ):
        from plane.db.models import Workspace

        other = Workspace.objects.create(name="Other", slug="other-ws", owner=create_user)
        WorkspaceMember.objects.create(workspace=other, member=create_user, role=20)
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response(interval=0))
        auth_id = start(session_client, other.slug).data["id"]

        response = poll(session_client, workspace.slug, auth_id)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_empty_ciphertext_does_not_set_connected(
        self, session_client, workspace, fake_http, github_app_env, mocker
    ):
        add_github_connect_routes(fake_http)
        auth_id = start(session_client, workspace.slug).data["id"]
        mocker.patch("plane.agent.services.git_connection.encrypt_data", return_value="")

        response = poll(session_client, workspace.slug, auth_id)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["error"] == "token_encryption_failed"
        assert not AgentGitConnection.objects.filter(workspace=workspace, status="connected").exists()


@pytest.mark.contract
class TestDeviceFlowSecrets:
    @pytest.mark.django_db
    def test_tokens_never_appear_in_responses_or_logs(
        self, session_client, workspace, fake_http, github_app_env, agent_caplog
    ):
        add_github_connect_routes(fake_http)
        started = start(session_client, workspace.slug)
        polled = poll(session_client, workspace.slug, started.data["id"])
        listed = session_client.get(CONNECTIONS_URL.format(slug=workspace.slug))

        secrets = (GITHUB_ACCESS_TOKEN, GITHUB_REFRESH_TOKEN, GITHUB_DEVICE_CODE, GITHUB_CLIENT_SECRET)
        for response in (started, polled, listed):
            body = response.content.decode()
            for secret in secrets:
                assert secret not in body
            assert "access_token" not in body
            assert "refresh_token" not in body
        assert agent_caplog.records, "the http seam and services are expected to log their calls"
        for record in agent_caplog.records:
            message = record.getMessage()
            for secret in secrets:
                assert secret not in message


@pytest.mark.contract
class TestDeviceFlowPermissions:
    @pytest.mark.django_db
    @pytest.mark.parametrize("client_fixture", ["member_client", "guest_client"])
    def test_non_admins_cannot_start_poll_or_cancel(
        self, request, client_fixture, session_client, workspace, fake_http, github_app_env
    ):
        client = request.getfixturevalue(client_fixture)
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response(interval=0))
        auth_id = start(session_client, workspace.slug).data["id"]

        assert start(client, workspace.slug).status_code == status.HTTP_403_FORBIDDEN
        assert poll(client, workspace.slug, auth_id).status_code == status.HTTP_403_FORBIDDEN
        cancel = client.post(device_authorization_url(workspace.slug, auth_id, "cancel"), {}, format="json")
        assert cancel.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_member_can_read_connections_and_guest_cannot(self, member_client, guest_client, workspace):
        assert member_client.get(CONNECTIONS_URL.format(slug=workspace.slug)).status_code == status.HTTP_200_OK
        assert guest_client.get(CONNECTIONS_URL.format(slug=workspace.slug)).status_code == status.HTTP_403_FORBIDDEN


def _run_threads(target, count=2, timeout=30):
    results = [None] * count
    errors = []
    barrier = threading.Barrier(count)

    def runner(index):
        try:
            barrier.wait(timeout=timeout)
            results[index] = target()
        except Exception as exc:  # surfaced through the errors list below
            errors.append(exc)
        finally:
            db_connection.close()

    threads = [threading.Thread(target=runner, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=timeout)
        assert not thread.is_alive(), "worker thread did not finish"
    return results, errors


@pytest.mark.contract
class TestDeviceFlowConcurrency:
    @pytest.mark.django_db(transaction=True)
    def test_two_concurrent_polls_store_one_connection_and_stay_completed(
        self, session_client, workspace, create_user, fake_http, github_app_env
    ):
        def slow_token(call):
            time.sleep(0.3)
            return github_token_response()

        add_github_connect_routes(fake_http, token_response=slow_token)
        fake_http.add("POST", "github.com/login/device/code", github_device_code_response(interval=0))
        auth_id = start(session_client, workspace.slug).data["id"]

        results, errors = _run_threads(lambda: poll(client_for_user(create_user), workspace.slug, auth_id))

        assert not errors, errors
        assert [r.data["status"] for r in results] == ["completed", "completed"]
        assert fake_http.count("POST", "github.com/login/oauth/access_token") == 1
        assert AgentGitConnection.objects.filter(workspace=workspace, provider="github").count() == 1
        assert AgentGithubDeviceAuthorization.objects.get(pk=auth_id).status == "completed"

    @pytest.mark.django_db(transaction=True)
    def test_two_concurrent_refreshes_call_github_once(self, session_client, workspace, fake_http, github_app_env):
        connect_github(session_client, workspace.slug, fake_http)
        connection = AgentGitConnection.objects.get(workspace=workspace, provider="github")
        expire_connection_token(connection)

        def slow_refresh(call):
            time.sleep(0.3)
            return github_token_response(access_token="ghu_REFRESHED_0002", refresh_token="ghr_REFRESHED_0002")

        fake_http.add("POST", "github.com/login/oauth/access_token", slow_refresh)

        results, errors = _run_threads(lambda: github_connection.usable_token(connection.id))

        assert not errors, errors
        assert results == ["ghu_REFRESHED_0002", "ghu_REFRESHED_0002"]
        refresh_calls = [
            call
            for call in fake_http.calls
            if call["host_path"] == "github.com/login/oauth/access_token"
            and (call.get("data") or {}).get("grant_type") == "refresh_token"
        ]
        assert len(refresh_calls) == 1
        connection.refresh_from_db()
        assert decrypt_data(connection.refresh_token) == "ghr_REFRESHED_0002"


@pytest.mark.contract
class TestUsableToken:
    @pytest.mark.django_db
    def test_empty_decrypt_sets_reconnect_required_without_provider_call(
        self, session_client, workspace, fake_http, github_app_env
    ):
        connect_github(session_client, workspace.slug, fake_http)
        connection = AgentGitConnection.objects.get(workspace=workspace, provider="github")
        connection.access_token = "not-a-fernet-token"
        connection.save(update_fields=["access_token"])
        calls_before = len(fake_http.calls)

        with pytest.raises(ProviderError) as error:
            github_connection.usable_token(connection.id)

        assert error.value.code == "provider_reconnect_required"
        assert len(fake_http.calls) == calls_before
        connection.refresh_from_db()
        assert connection.status == "reconnect_required"

    @pytest.mark.django_db
    def test_unexpired_token_is_returned_without_refresh(self, session_client, workspace, fake_http, github_app_env):
        connect_github(session_client, workspace.slug, fake_http)
        connection = AgentGitConnection.objects.get(workspace=workspace, provider="github")
        calls_before = len(fake_http.calls)

        assert github_connection.usable_token(connection.id) == GITHUB_ACCESS_TOKEN
        assert len(fake_http.calls) == calls_before

    @pytest.mark.django_db
    def test_rejected_refresh_token_sets_reconnect_required(self, session_client, workspace, fake_http, github_app_env):
        connect_github(session_client, workspace.slug, fake_http)
        connection = AgentGitConnection.objects.get(workspace=workspace, provider="github")
        expire_connection_token(connection)
        fake_http.add("POST", "github.com/login/oauth/access_token", github_error_response("bad_refresh_token"))

        with pytest.raises(ProviderError) as error:
            github_connection.usable_token(connection.id)

        assert error.value.code == "provider_reconnect_required"
        connection.refresh_from_db()
        assert connection.status == "reconnect_required"
        assert connection.last_error == "github_refresh_failed"


@pytest.mark.contract
class TestAppCredentials:
    @pytest.mark.django_db
    def test_env_value_is_used_when_instance_configuration_is_empty(self, monkeypatch):
        monkeypatch.setenv("GITHUB_APP_CLIENT_ID", "env-client-id")
        monkeypatch.setenv("GITHUB_APP_CLIENT_SECRET", "env-secret")
        monkeypatch.setenv("GITHUB_APP_SLUG", "env-slug")
        InstanceConfiguration.objects.create(key="GITHUB_APP_CLIENT_ID", value="", category="GITHUB_APP")
        InstanceConfiguration.objects.create(
            key="GITHUB_APP_CLIENT_SECRET", value="", category="GITHUB_APP", is_encrypted=True
        )

        credentials = github_connection.app_credentials()

        assert credentials.client_id == "env-client-id"
        assert credentials.client_secret == "env-secret"
        assert credentials.slug == "env-slug"

    @pytest.mark.django_db
    def test_instance_configuration_value_wins_when_set(self, monkeypatch):
        monkeypatch.setenv("GITHUB_APP_CLIENT_ID", "env-client-id")
        monkeypatch.setenv("GITHUB_APP_CLIENT_SECRET", "env-secret")
        InstanceConfiguration.objects.create(key="GITHUB_APP_CLIENT_ID", value="db-client-id", category="GITHUB_APP")
        InstanceConfiguration.objects.create(
            key="GITHUB_APP_CLIENT_SECRET",
            value=encrypt_data("db-secret"),
            category="GITHUB_APP",
            is_encrypted=True,
        )

        credentials = github_connection.app_credentials()

        assert credentials.client_id == "db-client-id"
        assert credentials.client_secret == "db-secret"


@pytest.mark.contract
class TestConnectingAdminLeaves:
    def _connected(self, session_client, workspace, fake_http):
        connect_github(session_client, workspace.slug, fake_http)
        return AgentGitConnection.objects.get(workspace=workspace, provider="github")

    @pytest.mark.django_db
    @pytest.mark.parametrize("change", [{"role": 15}, {"is_active": False}])
    def test_token_use_after_admin_loss_returns_reconnect_required_without_github_call(
        self, change, session_client, workspace, create_user, fake_http, github_app_env
    ):
        connection = self._connected(session_client, workspace, fake_http)
        WorkspaceMember.objects.filter(workspace=workspace, member=create_user).update(**change)
        calls_before = len(fake_http.calls)

        with pytest.raises(ProviderError) as error:
            github_connection.usable_token(connection.id)

        assert error.value.code == "provider_reconnect_required"
        assert len(fake_http.calls) == calls_before
        connection.refresh_from_db()
        assert connection.status == "reconnect_required"
        assert connection.last_error == "connected_admin_lost"

    @pytest.mark.django_db
    def test_connections_list_shows_reconnect_required_after_demotion(
        self, session_client, workspace, create_user, fake_http, github_app_env
    ):
        self._connected(session_client, workspace, fake_http)
        other_admin = client_for_user(make_workspace_user(workspace, 20))
        WorkspaceMember.objects.filter(workspace=workspace, member=create_user).update(role=15)

        listed = other_admin.get(CONNECTIONS_URL.format(slug=workspace.slug))

        github = next(item for item in listed.data if item["provider"] == "github")
        assert github["status"] == "reconnect_required"
        assert github["last_error"] == "connected_admin_lost"

    @pytest.mark.django_db
    def test_another_admin_reconnect_restores_connected(
        self, session_client, workspace, create_user, fake_http, github_app_env
    ):
        connection = self._connected(session_client, workspace, fake_http)
        second_admin = make_workspace_user(workspace, 20)
        WorkspaceMember.objects.filter(workspace=workspace, member=create_user).update(role=15)
        with pytest.raises(ProviderError):
            github_connection.usable_token(connection.id)

        fake_http.add("GET", "api.github.com/user", github_user_response(login="second-admin", user_id=202))
        response = connect_github(client_for_user(second_admin), workspace.slug, fake_http)

        assert response.data["status"] == "completed"
        connection.refresh_from_db()
        assert connection.status == "connected"
        assert connection.last_error == ""
        assert connection.connected_by_id == second_admin.id
        assert AgentGitConnection.objects.filter(workspace=workspace, provider="github").count() == 1


@pytest.mark.contract
class TestDeviceFlowNoProviderHostChange:
    @pytest.mark.django_db
    def test_github_calls_use_fixed_hosts_only(self, session_client, workspace, fake_http, github_app_env):
        connect_github(session_client, workspace.slug, fake_http)

        assert {call["host"] for call in fake_http.calls} <= {"github.com", "api.github.com"}
        assert all(call["url"].startswith("https://") for call in fake_http.calls)
