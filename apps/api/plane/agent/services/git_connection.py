# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Shared rules for Git provider connections (both providers).

``encrypt_data`` and ``decrypt_data`` return ``""`` on any error. The helpers
here turn that into an explicit failure, so a connection never becomes
``connected`` with an empty token and no provider call is made with one.
"""

# Python imports
import logging
import uuid

# Module imports
from plane.agent.git_providers.base import ProviderError
from plane.agent.services.branch_name import is_valid_ref_name
from plane.db.models import (
    AgentGitAccountState,
    AgentGitConnection,
    AgentGitConnectionStatus,
    AgentGitPolicy,
    AgentGitRepository,
    ProjectRepositoryBinding,
)
from plane.license.utils.encryption import decrypt_data, encrypt_data

logger = logging.getLogger("plane.agent.services.git_connection")


def encrypt_secret(value, provider):
    """Encrypt ``value`` or raise when encryption produced no ciphertext."""
    if not value:
        return ""
    ciphertext = encrypt_data(value)
    if not ciphertext:
        logger.error("token encryption failed for provider %s", provider)
        raise ProviderError("token_encryption_failed", provider, http_status=500)
    return ciphertext


def decrypt_secret(ciphertext):
    """Return the plaintext, ``""`` for an empty value, or ``None`` when a stored value cannot be decrypted."""
    if not ciphertext:
        return ""
    plaintext = decrypt_data(ciphertext)
    return plaintext or None


def status_error(connection):
    """Return the neutral error for a connection that cannot be used, else ``None``."""
    if connection is None or connection.status == AgentGitConnectionStatus.DISCONNECTED:
        provider = connection.provider if connection else ""
        return ProviderError("provider_disconnected", provider, http_status=409)
    if connection.status == AgentGitConnectionStatus.RECONNECT_REQUIRED:
        return ProviderError("provider_reconnect_required", connection.provider, connection.last_error, http_status=409)
    return None


def mark_reconnect_required(connection, reason):
    """Persist ``reconnect_required`` with ``reason`` on ``connection`` (caller holds the row)."""
    connection.status = AgentGitConnectionStatus.RECONNECT_REQUIRED
    connection.last_error = reason
    connection.save(update_fields=["status", "last_error", "updated_at"])
    logger.warning("connection %s set to reconnect_required: %s", connection.id, reason)
    return ProviderError("provider_reconnect_required", connection.provider, reason, http_status=409)


def clear_tokens(connection):
    connection.access_token = ""
    connection.refresh_token = ""
    connection.token_expires_at = None


def get_connection(workspace_id, provider):
    return AgentGitConnection.objects.filter(workspace_id=workspace_id, provider=provider).first()


# Repository binding


def binding_availability(binding):
    """Whether new agent work may use ``binding``.

    Usable only when its account is attached, its connection is connected,
    and the binding host equals the connection host. The binding row itself
    is kept for audit in every other case.
    """
    account = binding.account
    if account is None or account.deleted_at is not None or account.state != AgentGitAccountState.ATTACHED:
        return {"available": False, "reason": "repository_unavailable"}
    blocked = status_error(account.connection)
    if blocked is not None:
        return {"available": False, "reason": blocked.code}
    if account.connection.host != binding.host:
        return {"available": False, "reason": "repository_unavailable"}
    return {"available": True, "reason": ""}


def resolve_binding_request(workspace, repository):
    """Validate the ``repository`` part of a project create request.

    Only the catalog row ID and an optional ``base_ref`` are read. Provider,
    host, IDs and URLs always come from this workspace's catalog row, so
    other client-supplied fields are ignored. Returns the binding field values.
    """
    if not isinstance(repository, dict):
        raise ProviderError("invalid_repository", "", http_status=400)
    try:
        repository_id = uuid.UUID(str(repository.get("repository_id")))
    except ValueError:
        raise ProviderError("invalid_repository", "", http_status=400)

    row = (
        AgentGitRepository.objects.select_related("account", "account__connection")
        .filter(pk=repository_id, workspace=workspace)
        .first()
    )
    if row is None:
        raise ProviderError("repository_not_found", "", http_status=404)
    blocked = status_error(row.account.connection)
    if blocked is not None:
        blocked.detail = ""
        raise blocked
    if row.account.state != AgentGitAccountState.ATTACHED:
        raise ProviderError("repository_unavailable", row.provider, http_status=409)

    base_ref = repository.get("base_ref") or row.default_branch
    if not is_valid_ref_name(base_ref):
        raise ProviderError("invalid_base_ref", row.provider, http_status=400)

    connection = row.account.connection
    if ProjectRepositoryBinding.objects.filter(
        workspace=workspace, provider=row.provider, host=connection.host, external_repository_id=row.external_id
    ).exists():
        raise ProviderError("repository_already_bound", row.provider, http_status=409)
    return {
        "workspace": workspace,
        "account": row.account,
        "provider": row.provider,
        "host": connection.host,
        "external_repository_id": row.external_id,
        "full_name": row.full_name,
        "clone_url": row.clone_url,
        "web_url": row.web_url,
        "default_branch": row.default_branch,
        "base_ref": base_ref,
    }


def binding_summary(binding):
    """Read-only view of a binding for API responses (no secrets exist on it)."""
    return {
        "id": str(binding.id),
        "provider": binding.provider,
        "host": binding.host,
        "external_repository_id": binding.external_repository_id,
        "full_name": binding.full_name,
        "web_url": binding.web_url,
        "default_branch": binding.default_branch,
        "base_ref": binding.base_ref,
        **binding_availability(binding),
    }


# Change-request policy

POLICY_FIELDS = ("open_as_draft", "mirror_conclusions", "branch_format")


def change_request_policy(workspace_id, provider):
    """The policy values that agent delivery reads; defaults when the workspace saved none."""
    policy = AgentGitPolicy.objects.filter(workspace_id=workspace_id, provider=provider).first()
    if policy is None:
        policy = AgentGitPolicy(workspace_id=workspace_id, provider=provider)
    return {"provider": provider, **{name: getattr(policy, name) for name in POLICY_FIELDS}}
