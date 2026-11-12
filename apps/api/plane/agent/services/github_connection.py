# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""GitHub App connection: device flow, token refresh and the connecting-admin rule.

GitHub App refresh tokens are single-use: after one refresh the old refresh
token and the old access token stop working. So every token use goes
through :func:`usable_token`, which refreshes under a row lock on the
connection and saves the new pair in the same transaction.
"""

# Python imports
import logging
import os
from dataclasses import dataclass
from datetime import timedelta

# Django imports
from django.db import IntegrityError, transaction
from django.utils import timezone

# Module imports
from plane.agent.git_providers import http
from plane.agent.git_providers.base import ProviderError
from plane.agent.git_providers.github import api_headers, has_next_page, raise_for_status
from plane.agent.services import git_connection
from plane.db.models import (
    AgentGitAccount,
    AgentGitAccountState,
    AgentGitConnection,
    AgentGitConnectionStatus,
    AgentGitProvider,
    AgentGithubDeviceAuthorization,
    AgentGithubDeviceAuthorizationStatus,
    WorkspaceMember,
)
from plane.license.models import InstanceConfiguration
from plane.license.utils.encryption import decrypt_data

logger = logging.getLogger("plane.agent.services.github_connection")

PROVIDER = AgentGitProvider.GITHUB
GITHUB_BASE_URL = "https://github.com"
GITHUB_HOST = "github.com"
GITHUB_API_URL = "https://api.github.com"
DEVICE_CODE_URL = f"{GITHUB_BASE_URL}/login/device/code"
ACCESS_TOKEN_URL = f"{GITHUB_BASE_URL}/login/oauth/access_token"
DEVICE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"
# Refresh a little before the access token expires, so a token handed to a
# caller does not expire during its request.
REFRESH_MARGIN = timedelta(minutes=5)
ADMIN_ROLE = 20

GITHUB_APP_CLIENT_ID = "GITHUB_APP_CLIENT_ID"
GITHUB_APP_CLIENT_SECRET = "GITHUB_APP_CLIENT_SECRET"
GITHUB_APP_SLUG = "GITHUB_APP_SLUG"

_OAUTH_HEADERS = {"Accept": "application/json"}
_TERMINAL_STATUSES = {
    AgentGithubDeviceAuthorizationStatus.COMPLETED,
    AgentGithubDeviceAuthorizationStatus.CANCELLED,
    AgentGithubDeviceAuthorizationStatus.EXPIRED,
    AgentGithubDeviceAuthorizationStatus.DENIED,
}


@dataclass(frozen=True)
class AppCredentials:
    client_id: str
    client_secret: str
    slug: str


def _configured_value(key):
    """Instance configuration value when it is non-empty, else the environment value.

    ``get_configuration_value`` returns a stored empty string as-is, and
    ``configure_instance`` copies the environment only when the row is first
    created, so neither gives "configuration first, environment as fallback".
    """
    row = InstanceConfiguration.objects.filter(key=key).values("value", "is_encrypted").first()
    if row and row["value"]:
        value = decrypt_data(row["value"]) if row["is_encrypted"] else row["value"]
        if value:
            return value
    return os.environ.get(key, "")


def app_credentials():
    return AppCredentials(
        client_id=_configured_value(GITHUB_APP_CLIENT_ID),
        client_secret=_configured_value(GITHUB_APP_CLIENT_SECRET),
        slug=_configured_value(GITHUB_APP_SLUG),
    )


def install_url():
    slug = app_credentials().slug
    return f"{GITHUB_BASE_URL}/apps/{slug}/installations/new" if slug else ""


def _unexpected(response):
    return ProviderError("github_unexpected_response", PROVIDER, f"HTTP {response.status_code}", http_status=502)


def _require_client_id(credentials):
    if not credentials.client_id:
        raise ProviderError(
            "github_app_not_configured",
            PROVIDER,
            "Set the GitHub App client ID in the instance admin or in GITHUB_APP_CLIENT_ID.",
            http_status=400,
        )


# Device flow


def start_device_authorization(workspace, user, kind):
    credentials = app_credentials()
    _require_client_id(credentials)
    response = http.request(
        "POST",
        DEVICE_CODE_URL,
        provider=PROVIDER,
        headers=_OAUTH_HEADERS,
        data={"client_id": credentials.client_id},
    )
    body = response.json() or {}
    if body.get("error") == "device_flow_disabled":
        raise ProviderError(
            "device_flow_disabled",
            PROVIDER,
            "Enable Device Flow in the GitHub App settings.",
            http_status=400,
        )
    if response.status_code != 200 or not body.get("device_code") or not body.get("user_code"):
        raise _unexpected(response)

    authorization = AgentGithubDeviceAuthorization.objects.create(
        workspace=workspace,
        requested_by=user,
        kind=kind,
        device_code=git_connection.encrypt_secret(body["device_code"], PROVIDER),
        user_code=str(body["user_code"])[:32],
        verification_uri=str(body.get("verification_uri") or f"{GITHUB_BASE_URL}/login/device")[:2048],
        expires_at=timezone.now() + timedelta(seconds=int(body.get("expires_in") or 900)),
        interval=max(int(body["interval"] if body.get("interval") is not None else 5), 0),
    )
    logger.info("github device authorization %s started for workspace %s", authorization.id, workspace.id)
    return authorization


def poll_device_authorization(workspace, authorization_id, user):
    """Advance one device authorization by at most one GitHub call.

    The authorization row is locked, so two concurrent polls make one GitHub
    call; the second sees the terminal state and returns it unchanged.
    """
    with transaction.atomic():
        authorization = AgentGithubDeviceAuthorization.objects.select_for_update().get(
            pk=authorization_id, workspace=workspace
        )
        if authorization.status in _TERMINAL_STATUSES:
            return authorization

        now = timezone.now()
        if now >= authorization.expires_at:
            authorization.status = AgentGithubDeviceAuthorizationStatus.EXPIRED
            authorization.save(update_fields=["status", "updated_at"])
            return authorization
        if authorization.last_polled_at and (now - authorization.last_polled_at) < timedelta(
            seconds=authorization.interval
        ):
            return authorization

        authorization.last_polled_at = now
        device_code = git_connection.decrypt_secret(authorization.device_code)
        if not device_code:
            authorization.status = AgentGithubDeviceAuthorizationStatus.DENIED
            authorization.last_error = "device_code_unreadable"
            authorization.save()
            return authorization

        credentials = app_credentials()
        _require_client_id(credentials)
        response = http.request(
            "POST",
            ACCESS_TOKEN_URL,
            provider=PROVIDER,
            headers=_OAUTH_HEADERS,
            data={
                "client_id": credentials.client_id,
                "device_code": device_code,
                "grant_type": DEVICE_GRANT_TYPE,
            },
        )
        body = response.json() or {}
        error = body.get("error")
        if error == "authorization_pending":
            pass
        elif error == "slow_down":
            authorization.interval = int(body.get("interval") or authorization.interval + 5)
        elif error == "expired_token":
            authorization.status = AgentGithubDeviceAuthorizationStatus.EXPIRED
        elif error:
            authorization.status = AgentGithubDeviceAuthorizationStatus.DENIED
            authorization.last_error = str(error)[:64]
        elif response.status_code != 200 or not body.get("access_token"):
            raise _unexpected(response)
        else:
            connection = _store_connection(workspace, user, body)
            _sync_after_connect(connection, body["access_token"])
            authorization.status = AgentGithubDeviceAuthorizationStatus.COMPLETED
        authorization.save()

    logger.info("github device authorization %s is %s", authorization.id, authorization.status)
    return authorization


def cancel_device_authorization(workspace, authorization_id):
    with transaction.atomic():
        authorization = AgentGithubDeviceAuthorization.objects.select_for_update().get(
            pk=authorization_id, workspace=workspace
        )
        if authorization.status == AgentGithubDeviceAuthorizationStatus.PENDING:
            authorization.status = AgentGithubDeviceAuthorizationStatus.CANCELLED
            authorization.save(update_fields=["status", "updated_at"])
    return authorization


def _apply_token_body(connection, body):
    connection.access_token = git_connection.encrypt_secret(body["access_token"], PROVIDER)
    connection.refresh_token = git_connection.encrypt_secret(body.get("refresh_token") or "", PROVIDER)
    expires_in = body.get("expires_in")
    connection.token_expires_at = timezone.now() + timedelta(seconds=int(expires_in)) if expires_in else None


def _store_connection(workspace, user, token_body):
    access_token = token_body["access_token"]
    response = http.request("GET", f"{GITHUB_API_URL}/user", provider=PROVIDER, headers=api_headers(access_token))
    identity = response.json() or {}
    if response.status_code != 200 or not identity.get("login"):
        raise _unexpected(response)

    connection = AgentGitConnection.objects.select_for_update().filter(
        workspace=workspace, provider=PROVIDER
    ).first() or AgentGitConnection(workspace=workspace, provider=PROVIDER)
    _apply_token_body(connection, token_body)
    connection.base_url = GITHUB_BASE_URL
    connection.host = GITHUB_HOST
    connection.account_external_id = str(identity.get("id") or "")
    connection.account_login = str(identity["login"])[:255]
    connection.account_is_bot = False
    connection.token_scopes = [scope for scope in str(token_body.get("scope") or "").split(",") if scope]
    connection.connected_by = user
    connection.connected_at = timezone.now()
    connection.status = AgentGitConnectionStatus.CONNECTED
    connection.last_error = ""
    connection.warnings = []
    connection.save()
    logger.info("github connection %s connected for workspace %s", connection.id, workspace.id)
    return connection


# Installations

MAX_INSTALLATION_PAGES = 50


def _list_installations(token):
    installations = []
    for page in range(1, MAX_INSTALLATION_PAGES + 1):
        response = http.request(
            "GET",
            f"{GITHUB_API_URL}/user/installations",
            provider=PROVIDER,
            headers=api_headers(token),
            params={"per_page": 100, "page": page},
        )
        raise_for_status(response)
        installations.extend((response.json() or {}).get("installations") or [])
        if not has_next_page(response):
            break
    return installations


def sync_installations(connection, token):
    """Upsert the installations the token can see.

    New installations become ``candidate``. Existing rows get new names only:
    sync never attaches an installation and never clears ``detached``.
    """
    installations = _list_installations(token)
    for installation in installations:
        account_info = installation.get("account") or {}
        fields = {
            "login": str(account_info.get("login") or installation["id"])[:255],
            "account_type": str(account_info.get("type") or installation.get("target_type") or "")[:32],
            "repository_selection": str(installation.get("repository_selection") or "")[:16],
        }
        external_id = str(installation["id"])
        try:
            with transaction.atomic():
                account, created = AgentGitAccount.objects.get_or_create(
                    connection=connection,
                    external_id=external_id,
                    defaults={
                        **fields,
                        "workspace_id": connection.workspace_id,
                        "provider": PROVIDER,
                        "state": AgentGitAccountState.CANDIDATE,
                    },
                )
                if not created:
                    for name, value in fields.items():
                        setattr(account, name, value)
                    account.save(update_fields=[*fields.keys(), "updated_at"])
        except IntegrityError:
            # A concurrent sync created the same installation first.
            logger.info("installation %s was created by a concurrent sync", external_id)
    logger.info("github connection %s synced %s installations", connection.id, len(installations))
    return list(AgentGitAccount.objects.filter(connection=connection))


def _sync_after_connect(connection, token):
    """Sync installations after connect; a failure leaves the connection and the admin can sync again."""
    try:
        sync_installations(connection, token)
    except ProviderError as error:
        logger.warning("installation sync after connect failed for %s: %s", connection.id, error.code)


# Token use


def connected_admin_is_active(connection):
    return (
        bool(connection.connected_by_id)
        and WorkspaceMember.objects.filter(
            workspace_id=connection.workspace_id,
            member_id=connection.connected_by_id,
            role=ADMIN_ROLE,
            is_active=True,
        ).exists()
    )


def ensure_connected_admin(connection):
    """Set ``reconnect_required`` when the admin who connected GitHub is no longer an active Admin."""
    if connection.status != AgentGitConnectionStatus.CONNECTED or connected_admin_is_active(connection):
        return
    with transaction.atomic():
        locked = AgentGitConnection.objects.select_for_update().get(pk=connection.pk)
        if locked.status == AgentGitConnectionStatus.CONNECTED and not connected_admin_is_active(locked):
            git_connection.mark_reconnect_required(locked, "connected_admin_lost")
    connection.refresh_from_db()


def _refresh_locked(connection):
    """Refresh the token pair of a locked connection. Returns ``(token, error)``."""
    refresh_token = git_connection.decrypt_secret(connection.refresh_token)
    if not refresh_token:
        return None, git_connection.mark_reconnect_required(connection, "github_refresh_failed")
    credentials = app_credentials()
    _require_client_id(credentials)
    response = http.request(
        "POST",
        ACCESS_TOKEN_URL,
        provider=PROVIDER,
        headers=_OAUTH_HEADERS,
        data={
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    if response.status_code >= 500:
        raise _unexpected(response)
    body = response.json() or {}
    if body.get("error") or not body.get("access_token"):
        return None, git_connection.mark_reconnect_required(connection, "github_refresh_failed")
    _apply_token_body(connection, body)
    connection.save(update_fields=["access_token", "refresh_token", "token_expires_at", "updated_at"])
    logger.info("github connection %s refreshed its token", connection.id)
    return body["access_token"], None


def usable_token(connection_id):
    """Return a valid access token for the connection or raise :class:`ProviderError`.

    Holds a row lock for the whole check, so concurrent callers refresh at
    most once. A connection whose connecting admin is no longer an active
    Admin of the workspace is set to ``reconnect_required`` and its token is
    not used.
    """
    error = None
    token = None
    with transaction.atomic():
        connection = AgentGitConnection.objects.select_for_update().get(pk=connection_id)
        blocked = git_connection.status_error(connection)
        if blocked:
            raise blocked
        if not connected_admin_is_active(connection):
            error = git_connection.mark_reconnect_required(connection, "connected_admin_lost")
        else:
            token = git_connection.decrypt_secret(connection.access_token)
            if not token:
                error = git_connection.mark_reconnect_required(connection, "token_decrypt_failed")
            elif connection.token_expires_at and connection.token_expires_at <= timezone.now() + REFRESH_MARGIN:
                token, error = _refresh_locked(connection)
    # Raise after the block, so the reconnect_required state above is committed.
    if error:
        raise error
    return token
