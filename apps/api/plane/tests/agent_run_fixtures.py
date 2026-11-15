# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Shared setup for the Agent Run tests: a connected Claude agent, a bound project and an issue."""

from dataclasses import dataclass

import pytest

from plane.agent.services.agent_settings import ensure_workspace_agent
from plane.db.models import (
    Agent,
    AgentConnectionState,
    AgentRun,
    Issue,
    Project,
    ProjectMember,
    ProjectRepositoryBinding,
    State,
    User,
    Workspace,
)
from plane.license.utils.encryption import encrypt_data
from plane.tests.agent_git_fixtures import GITLAB_HOST, GITLAB_TOKEN, make_catalog

WORKER_RUNS = "/api/agent-worker/v1/runs"
CLAIM_URL = f"{WORKER_RUNS}/claim/"
TEST_CA_BUNDLE = "-----BEGIN CERTIFICATE-----\nMIIBtest\n-----END CERTIFICATE-----\n"


def worker_run_url(run_id, action):
    return f"{WORKER_RUNS}/{run_id}/{action}/"


def comments_url(issue):
    return f"/api/workspaces/{issue.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}/comments/"


def runs_url(issue, run_id=None, action=None):
    url = f"/api/workspaces/{issue.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}/agent-runs/"
    if run_id is not None:
        url += f"{run_id}/"
    if action:
        url += f"{action}/"
    return url


def agent_mention(agent):
    return f'<mention-component entity_name="agent_mention" entity_identifier="{agent.id}"></mention-component>'


def user_mention(user):
    return f'<mention-component entity_name="user_mention" entity_identifier="{user.id}"></mention-component>'


def connect_agent(agent):
    connection = agent.connection
    connection.state = AgentConnectionState.CONNECTED
    connection.save()
    return agent


def connected_agent(workspace, harness="claude_code"):
    return connect_agent(ensure_workspace_agent(workspace, harness))


def bind_project(project, user, provider="github"):
    """Bind ``project`` to a catalog repository of a connected ``provider`` connection."""
    host = "github.com" if provider == "github" else GITLAB_HOST
    connection, account, rows = make_catalog(
        project.workspace,
        user,
        provider=provider,
        host=host,
        repositories=[(f"{project.identifier}-501", f"{project.identifier.lower()}-org/api")],
    )
    if provider == "gitlab":
        connection.access_token = encrypt_data(GITLAB_TOKEN)
        connection.ca_bundle = TEST_CA_BUNDLE
        connection.save()
    row = rows[0]
    return ProjectRepositoryBinding.objects.create(
        project=project,
        workspace=project.workspace,
        account=account,
        provider=provider,
        host=host,
        external_repository_id=row.external_id,
        full_name=row.full_name,
        clone_url=row.clone_url,
        web_url=row.web_url,
        default_branch="main",
        base_ref="main",
    )


def make_project(workspace, user, identifier="AGT", role=20):
    project = Project.objects.create(name=f"Project {identifier}", identifier=identifier, workspace=workspace)
    ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=role)
    State.objects.create(name="Todo", project=project, group="unstarted", default=True)
    return project


def make_issue(project, name="Login fails after reset", description_html="<p>Users cannot log in.</p>"):
    state = State.objects.get(project=project, default=True)
    return Issue.objects.create(
        name=name, workspace=project.workspace, project=project, state=state, description_html=description_html
    )


def post_comment(client, issue, html):
    return client.post(comments_url(issue), {"comment_html": html}, format="json")


def ask(client, issue, *agents, text="What does the login view do?"):
    """Post a comment that mentions ``agents`` and return the response."""
    mentions = " ".join(agent_mention(agent) for agent in agents)
    return post_comment(client, issue, f"<p>{mentions} {text}</p>")


def claim(worker_client, harnesses=("claude_code",)):
    return worker_client.post(CLAIM_URL, {"harnesses": list(harnesses)}, format="json")


@dataclass
class RunSetup:
    workspace: Workspace
    user: User
    agent: Agent
    project: Project
    issue: Issue
    binding: ProjectRepositoryBinding


@pytest.fixture
def run_setup(db, workspace, create_user, mock_celery):
    """A connected Claude agent, a GitHub-bound project where the user is admin, and an issue."""
    project = make_project(workspace, create_user)
    binding = bind_project(project, create_user)
    return RunSetup(
        workspace=workspace,
        user=create_user,
        agent=connected_agent(workspace),
        project=project,
        issue=make_issue(project),
        binding=binding,
    )


def create_run(session_client, setup, text="What does the login view do?"):
    response = ask(session_client, setup.issue, setup.agent, text=text)
    assert response.status_code == 201, response.data
    return AgentRun.objects.get(trigger_comment_id=response.data["id"], agent=setup.agent)


def claim_run(worker_client):
    """Claim the oldest created Run and return the claim body."""
    response = claim(worker_client)
    assert response.status_code == 200, response.data
    assert response.data["run"] is not None
    return response.data["run"]
