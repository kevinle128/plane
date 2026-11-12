# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Self-hosted GitLab connection with a pasted Group Access Token.

A workspace admin chooses the server, so every response is untrusted. The
connect checks run in a fixed order and stop at the first failure; nothing
is stored unless all of them pass. ``/personal_access_tokens/self`` runs
before ``/version`` because it accepts a token of any scope, while
``/version`` refuses a ``write_repository``-only token with 403, which
would hide the missing-scope reason.
"""

# Python imports
import datetime
import logging
import ssl
from types import SimpleNamespace
from urllib.parse import quote, urlsplit

# Django imports
from django.conf import settings
from django.db import transaction
from django.utils import timezone

# Module imports
from plane.agent.git_providers import http
from plane.agent.git_providers.base import ProviderError
from plane.agent.git_providers.gitlab import GitlabClient, parse_gitlab_version
from plane.agent.services import git_connection
from plane.db.models import (
    AgentGitAccount,
    AgentGitAccountState,
    AgentGitConnection,
    AgentGitConnectionStatus,
    AgentGitProvider,
)

logger = logging.getLogger("plane.agent.services.gitlab_connection")

PROVIDER = AgentGitProvider.GITLAB
MINIMUM_VERSION = (15, 5)
REQUIRED_SCOPES = ("api", "write_repository")
CONNECT_BUDGET_SECONDS = 30
MAX_CA_BUNDLE_BYTES = 256 * 1024
DEVELOPER_ACCESS_LEVEL = 30
ACCESS_LEVEL_NAMES = {
    0: "No access",
    5: "Minimal access",
    10: "Guest",
    15: "Planner",
    20: "Reporter",
    30: "Developer",
    40: "Maintainer",
    50: "Owner",
}
NOT_BOT_WARNING = "gitlab_token_not_bot"


def _error(code, detail="", http_status=400):
    return ProviderError(code, PROVIDER, detail, http_status=http_status)


def _unexpected(response):
    return _error("gitlab_unexpected_response", f"HTTP {response.status_code}", http_status=502)


def normalize_base_url(raw):
    """Return ``(base_url, host)``: https only, no user info, query or fragment, no trailing ``/``."""
    try:
        parts = urlsplit(str(raw).strip())
        port = parts.port
    except ValueError:
        raise _error("gitlab_url_invalid")
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
    ):
        raise _error("gitlab_url_invalid")
    host = parts.hostname.rstrip(".").lower()
    netloc = f"[{host}]" if ":" in host else host
    if port:
        netloc = f"{netloc}:{port}"
    return f"https://{netloc}{parts.path.rstrip('/')}", host


def _matches(host, domain):
    return host == domain or host.endswith(f".{domain}")


def _check_host_allowed(host, request_host):
    """Refuse the Plane host itself always, and operator-disallowed domains unless allowlisted.

    ``AGENT_GIT_ALLOWED_HOSTS`` lifts ``WEBHOOK_DISALLOWED_DOMAINS`` only; it
    never lets a workspace point the connection back at Plane.
    """
    plane_host = (request_host or "").split(":")[0].rstrip(".").lower()
    if plane_host and _matches(host, plane_host):
        raise _error("gitlab_url_not_allowed_or_unresolved")
    if host in settings.AGENT_GIT_ALLOWED_HOSTS:
        return
    if any(_matches(host, domain) for domain in settings.WEBHOOK_DISALLOWED_DOMAINS):
        raise _error("gitlab_url_not_allowed_or_unresolved")


def _validate_ca_bundle(pem):
    if not pem:
        return None
    if not isinstance(pem, str) or len(pem.encode()) > MAX_CA_BUNDLE_BYTES:
        raise _error("gitlab_ca_invalid")
    try:
        ssl.create_default_context(cadata=pem)
    except (ssl.SSLError, ValueError, TypeError):
        raise _error("gitlab_ca_invalid")
    return pem


def _expiry(expires_at):
    """Return the expiry as a UTC datetime (start of that day), or ``None`` for a token that never expires."""
    if not expires_at:
        return None
    try:
        day = datetime.date.fromisoformat(str(expires_at)[:10])
    except ValueError:
        raise _error("gitlab_unexpected_response", "expires_at", http_status=502)
    return datetime.datetime.combine(day, datetime.time.min, tzinfo=datetime.timezone.utc)


def _explain_missing_token_endpoint(client, deadline):
    """``/personal_access_tokens/self`` gave 404: older than 15.5, or not GitLab at all."""
    response = client.get("version", deadline=deadline)
    body = response.json()
    if response.status_code == 404 or not isinstance(body, dict):
        raise _error("gitlab_not_gitlab")
    if response.status_code != 200:
        raise _unexpected(response)
    version = parse_gitlab_version(body.get("version"))
    if version is None:
        raise _error("gitlab_not_gitlab")
    if version < MINIMUM_VERSION:
        raise _error("gitlab_version_unsupported", f"found {body['version']}, minimum 15.5")
    raise _unexpected(SimpleNamespace(status_code=404))


def _check_token(client, deadline):
    response = client.get("personal_access_tokens/self", deadline=deadline)
    if response.status_code == 401:
        raise _error("gitlab_token_invalid")
    if response.status_code == 404:
        _explain_missing_token_endpoint(client, deadline)
    if response.status_code != 200:
        raise _unexpected(response)
    token = response.json()
    if not isinstance(token, dict):
        raise _error("gitlab_not_gitlab")
    expires_at = _expiry(token.get("expires_at"))
    if not token.get("active") or token.get("revoked") or (expires_at and expires_at <= timezone.now()):
        raise _error("gitlab_token_invalid")
    scopes = token.get("scopes") or []
    missing = [scope for scope in REQUIRED_SCOPES if scope not in scopes]
    if missing:
        raise _error("gitlab_scope_missing", ", ".join(missing))
    return token, expires_at


def _check_version(client, deadline):
    response = client.get("version", deadline=deadline)
    if response.status_code == 401:
        raise _error("gitlab_token_invalid")
    body = response.json()
    if response.status_code == 404 or not isinstance(body, dict):
        raise _error("gitlab_not_gitlab")
    if response.status_code != 200:
        raise _unexpected(response)
    version = parse_gitlab_version(body.get("version"))
    if version is None:
        raise _error("gitlab_not_gitlab")
    if version < MINIMUM_VERSION:
        raise _error("gitlab_version_unsupported", f"found {body['version']}, minimum 15.5")
    return str(body["version"])[:64]


def _check_json(response, not_found_code=None):
    if response.status_code == 401:
        raise _error("gitlab_token_invalid")
    if not_found_code and response.status_code in (403, 404):
        raise _error(not_found_code)
    if response.status_code != 200:
        raise _unexpected(response)
    body = response.json()
    if not isinstance(body, dict) or "id" not in body:
        raise _error("gitlab_unexpected_response", "body", http_status=502)
    return body


def _check_member(client, group_id, user_id, deadline):
    response = client.get(f"groups/{group_id}/members/all/{user_id}", deadline=deadline)
    if response.status_code == 404:
        raise _error("gitlab_role_too_low", "none")
    member = _check_json(response)
    level = int(member.get("access_level") or 0)
    if level < DEVELOPER_ACCESS_LEVEL:
        raise _error("gitlab_role_too_low", ACCESS_LEVEL_NAMES.get(level, str(level)))


def _ensure_same_base_url(connection, base_url):
    if (
        connection is not None
        and connection.status != AgentGitConnectionStatus.DISCONNECTED
        and connection.base_url != base_url
    ):
        raise _error("gitlab_disconnect_first", http_status=409)


def connect(workspace, user, *, base_url, group_path, token, ca_bundle, request_host):
    """Run the connect checks and store the connection and its single attached group."""
    base_url, host = normalize_base_url(base_url)
    _check_host_allowed(host, request_host)
    ca_bundle = _validate_ca_bundle(ca_bundle)
    group_path = group_path.strip().strip("/")
    if not group_path:
        raise _error("invalid_request")
    _ensure_same_base_url(git_connection.get_connection(workspace.id, PROVIDER), base_url)

    deadline = http.new_deadline(CONNECT_BUDGET_SECONDS)
    client = GitlabClient(SimpleNamespace(base_url=base_url, host=host, ca_bundle=ca_bundle), token)
    token_info, expires_at = _check_token(client, deadline)
    server_version = _check_version(client, deadline)
    token_user = _check_json(client.get("user", deadline=deadline))
    group = _check_json(client.get(f"groups/{quote(group_path, safe='')}", deadline=deadline), "gitlab_group_not_found")
    _check_member(client, group["id"], token_user["id"], deadline)

    with transaction.atomic():
        connection = (
            AgentGitConnection.objects.select_for_update().filter(workspace=workspace, provider=PROVIDER).first()
        )
        _ensure_same_base_url(connection, base_url)
        connection = connection or AgentGitConnection(workspace=workspace, provider=PROVIDER)
        is_bot = bool(token_user.get("bot"))
        connection.base_url = base_url
        connection.host = host
        connection.ca_bundle = ca_bundle
        connection.access_token = git_connection.encrypt_secret(token, PROVIDER)
        connection.refresh_token = ""
        connection.token_expires_at = expires_at
        connection.token_name = str(token_info.get("name") or "")[:255]
        connection.token_scopes = [str(scope) for scope in token_info.get("scopes") or []]
        connection.server_version = server_version
        connection.account_external_id = str(token_user["id"])
        connection.account_login = str(token_user.get("username") or "")[:255]
        connection.account_is_bot = is_bot
        connection.connected_by = user
        connection.connected_at = timezone.now()
        connection.status = AgentGitConnectionStatus.CONNECTED
        connection.last_error = ""
        connection.warnings = [] if is_bot else [NOT_BOT_WARNING]
        connection.save()
        _attach_single_group(connection, group, user)
    logger.info("gitlab connection %s connected for workspace %s", connection.id, workspace.id)
    return connection


def _attach_single_group(connection, group, user):
    """One token is bound to one group: attach it and detach every other group of the connection."""
    now = timezone.now()
    account, _ = AgentGitAccount.objects.get_or_create(
        connection=connection,
        external_id=str(group["id"]),
        defaults={"workspace_id": connection.workspace_id, "provider": PROVIDER, "login": group.get("full_path", "")},
    )
    account.login = str(group.get("full_path") or group.get("path") or group["id"])[:255]
    account.account_type = "Group"
    account.state = AgentGitAccountState.ATTACHED
    account.attached_by = user
    account.attached_at = now
    account.removed_at = None
    account.save()
    AgentGitAccount.objects.filter(connection=connection).exclude(pk=account.pk).exclude(
        state=AgentGitAccountState.DETACHED
    ).update(state=AgentGitAccountState.DETACHED, removed_at=now)


def usable_token(connection_id):
    """Return the stored GitLab token, or raise when the connection cannot be used.

    An expired token or a stored value that cannot be decrypted sets
    ``reconnect_required`` before any provider call.
    """
    error = None
    with transaction.atomic():
        connection = AgentGitConnection.objects.select_for_update().get(pk=connection_id)
        blocked = git_connection.status_error(connection)
        if blocked:
            raise blocked
        token = git_connection.decrypt_secret(connection.access_token)
        if not token:
            error = git_connection.mark_reconnect_required(connection, "token_decrypt_failed")
        elif connection.token_expires_at and connection.token_expires_at <= timezone.now():
            error = git_connection.mark_reconnect_required(connection, "gitlab_token_invalid")
    if error:
        raise error
    return token


def access_token_settings_url(connection):
    """Group page where an admin revokes the Group Access Token."""
    group = (
        AgentGitAccount.objects.filter(connection=connection, state=AgentGitAccountState.ATTACHED)
        .values_list("login", flat=True)
        .first()
    )
    return f"{connection.base_url}/groups/{group}/-/settings/access_tokens" if group else ""


def disconnect(workspace):
    """Forget the stored GitLab token without any GitLab call. Returns ``(connection, revoke_url)``.

    Plane does not revoke the Group Access Token; the admin revokes it in the
    group settings. Bindings stay for history and become unavailable.
    """
    with transaction.atomic():
        connection = (
            AgentGitConnection.objects.select_for_update().filter(workspace=workspace, provider=PROVIDER).first()
        )
        if connection is None:
            raise _error("provider_disconnected", http_status=404)
        revoke_url = access_token_settings_url(connection)
        git_connection.clear_tokens(connection)
        connection.status = AgentGitConnectionStatus.DISCONNECTED
        connection.last_error = ""
        connection.save(
            update_fields=["access_token", "refresh_token", "token_expires_at", "status", "last_error", "updated_at"]
        )
    logger.info("gitlab connection %s disconnected without a provider call", connection.id)
    return connection, revoke_url
