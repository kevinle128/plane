# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import datetime
import time

import pytest
from rest_framework import status

from plane.agent.git_providers.base import ProviderError
from plane.db.models import AgentGitAccount, AgentGitConnection, ProjectRepositoryBinding
from plane.license.utils.encryption import decrypt_data
from plane.tests.agent_git_fakes import json_response, text_response
from plane.tests.agent_git_fixtures import (
    GITLAB_BASE_URL,
    GITLAB_TOKEN,
    add_gitlab_connect_routes,
    gitlab_connect_payload,
    gitlab_connection_url,
    gitlab_fixture,
    gitlab_path,
    make_catalog,
    project_payload,
    projects_url,
)

CONNECTIONS_URL = "/api/workspaces/{slug}/agent-git/connections/"
SELF = gitlab_path("personal_access_tokens/self")
VERSION = gitlab_path("version")


def connect(client, slug, **overrides):
    return client.post(gitlab_connection_url(slug), gitlab_connect_payload(**overrides), format="json")


def assert_nothing_stored(workspace):
    assert not AgentGitConnection.objects.filter(workspace=workspace, provider="gitlab", status="connected").exists()
    assert not AgentGitAccount.objects.filter(workspace=workspace, provider="gitlab").exists()


def visited(fake):
    return [call["path"].removeprefix("/api/v4/") for call in fake.calls]


def self_signed_pem():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Plane Test CA")])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return certificate.public_bytes(serialization.Encoding.PEM).decode()


@pytest.mark.contract
class TestGitlabConnectSuccess:
    @pytest.mark.django_db
    def test_connect_stores_the_connection_and_attaches_the_group(
        self, session_client, workspace, create_user, fake_http, mock_celery, agent_caplog
    ):
        add_gitlab_connect_routes(fake_http)

        response = connect(session_client, workspace.slug)

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert visited(fake_http) == [
            "personal_access_tokens/self",
            "version",
            "user",
            "groups/platform",
            "groups/19/members/all/77",
        ]
        connection = AgentGitConnection.objects.get(workspace=workspace, provider="gitlab")
        assert connection.status == "connected"
        assert connection.base_url == GITLAB_BASE_URL
        assert connection.host == "git.example.com"
        assert connection.server_version == "18.10.3-ee"
        assert connection.token_name == "plane-agents"
        assert connection.token_scopes == ["api", "write_repository"]
        assert connection.account_login == "group_19_bot_0123456789abcdef"
        assert connection.account_is_bot is True
        assert connection.token_expires_at is None
        assert connection.warnings == []
        assert connection.connected_by_id == create_user.id
        assert decrypt_data(connection.access_token) == GITLAB_TOKEN
        group = AgentGitAccount.objects.get(connection=connection)
        assert (group.external_id, group.login, group.state, group.account_type) == (
            "19",
            "platform",
            "attached",
            "Group",
        )

        listed = session_client.get(CONNECTIONS_URL.format(slug=workspace.slug))
        gitlab = next(item for item in listed.data if item["provider"] == "gitlab")
        assert gitlab["server_version"] == "18.10.3-ee"
        assert gitlab["token_name"] == "plane-agents"
        for body in (response.content.decode(), listed.content.decode()):
            assert GITLAB_TOKEN not in body
        for record in agent_caplog.records:
            assert GITLAB_TOKEN not in record.getMessage()
        for call in fake_http.calls:
            assert GITLAB_TOKEN not in call["url"]
            assert call["headers"]["PRIVATE-TOKEN"] == GITLAB_TOKEN

    @pytest.mark.django_db
    def test_all_checks_share_one_thirty_second_budget(self, session_client, workspace, fake_http, mock_celery):
        add_gitlab_connect_routes(fake_http)
        before = time.monotonic()

        connect(session_client, workspace.slug)

        deadlines = {call["deadline"] for call in fake_http.calls}
        assert len(deadlines) == 1
        assert before + 29 <= deadlines.pop() <= time.monotonic() + 30

    @pytest.mark.django_db
    def test_expiry_date_is_stored(self, session_client, workspace, fake_http, mock_celery):
        token = {**gitlab_fixture("token_self_active.json"), "expires_at": "2099-01-31"}
        add_gitlab_connect_routes(fake_http, token=json_response(200, token))

        connect(session_client, workspace.slug)

        connection = AgentGitConnection.objects.get(workspace=workspace, provider="gitlab")
        assert connection.token_expires_at.date() == datetime.date(2099, 1, 31)

    @pytest.mark.django_db
    def test_relative_root_base_url_keeps_its_path(self, session_client, workspace, fake_http, mock_celery):
        add_gitlab_connect_routes(fake_http, base_path="/gitlab")

        response = connect(session_client, workspace.slug, base_url=f"{GITLAB_BASE_URL}/gitlab/")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert AgentGitConnection.objects.get(workspace=workspace, provider="gitlab").base_url == (
            f"{GITLAB_BASE_URL}/gitlab"
        )
        assert all(call["path"].startswith("/gitlab/api/v4/") for call in fake_http.calls)

    @pytest.mark.django_db
    def test_nested_group_path_is_url_encoded(self, session_client, workspace, fake_http, mock_celery):
        add_gitlab_connect_routes(fake_http, group_path="platform/tools")

        response = connect(session_client, workspace.slug, group_path="platform/tools")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert "groups/platform%2Ftools" in visited(fake_http)

    @pytest.mark.django_db
    def test_human_token_connects_with_a_warning(self, session_client, workspace, fake_http, mock_celery):
        add_gitlab_connect_routes(fake_http, user="user_human.json")

        response = connect(session_client, workspace.slug)

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data["warnings"] == ["gitlab_token_not_bot"]
        assert AgentGitConnection.objects.get(workspace=workspace, provider="gitlab").account_is_bot is False

    @pytest.mark.django_db
    def test_github_and_gitlab_connections_coexist(
        self, session_client, workspace, create_user, fake_http, mock_celery
    ):
        make_catalog(workspace, create_user, repositories=[(501, "plane-mini/api")])
        add_gitlab_connect_routes(fake_http)

        connect(session_client, workspace.slug)

        listed = session_client.get(CONNECTIONS_URL.format(slug=workspace.slug))
        assert {item["provider"]: item["status"] for item in listed.data} == {
            "github": "connected",
            "gitlab": "connected",
        }


@pytest.mark.contract
class TestGitlabConnectFailures:
    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "fixture, missing",
        [
            ("token_self_api_only.json", "write_repository"),
            ("token_self_write_repository_only.json", "api"),
        ],
    )
    def test_missing_scope_is_named_and_stops_the_checks(
        self, fixture, missing, session_client, workspace, fake_http, mock_celery
    ):
        add_gitlab_connect_routes(fake_http, token=fixture)

        response = connect(session_client, workspace.slug)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (response.data["error"], response.data["detail"]) == ("gitlab_scope_missing", missing)
        assert visited(fake_http) == ["personal_access_tokens/self"]
        assert_nothing_stored(workspace)

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "token_response",
        [
            json_response(401, {"message": "401 Unauthorized"}),
            json_response(200, gitlab_fixture("token_self_expired.json")),
            json_response(200, gitlab_fixture("token_self_revoked.json")),
            json_response(200, {**gitlab_fixture("token_self_active.json"), "expires_at": "2020-01-01"}),
            json_response(200, {**gitlab_fixture("token_self_active.json"), "active": False}),
        ],
        ids=["401", "expired", "revoked", "past-expiry", "inactive"],
    )
    def test_expired_revoked_or_inactive_token_is_rejected_before_version(
        self, token_response, session_client, workspace, fake_http, mock_celery
    ):
        add_gitlab_connect_routes(fake_http, token=token_response)

        response = connect(session_client, workspace.slug)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "gitlab_token_invalid"
        assert visited(fake_http) == ["personal_access_tokens/self"]
        assert_nothing_stored(workspace)

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "error",
        [
            ProviderError("gitlab_url_unreachable", "gitlab", "timeout", http_status=502),
            ProviderError("gitlab_url_unreachable", "gitlab", "connection", http_status=502),
            ProviderError("gitlab_url_redirected", "gitlab", "https://login.example.com", http_status=502),
            ProviderError("gitlab_url_not_allowed_or_unresolved", "gitlab", http_status=400),
            ProviderError("gitlab_tls_failed", "gitlab", http_status=502),
            ProviderError("gitlab_unexpected_response", "gitlab", "response_too_large", http_status=502),
        ],
        ids=["timeout", "refused", "redirect", "blocked-or-unresolved", "tls", "body-too-large"],
    )
    def test_transport_failures_return_their_code_and_store_nothing(
        self, error, session_client, workspace, fake_http, mock_celery
    ):
        fake_http.add("GET", SELF, error)

        response = connect(session_client, workspace.slug)

        assert response.data["error"] == error.code
        assert response.data.get("detail", "") == error.detail
        assert response.status_code == error.http_status
        assert_nothing_stored(workspace)

    @pytest.mark.django_db
    def test_budget_exhausted_on_a_later_check_stores_nothing(self, session_client, workspace, fake_http, mock_celery):
        add_gitlab_connect_routes(fake_http)
        fake_http.add(
            "GET", gitlab_path("groups/platform"), ProviderError("gitlab_url_unreachable", "gitlab", "timeout")
        )

        response = connect(session_client, workspace.slug)

        assert (response.data["error"], response.data["detail"]) == ("gitlab_url_unreachable", "timeout")
        assert_nothing_stored(workspace)

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "version_response, code",
        [
            (json_response(200, gitlab_fixture("version_15_4.json")), "gitlab_version_unsupported"),
            (json_response(404, {"message": "404 Not Found"}), "gitlab_not_gitlab"),
            (text_response(200, "<html>Welcome</html>"), "gitlab_not_gitlab"),
            (json_response(403, gitlab_fixture("version_insufficient_scope.json")), "gitlab_unexpected_response"),
        ],
        ids=["old-server", "no-api", "html", "pre-15.5-write-only-token"],
    )
    def test_token_self_404_is_explained_by_the_version_call(
        self, version_response, code, session_client, workspace, fake_http, mock_celery
    ):
        fake_http.add("GET", SELF, json_response(404, gitlab_fixture("token_self_not_found.json")))
        fake_http.add("GET", VERSION, version_response)

        response = connect(session_client, workspace.slug)

        assert response.data["error"] == code
        assert visited(fake_http) == ["personal_access_tokens/self", "version"]
        assert_nothing_stored(workspace)

    @pytest.mark.django_db
    def test_unsupported_version_shows_found_and_minimum(self, session_client, workspace, fake_http, mock_celery):
        fake_http.add("GET", SELF, json_response(404, gitlab_fixture("token_self_not_found.json")))
        fake_http.add("GET", VERSION, json_response(200, gitlab_fixture("version_15_4.json")))

        response = connect(session_client, workspace.slug)

        assert response.data["detail"] == "found 15.4.9-ee, minimum 15.5"

    @pytest.mark.django_db
    def test_html_answer_on_token_self_is_not_gitlab(self, session_client, workspace, fake_http, mock_celery):
        fake_http.add("GET", SELF, text_response(200, "<html>Sign in</html>"))

        response = connect(session_client, workspace.slug)

        assert response.data["error"] == "gitlab_not_gitlab"
        assert_nothing_stored(workspace)

    @pytest.mark.django_db
    def test_version_below_minimum_after_token_check_is_rejected(
        self, session_client, workspace, fake_http, mock_celery
    ):
        add_gitlab_connect_routes(fake_http, version=json_response(200, {"version": "15.4.0"}))

        response = connect(session_client, workspace.slug)

        assert response.data["error"] == "gitlab_version_unsupported"
        assert_nothing_stored(workspace)

    @pytest.mark.django_db
    def test_unexpected_status_is_reported_not_raised(self, session_client, workspace, fake_http, mock_celery):
        add_gitlab_connect_routes(fake_http, user=json_response(500, {"message": "500 Internal Server Error"}))

        response = connect(session_client, workspace.slug)

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert (response.data["error"], response.data["detail"]) == ("gitlab_unexpected_response", "HTTP 500")
        assert_nothing_stored(workspace)

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "group_response",
        [json_response(404, gitlab_fixture("group_not_found.json")), json_response(403, {"message": "403 Forbidden"})],
        ids=["missing", "hidden"],
    )
    def test_unknown_or_hidden_group(self, group_response, session_client, workspace, fake_http, mock_celery):
        add_gitlab_connect_routes(fake_http, group=group_response)

        response = connect(session_client, workspace.slug)

        assert response.data["error"] == "gitlab_group_not_found"
        assert_nothing_stored(workspace)

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "member_response, found",
        [
            (json_response(200, gitlab_fixture("member_reporter.json")), "Reporter"),
            (json_response(404, {"message": "404 Not found"}), "none"),
        ],
        ids=["reporter", "not-a-member"],
    )
    def test_role_below_developer(self, member_response, found, session_client, workspace, fake_http, mock_celery):
        add_gitlab_connect_routes(fake_http, member=member_response)

        response = connect(session_client, workspace.slug)

        assert (response.data["error"], response.data["detail"]) == ("gitlab_role_too_low", found)
        assert_nothing_stored(workspace)

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "base_url",
        [
            "http://git.example.com",
            "https://user:pass@git.example.com",
            "https://git.example.com/?a=1",
            "https://git.example.com/#top",
            "git.example.com",
            "https://",
            "ftp://git.example.com",
        ],
    )
    def test_malformed_base_url_is_rejected_without_a_call(
        self, base_url, session_client, workspace, fake_http, mock_celery
    ):
        response = connect(session_client, workspace.slug, base_url=base_url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "gitlab_url_invalid"
        assert fake_http.calls == []

    @pytest.mark.django_db
    def test_plane_request_host_is_refused_without_a_call(self, session_client, workspace, fake_http, mock_celery):
        response = connect(session_client, workspace.slug, base_url="https://testserver")

        assert response.data["error"] == "gitlab_url_not_allowed_or_unresolved"
        assert fake_http.calls == []

    @pytest.mark.django_db
    def test_plane_request_host_is_refused_even_when_allowlisted(
        self, session_client, workspace, fake_http, mock_celery, settings
    ):
        settings.AGENT_GIT_ALLOWED_HOSTS = ["testserver"]

        response = connect(session_client, workspace.slug, base_url="https://testserver")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "gitlab_url_not_allowed_or_unresolved"
        assert fake_http.calls == []

    @pytest.mark.django_db
    def test_allowlisted_host_skips_the_disallowed_domains(
        self, session_client, workspace, fake_http, mock_celery, settings
    ):
        settings.WEBHOOK_DISALLOWED_DOMAINS = ["example.com"]
        settings.AGENT_GIT_ALLOWED_HOSTS = ["git.example.com"]
        add_gitlab_connect_routes(fake_http)

        response = connect(session_client, workspace.slug)

        assert response.status_code == status.HTTP_201_CREATED, response.data

    @pytest.mark.django_db
    def test_disallowed_domain_is_refused_without_a_call(
        self, session_client, workspace, fake_http, mock_celery, settings
    ):
        settings.WEBHOOK_DISALLOWED_DOMAINS = ["example.com"]

        response = connect(session_client, workspace.slug)

        assert response.data["error"] == "gitlab_url_not_allowed_or_unresolved"
        assert fake_http.calls == []

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "payload",
        [{"base_url": GITLAB_BASE_URL}, {"group_path": "platform", "token": GITLAB_TOKEN}, {"token": 12}],
    )
    def test_missing_fields_return_400(self, payload, session_client, workspace, fake_http, mock_celery):
        response = session_client.post(gitlab_connection_url(workspace.slug), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "invalid_request"

    @pytest.mark.django_db
    def test_empty_ciphertext_does_not_set_connected(self, session_client, workspace, fake_http, mock_celery, mocker):
        add_gitlab_connect_routes(fake_http)
        mocker.patch("plane.agent.services.git_connection.encrypt_data", return_value="")

        response = connect(session_client, workspace.slug)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["error"] == "token_encryption_failed"
        assert_nothing_stored(workspace)


@pytest.mark.contract
class TestGitlabCaBundle:
    @pytest.mark.django_db
    def test_untrusted_certificate_without_bundle(self, session_client, workspace, fake_http, mock_celery):
        fake_http.add("GET", SELF, ProviderError("gitlab_tls_failed", "gitlab", http_status=502))

        response = connect(session_client, workspace.slug)

        assert response.data["error"] == "gitlab_tls_failed"
        assert_nothing_stored(workspace)

    @pytest.mark.django_db
    def test_valid_bundle_is_used_for_every_check_and_stored(self, session_client, workspace, fake_http, mock_celery):
        pem = self_signed_pem()
        add_gitlab_connect_routes(fake_http)

        response = connect(session_client, workspace.slug, ca_bundle=pem)

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert all(call["ca_bundle"] == pem for call in fake_http.calls)
        assert AgentGitConnection.objects.get(workspace=workspace, provider="gitlab").ca_bundle == pem
        assert response.data["has_ca_bundle"] is True

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "bundle",
        ["not a certificate", "-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----\n", "x" * (256 * 1024 + 1)],
        ids=["text", "bad-pem", "too-large"],
    )
    def test_invalid_bundle_is_rejected_without_a_call(self, bundle, session_client, workspace, fake_http, mock_celery):
        response = connect(session_client, workspace.slug, ca_bundle=bundle)

        assert response.data["error"] == "gitlab_ca_invalid"
        assert fake_http.calls == []


@pytest.mark.contract
class TestGitlabReconnect:
    @pytest.mark.django_db
    def test_reconnect_with_another_group_detaches_the_old_group(
        self, session_client, workspace, fake_http, mock_celery
    ):
        add_gitlab_connect_routes(fake_http)
        connect(session_client, workspace.slug)
        connection = AgentGitConnection.objects.get(workspace=workspace, provider="gitlab")
        old_group = AgentGitAccount.objects.get(connection=connection)
        from plane.db.models import AgentGitRepository

        repository = AgentGitRepository.objects.create(
            account=old_group,
            workspace=workspace,
            provider="gitlab",
            external_id="101",
            full_name="platform/api",
            owner_login="platform",
            default_branch="main",
            clone_url="https://git.example.com/platform/api.git",
        )
        created = session_client.post(
            projects_url(workspace.slug),
            project_payload("Old", "OLD", {"repository_id": str(repository.id)}),
            format="json",
        )
        assert created.status_code == status.HTTP_201_CREATED, created.data
        add_gitlab_connect_routes(
            fake_http,
            group=json_response(200, {**gitlab_fixture("group.json"), "id": 20, "full_path": "data"}),
            group_path="data",
        )

        response = connect(session_client, workspace.slug, group_path="data")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        states = dict(AgentGitAccount.objects.filter(connection=connection).values_list("login", "state"))
        assert states == {"platform": "detached", "data": "attached"}
        from plane.agent.services.git_connection import binding_availability

        binding = ProjectRepositoryBinding.objects.get(project_id=created.data["id"])
        assert binding_availability(binding) == {"available": False, "reason": "repository_unavailable"}

    @pytest.mark.django_db
    def test_old_group_cannot_be_attached_again_with_the_new_token(
        self, session_client, workspace, fake_http, mock_celery
    ):
        add_gitlab_connect_routes(fake_http)
        connect(session_client, workspace.slug)
        connection = AgentGitConnection.objects.get(workspace=workspace, provider="gitlab")
        old_group = AgentGitAccount.objects.get(connection=connection)
        add_gitlab_connect_routes(
            fake_http,
            group=json_response(200, {**gitlab_fixture("group.json"), "id": 20, "full_path": "data"}),
            group_path="data",
        )
        assert connect(session_client, workspace.slug, group_path="data").status_code == status.HTTP_201_CREATED
        mock_celery.reset_mock()

        response = session_client.post(
            f"/api/workspaces/{workspace.slug}/agent-git/gitlab/accounts/{old_group.id}/attach/", {}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {"error": "account_attach_not_supported", "provider": "gitlab", "detail": "connect"}
        states = dict(AgentGitAccount.objects.filter(connection=connection).values_list("login", "state"))
        assert states == {"platform": "detached", "data": "attached"}
        mock_celery.assert_not_called()

    @pytest.mark.django_db
    def test_another_base_url_needs_disconnect_first(self, session_client, workspace, fake_http, mock_celery):
        add_gitlab_connect_routes(fake_http)
        connect(session_client, workspace.slug)

        response = connect(session_client, workspace.slug, base_url="https://gitlab.other.example")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["error"] == "gitlab_disconnect_first"
        assert AgentGitConnection.objects.get(workspace=workspace, provider="gitlab").base_url == GITLAB_BASE_URL


@pytest.mark.contract
class TestGitlabConnectPermissions:
    @pytest.mark.django_db
    @pytest.mark.parametrize("client_fixture", ["member_client", "guest_client"])
    def test_non_admins_get_403(self, request, client_fixture, workspace, fake_http, mock_celery):
        client = request.getfixturevalue(client_fixture)

        response = connect(client, workspace.slug)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert fake_http.calls == []
