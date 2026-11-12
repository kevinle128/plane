# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Serializers for Git provider connections.

Every serializer lists its fields explicitly. Token columns (access_token,
refresh_token, device_code) are never part of a field list, and
``to_representation`` removes them again as a second guard.
"""

# Third party imports
from rest_framework import serializers

# Module imports
from plane.app.serializers.base import BaseSerializer
from plane.app.serializers.user import UserLiteSerializer
from plane.db.models import (
    AgentGitAccount,
    AgentGitConnection,
    AgentGitPolicy,
    AgentGitProvider,
    AgentGitRepository,
    AgentGithubDeviceAuthorization,
)

SECRET_FIELDS = ("access_token", "refresh_token", "device_code")


class _NoSecretsMixin:
    def to_representation(self, instance):
        data = super().to_representation(instance)
        for name in SECRET_FIELDS:
            data.pop(name, None)
        return data


class AgentGitConnectionSerializer(_NoSecretsMixin, BaseSerializer):
    connected_by_detail = UserLiteSerializer(source="connected_by", read_only=True)
    has_ca_bundle = serializers.SerializerMethodField()
    install_url = serializers.SerializerMethodField()

    class Meta:
        model = AgentGitConnection
        fields = [
            "id",
            "provider",
            "base_url",
            "host",
            "status",
            "last_error",
            "warnings",
            "account_external_id",
            "account_login",
            "account_is_bot",
            "token_name",
            "token_scopes",
            "token_expires_at",
            "server_version",
            "connected_by",
            "connected_by_detail",
            "connected_at",
            "worker_last_error",
            "worker_checked_at",
            "has_ca_bundle",
            "install_url",
            "updated_at",
        ]
        read_only_fields = fields

    def get_has_ca_bundle(self, obj):
        return bool(obj.ca_bundle)

    def get_install_url(self, obj):
        if obj.provider != AgentGitProvider.GITHUB:
            return ""
        from plane.agent.services.github_connection import install_url

        return install_url()


class AgentGithubDeviceAuthorizationSerializer(_NoSecretsMixin, BaseSerializer):
    class Meta:
        model = AgentGithubDeviceAuthorization
        fields = [
            "id",
            "kind",
            "status",
            "user_code",
            "verification_uri",
            "expires_at",
            "interval",
            "last_error",
        ]
        read_only_fields = fields


class AgentGitAccountSerializer(BaseSerializer):
    class Meta:
        model = AgentGitAccount
        fields = [
            "id",
            "provider",
            "external_id",
            "login",
            "account_type",
            "repository_selection",
            "state",
            "attached_by",
            "attached_at",
            "removed_at",
            "catalog_refreshed_at",
            "catalog_error",
        ]
        read_only_fields = fields


class AgentGitRepositorySerializer(BaseSerializer):
    """A catalog row as the repository picker sees it."""

    account_id = serializers.UUIDField(read_only=True)
    account_login = serializers.CharField(source="account.login", read_only=True)
    account_type = serializers.CharField(source="account.account_type", read_only=True)
    host = serializers.CharField(source="account.connection.host", read_only=True)

    class Meta:
        model = AgentGitRepository
        fields = [
            "id",
            "provider",
            "host",
            "account_id",
            "account_login",
            "account_type",
            "external_id",
            "full_name",
            "owner_login",
            "private",
            "default_branch",
            "web_url",
        ]
        read_only_fields = fields


class AgentGitPolicySerializer(serializers.ModelSerializer):
    """Writable policy fields; ``provider`` comes from the URL."""

    class Meta:
        model = AgentGitPolicy
        fields = ["open_as_draft", "mirror_conclusions"]
