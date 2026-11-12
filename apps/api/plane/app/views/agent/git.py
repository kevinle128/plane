# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Workspace endpoints for Git provider connections (GitHub and GitLab).

Members read; only workspace admins change anything. Views stay thin: the
rules live in ``plane.agent.services``.
"""

# Python imports
import logging

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.agent.git_providers.base import ProviderError
from plane.agent.services import github_connection
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers.agent_git import (
    AgentGitConnectionSerializer,
    AgentGithubDeviceAuthorizationSerializer,
)
from plane.app.views.base import BaseAPIView
from plane.db.models import (
    AgentGitConnection,
    AgentGitProvider,
    AgentGithubDeviceAuthorizationKind,
    Workspace,
)

logger = logging.getLogger("plane.app.views.agent")


def provider_error_response(error):
    return Response(error.as_response_body(), status=error.http_status)


class AgentGitConnectionsEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        connections = list(AgentGitConnection.objects.filter(workspace=workspace).select_related("connected_by"))
        for connection in connections:
            if connection.provider == AgentGitProvider.GITHUB:
                github_connection.ensure_connected_admin(connection)
        return Response(AgentGitConnectionSerializer(connections, many=True).data, status=status.HTTP_200_OK)


class AgentGithubDeviceAuthorizationEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        kind = request.data.get("kind", AgentGithubDeviceAuthorizationKind.USER)
        if kind not in AgentGithubDeviceAuthorizationKind.values:
            return Response({"error": "invalid_kind"}, status=status.HTTP_400_BAD_REQUEST)
        workspace = Workspace.objects.get(slug=slug)
        try:
            authorization = github_connection.start_device_authorization(workspace, request.user, kind)
        except ProviderError as error:
            return provider_error_response(error)
        return Response(
            AgentGithubDeviceAuthorizationSerializer(authorization).data,
            status=status.HTTP_201_CREATED,
        )


class AgentGithubDeviceAuthorizationPollEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug, pk):
        workspace = Workspace.objects.get(slug=slug)
        try:
            authorization = github_connection.poll_device_authorization(workspace, pk, request.user)
        except ProviderError as error:
            return provider_error_response(error)
        return Response(AgentGithubDeviceAuthorizationSerializer(authorization).data, status=status.HTTP_200_OK)


class AgentGithubDeviceAuthorizationCancelEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug, pk):
        workspace = Workspace.objects.get(slug=slug)
        authorization = github_connection.cancel_device_authorization(workspace, pk)
        return Response(AgentGithubDeviceAuthorizationSerializer(authorization).data, status=status.HTTP_200_OK)
