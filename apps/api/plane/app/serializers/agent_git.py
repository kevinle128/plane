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
from plane.db.models import AgentGitConnection, AgentGithubDeviceAuthorization

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
            "updated_at",
        ]
        read_only_fields = fields

    def get_has_ca_bundle(self, obj):
        return bool(obj.ca_bundle)


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
