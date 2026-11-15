# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views.agent.settings import (
    AgentConnectEndpoint,
    AgentDetailEndpoint,
    AgentDisconnectEndpoint,
    AgentsEndpoint,
)
from plane.app.views.agent.runs import IssueRunDetailEndpoint, IssueRunEventsEndpoint, IssueRunsEndpoint
from plane.app.views.agent.git import (
    AgentGitAccountAttachEndpoint,
    AgentGitAccountDetailEndpoint,
    AgentGitAccountsEndpoint,
    AgentGitConnectionEndpoint,
    AgentGitConnectionsEndpoint,
    AgentGitPolicyEndpoint,
    AgentGitRepositoriesEndpoint,
    AgentGithubAccountsSyncEndpoint,
    AgentGithubDeviceAuthorizationCancelEndpoint,
    AgentGithubDeviceAuthorizationEndpoint,
    AgentGithubDeviceAuthorizationPollEndpoint,
)

AGENT_GIT = "workspaces/<str:slug>/agent-git"
AGENTS = "workspaces/<str:slug>/agents"
ISSUE_RUNS = "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/agent-runs"

urlpatterns = [
    path(f"{AGENTS}/", AgentsEndpoint.as_view(), name="agents"),
    path(f"{AGENTS}/<str:harness>/", AgentDetailEndpoint.as_view(), name="agent-detail"),
    path(f"{AGENTS}/<str:harness>/connect/", AgentConnectEndpoint.as_view(), name="agent-connect"),
    path(f"{AGENTS}/<str:harness>/disconnect/", AgentDisconnectEndpoint.as_view(), name="agent-disconnect"),
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
    path(
        f"{AGENT_GIT}/github/accounts/sync/",
        AgentGithubAccountsSyncEndpoint.as_view(),
        name="agent-git-github-accounts-sync",
    ),
    path(f"{AGENT_GIT}/<str:provider>/connection/", AgentGitConnectionEndpoint.as_view(), name="agent-git-connection"),
    path(f"{AGENT_GIT}/<str:provider>/accounts/", AgentGitAccountsEndpoint.as_view(), name="agent-git-accounts"),
    path(
        f"{AGENT_GIT}/<str:provider>/accounts/<uuid:pk>/",
        AgentGitAccountDetailEndpoint.as_view(),
        name="agent-git-account-detail",
    ),
    path(
        f"{AGENT_GIT}/<str:provider>/accounts/<uuid:pk>/attach/",
        AgentGitAccountAttachEndpoint.as_view(),
        name="agent-git-account-attach",
    ),
    path(f"{AGENT_GIT}/<str:provider>/policy/", AgentGitPolicyEndpoint.as_view(), name="agent-git-policy"),
    path(f"{AGENT_GIT}/repositories/", AgentGitRepositoriesEndpoint.as_view(), name="agent-git-repositories"),
    path(f"{ISSUE_RUNS}/", IssueRunsEndpoint.as_view(), name="issue-agent-runs"),
    path(f"{ISSUE_RUNS}/<uuid:run_id>/", IssueRunDetailEndpoint.as_view(), name="issue-agent-run-detail"),
    path(f"{ISSUE_RUNS}/<uuid:run_id>/events/", IssueRunEventsEndpoint.as_view(), name="issue-agent-run-events"),
]
