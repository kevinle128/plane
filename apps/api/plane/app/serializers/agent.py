# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Workspace Agent settings. The bot user and Worker identity are never serialized."""

# Django imports
from django.utils import timezone

# Third party imports
from rest_framework import serializers

# Module imports
from plane.agent.services.agent_settings import connection_view, is_available_for_mentions


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
