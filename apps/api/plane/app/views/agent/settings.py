# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Workspace Agent settings: members read, admins change and connect."""

# Django imports
from django.http import Http404

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.agent.services import harness_probe
from plane.agent.services.agent_settings import ensure_workspace_agent, ensure_workspace_agents
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers.agent import AgentSerializer
from plane.app.views.base import BaseAPIView
from plane.db.models import AgentHarness, Workspace


def agent_for(slug, harness):
    """The Agent of ``harness`` in the workspace; an unknown Harness is a 404."""
    if harness not in AgentHarness.values:
        raise Http404
    return ensure_workspace_agent(Workspace.objects.get(slug=slug), harness)


def agent_response(agent, response_status=status.HTTP_200_OK):
    agent.refresh_from_db()
    agent.connection.refresh_from_db()
    return Response(AgentSerializer(agent).data, status=response_status)


class AgentsEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        agents = ensure_workspace_agents(Workspace.objects.get(slug=slug))
        return Response(AgentSerializer(agents, many=True).data, status=status.HTTP_200_OK)


class AgentDetailEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug, harness):
        return Response(AgentSerializer(agent_for(slug, harness)).data, status=status.HTTP_200_OK)


class AgentConnectEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug, harness):
        agent = agent_for(slug, harness)
        try:
            harness_probe.request_probe(agent)
        except harness_probe.ProbeConflict as conflict:
            return Response({"error": conflict.code}, status=status.HTTP_409_CONFLICT)
        return agent_response(agent)


class AgentDisconnectEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug, harness):
        agent = agent_for(slug, harness)
        harness_probe.disconnect(agent)
        return agent_response(agent)
