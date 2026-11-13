# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Workspace Agent settings. The bot user and Worker identity are never serialized."""

# Python imports
import re

# Django imports
from django.utils import timezone

# Third party imports
from rest_framework import serializers

# Module imports
from plane.agent.services.agent_settings import HANDLE_TAKEN_MESSAGE, connection_view, is_available_for_mentions
from plane.db.models import Agent

# A mention handle: a letter, then letters, digits, "-" or "_"; 32 characters at most.
HANDLE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")


def agent_connection_data(connection, now):
    state, missing_action = connection_view(connection, now)
    return {
        "state": state,
        "probe_generation": connection.probe_generation,
        "probe_requested_at": connection.probe_requested_at,
        "harness_version": connection.harness_version,
        "location": connection.location,
        "models": connection.reported_models,
        "capabilities": connection.capabilities,
        "checks": connection.checks,
        "missing_action": missing_action,
        "failure_hint": connection.failure_hint,
        "verified_at": connection.verified_at,
    }


class AgentSerializer(serializers.Serializer):
    def to_representation(self, agent):
        now = timezone.now()
        return {
            "id": str(agent.id),
            "harness": agent.harness,
            "name": agent.name,
            "handle": agent.handle,
            "instructions": agent.instructions,
            "mentionable": agent.mentionable,
            "selected_model": agent.selected_model,
            "available_for_mentions": is_available_for_mentions(agent, now),
            "connection": agent_connection_data(agent.connection, now),
        }


def reject_control_characters(value):
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise serializers.ValidationError("Use one line of text without control characters.", code="invalid")
    return value


class AgentUpdateSerializer(serializers.Serializer):
    """Fields an admin can change. Each story of the settings page adds its field here."""

    name = serializers.CharField(max_length=64, trim_whitespace=True, validators=[reject_control_characters])
    handle = serializers.CharField(trim_whitespace=True)

    def validate_handle(self, value):
        handle = value.removeprefix("@")
        if not HANDLE_PATTERN.fullmatch(handle):
            raise serializers.ValidationError(
                "Use 1 to 32 letters, digits, - or _, starting with a letter.", code="invalid"
            )
        agent = self.context["agent"]
        # Case-insensitive, like the database constraint; the constraint still decides a concurrent change.
        if Agent.objects.filter(workspace_id=agent.workspace_id, handle__iexact=handle).exclude(pk=agent.pk).exists():
            raise serializers.ValidationError(HANDLE_TAKEN_MESSAGE, code="taken")
        return handle


def error_codes(errors):
    """First error code of each field, so the web app can show a translated message."""
    return {field: getattr(messages[0], "code", "invalid") for field, messages in errors.items() if messages}
