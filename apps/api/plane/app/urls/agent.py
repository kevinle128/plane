# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views.agent.git import (
    AgentGitConnectionsEndpoint,
    AgentGithubDeviceAuthorizationCancelEndpoint,
    AgentGithubDeviceAuthorizationEndpoint,
    AgentGithubDeviceAuthorizationPollEndpoint,
)

AGENT_GIT = "workspaces/<str:slug>/agent-git"

urlpatterns = [
    path(f"{AGENT_GIT}/connections/", AgentGitConnectionsEndpoint.as_view(), name="agent-git-connections"),
    path(
        f"{AGENT_GIT}/github/device-authorizations/",
        AgentGithubDeviceAuthorizationEndpoint.as_view(),
        name="agent-git-github-device-authorizations",
    ),
    path(
        f"{AGENT_GIT}/github/device-authorizations/<uuid:pk>/poll/",
        AgentGithubDeviceAuthorizationPollEndpoint.as_view(),
        name="agent-git-github-device-authorization-poll",
    ),
    path(
        f"{AGENT_GIT}/github/device-authorizations/<uuid:pk>/cancel/",
        AgentGithubDeviceAuthorizationCancelEndpoint.as_view(),
        name="agent-git-github-device-authorization-cancel",
    ),
]
