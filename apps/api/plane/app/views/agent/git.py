# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Workspace endpoints for Git provider connections (GitHub and GitLab).

Members read; only workspace admins change anything. Views stay thin: the
rules live in ``plane.agent.services``.
"""

# Python imports
import logging

# Django imports
from django.db import DatabaseError, transaction
from django.http import Http404
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.agent.git_providers.base import ProviderError
from plane.agent.services import git_connection, github_connection
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers.agent_git import (
    AgentGitAccountSerializer,
    AgentGitConnectionSerializer,
    AgentGitRepositorySerializer,
    AgentGithubDeviceAuthorizationSerializer,
)
from plane.app.views.base import BaseAPIView
from plane.bgtasks.agent_git_catalog_task import refresh_agent_git_catalog
from plane.db.models import (
    AgentGitAccount,
    AgentGitAccountState,
    AgentGitConnection,
    AgentGitConnectionStatus,
    AgentGitProvider,
    AgentGitRepository,
    AgentGithubDeviceAuthorizationKind,
    Workspace,
)

logger = logging.getLogger("plane.app.views.agent")


REPOSITORY_PAGE_SIZE = 100


def provider_error_response(error):
    return Response(error.as_response_body(), status=error.http_status)


def require_provider(provider):
    """Only ``github`` and ``gitlab`` are valid path segments; anything else is a 404."""
    if provider not in AgentGitProvider.values:
        raise Http404
    return provider


def enqueue_catalog_refresh(connection_id):
    # The task gets the connection ID only; it reads the token itself.
    connection_id = str(connection_id)
    transaction.on_commit(lambda: refresh_agent_git_catalog.delay(connection_id))


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


class AgentGitAccountsEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug, provider):
        require_provider(provider)
        accounts = AgentGitAccount.objects.filter(workspace__slug=slug, provider=provider)
        return Response(AgentGitAccountSerializer(accounts, many=True).data, status=status.HTTP_200_OK)


class AgentGithubAccountsSyncEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        connection = git_connection.get_connection(workspace.id, AgentGitProvider.GITHUB)
        try:
            blocked = git_connection.status_error(connection)
            if blocked:
                blocked.provider = AgentGitProvider.GITHUB
                raise blocked
            token = github_connection.usable_token(connection.id)
            accounts = github_connection.sync_installations(connection, token)
        except ProviderError as error:
            return provider_error_response(error)
        if any(account.state == AgentGitAccountState.ATTACHED for account in accounts):
            enqueue_catalog_refresh(connection.id)
        return Response(AgentGitAccountSerializer(accounts, many=True).data, status=status.HTTP_200_OK)


class AgentGitAccountAttachEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug, provider, pk):
        require_provider(provider)
        with transaction.atomic():
            account = AgentGitAccount.objects.select_for_update().get(pk=pk, workspace__slug=slug, provider=provider)
            account.state = AgentGitAccountState.ATTACHED
            account.attached_by = request.user
            account.attached_at = timezone.now()
            account.removed_at = None
            account.save(update_fields=["state", "attached_by", "attached_at", "removed_at", "updated_at"])
            enqueue_catalog_refresh(account.connection_id)
        return Response(AgentGitAccountSerializer(account).data, status=status.HTTP_200_OK)


class AgentGitAccountDetailEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def delete(self, request, slug, provider, pk):
        """Remove one GitHub installation from Plane (a Plane-side detach).

        Uninstalling at GitHub needs the App private key, which Plane does not
        hold, so the response links to the GitHub installation settings.
        """
        require_provider(provider)
        if provider != AgentGitProvider.GITHUB:
            return Response(
                {"error": "account_remove_not_supported", "provider": provider, "detail": "disconnect"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        account = AgentGitAccount.objects.get(pk=pk, workspace__slug=slug, provider=provider)
        try:
            with transaction.atomic():
                account = AgentGitAccount.objects.select_for_update().get(pk=account.pk)
                account.state = AgentGitAccountState.DETACHED
                account.removed_at = timezone.now()
                account.save(update_fields=["state", "removed_at", "updated_at"])
        except DatabaseError:
            logger.exception("removing account %s failed", pk)
            return Response(
                {"error": "account_remove_failed", "provider": provider},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        data = AgentGitAccountSerializer(account).data
        data["settings_url"] = github_connection.installation_settings_url(account)
        return Response(data, status=status.HTTP_200_OK)


class AgentGitRepositoriesEndpoint(BaseAPIView):
    """Repositories of attached accounts on connected connections (workspace Admins and Members)."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        queryset = AgentGitRepository.objects.filter(
            workspace__slug=slug,
            account__state=AgentGitAccountState.ATTACHED,
            account__deleted_at__isnull=True,
            account__connection__status=AgentGitConnectionStatus.CONNECTED,
            account__connection__deleted_at__isnull=True,
        ).select_related("account", "account__connection")
        provider = request.query_params.get("provider")
        if provider:
            queryset = queryset.filter(provider=provider)
        owner = request.query_params.get("owner")
        if owner:
            queryset = queryset.filter(owner_login=owner)
        search = (request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(full_name__icontains=search)
        try:
            offset = max(int(request.query_params.get("cursor") or 0), 0)
        except ValueError:
            return Response({"error": "invalid_cursor"}, status=status.HTTP_400_BAD_REQUEST)
        rows = list(
            queryset.order_by("provider", "owner_login", "full_name")[offset : offset + REPOSITORY_PAGE_SIZE + 1]
        )
        next_cursor = str(offset + REPOSITORY_PAGE_SIZE) if len(rows) > REPOSITORY_PAGE_SIZE else None
        rows = rows[:REPOSITORY_PAGE_SIZE]
        return Response(
            {"results": AgentGitRepositorySerializer(rows, many=True).data, "next_cursor": next_cursor},
            status=status.HTTP_200_OK,
        )
