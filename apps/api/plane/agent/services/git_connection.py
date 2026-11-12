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

# Module imports
from plane.agent.git_providers.base import ProviderError
from plane.db.models import AgentGitConnection, AgentGitConnectionStatus
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
