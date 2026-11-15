# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Run creation from a new work-item comment that mentions agents.

The caller saves the comment and calls ``create_runs_for_comment`` inside one
transaction, so a failure here also removes the comment. One Run is created
per distinct mentioned Agent. A Run whose repository cannot be used is saved
as ``failed`` at once and is never claimed.
"""

# Python imports
import secrets
import uuid

# Third party imports
from bs4 import BeautifulSoup

# Django imports
from django.utils import timezone

# Module imports
from plane.agent.services import context_snapshot, run_events
from plane.agent.services.agent_settings import connection_view, ensure_workspace_agents
from plane.agent.services.git_connection import binding_availability
from plane.db.models import (
    Agent,
    AgentConnectionState,
    AgentGitProvider,
    AgentRun,
    AgentRunEventKind,
    AgentRunStatus,
    ProjectRepositoryBinding,
)

AGENT_MENTION = "agent_mention"
SHORT_ID_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
SHORT_ID_LENGTH = 6


class AgentUnavailable(Exception):
    """A mentioned Agent cannot start a Run. The whole comment is rejected."""

    def __init__(self, agent, reason):
        super().__init__(reason)
        self.agent = agent
        self.reason = reason

    def body(self):
        return {"error": "agent_unavailable", "agent": self.agent, "reason": self.reason}


def parse_agent_mentions(comment_html):
    """The distinct agent IDs mentioned in ``comment_html``, in the order of their first mention."""
    soup = BeautifulSoup(comment_html or "", "html.parser")
    identifiers = []
    for node in soup.find_all("mention-component", attrs={"entity_name": AGENT_MENTION}):
        identifier = (node.get("entity_identifier") or "").strip()
        if identifier and identifier not in identifiers:
            identifiers.append(identifier)
    return identifiers


def unavailable_reason(agent, now=None):
    """Why ``agent`` cannot start a new Run, or ``""`` when it can."""
    state, _ = connection_view(agent.connection, now)
    if state != AgentConnectionState.CONNECTED:
        return "not_connected"
    if not agent.mentionable:
        return "not_mentionable"
    return ""


def mentioned_agents(workspace_id, identifiers):
    """Return the Agents for ``identifiers`` or raise ``AgentUnavailable`` for the first one that cannot run."""
    agents = []
    for identifier in identifiers:
        try:
            agent_id = uuid.UUID(identifier)
        except ValueError:
            raise AgentUnavailable(identifier, "not_found")
        agent = (
            Agent.objects.select_related("connection", "bot_user")
            .filter(pk=agent_id, workspace_id=workspace_id)
            .first()
        )
        if agent is None:
            raise AgentUnavailable(identifier, "not_found")
        reason = unavailable_reason(agent)
        if reason:
            raise AgentUnavailable(agent.name, reason)
        agents.append(agent)
    return agents


def new_short_id(workspace_id):
    while True:
        short_id = "R-" + "".join(secrets.choice(SHORT_ID_ALPHABET) for _ in range(SHORT_ID_LENGTH))
        if not AgentRun.objects.filter(workspace_id=workspace_id, short_id=short_id).exists():
            return short_id


def repository_problem(binding):
    """``(failure_code, failure_message)`` when the project repository cannot be used, else ``("", "")``."""
    if binding is None:
        return "repository_unavailable", "The project has no repository for agents."
    availability = binding_availability(binding)
    if availability["available"]:
        return "", ""
    provider = AgentGitProvider(binding.provider).label
    messages = {
        "provider_disconnected": f"The {provider} connection is disconnected.",
        "provider_reconnect_required": f"The {provider} connection must be connected again.",
    }
    code = availability["reason"]
    return code, messages.get(code, f"The {provider} repository {binding.full_name} is not available.")


def repository_snapshot(binding):
    if binding is None:
        return {}
    return {
        "provider": binding.provider,
        "host": binding.host,
        "external_repository_id": binding.external_repository_id,
        "full_name": binding.full_name,
        "clone_url": binding.clone_url,
        "default_branch": binding.default_branch,
        "base_ref": binding.base_ref,
    }


def create_runs_for_comment(comment, issue, requester):
    """Create one Run per Agent mentioned in ``comment``. Call inside the transaction that saved it."""
    identifiers = parse_agent_mentions(comment.comment_html)
    if not identifiers:
        return []
    agents = mentioned_agents(issue.workspace_id, identifiers)
    binding = (
        ProjectRepositoryBinding.objects.select_related("account", "account__connection")
        .filter(project_id=issue.project_id)
        .first()
    )
    failure_code, failure_message = repository_problem(binding)
    runs = []
    for agent in agents:
        run = AgentRun(
            workspace_id=issue.workspace_id,
            project_id=issue.project_id,
            issue=issue,
            agent=agent,
            requester=requester,
            trigger_comment=comment,
            short_id=new_short_id(issue.workspace_id),
            agent_name=agent.name,
            agent_handle=agent.handle,
            harness=agent.harness,
            model=agent.selected_model,
            instructions=agent.instructions,
            **repository_snapshot(binding),
        )
        if failure_code:
            run.status = AgentRunStatus.FAILED
            run.failure_code = failure_code
            run.failure_message = failure_message
            run.ended_at = timezone.now()
            run.save()
        else:
            run.save()
            context_snapshot.create_snapshot(run, comment)
            run_events.append_locked(
                run,
                [
                    {
                        "source_key": "trigger",
                        "kind": AgentRunEventKind.MESSAGE,
                        "payload": {
                            "role": "user",
                            "text": context_snapshot.plain_text(comment.comment_html),
                            "comment_id": str(comment.id),
                            "author_id": str(requester.id),
                        },
                    }
                ],
            )
        runs.append(run)
    return runs


def mention_candidates(workspace, project_id, query):
    """Agents for the mention picker of a project. Unavailable ones are listed as disabled with a reason."""
    has_binding = ProjectRepositoryBinding.objects.filter(project_id=project_id, workspace=workspace).exists()
    query = (query or "").lower()
    candidates = []
    for agent in ensure_workspace_agents(workspace):
        if query and query not in agent.name.lower() and query not in agent.handle.lower():
            continue
        reason = unavailable_reason(agent) or ("" if has_binding else "no_repository")
        candidates.append(
            {
                "id": str(agent.id),
                "name": agent.name,
                "handle": agent.handle,
                "harness": agent.harness,
                "disabled": bool(reason),
                "disabled_reason": reason,
            }
        )
    return candidates
