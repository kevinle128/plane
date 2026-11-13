# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Workspace Agents: lazy creation, derived connection state and availability.

Four Agents exist per workspace, one per Harness. They are created on the first
read. A concurrent first read hits the unique constraints (deterministic bot
username, unique workspace and Harness) and re-reads the row, so two reads never
create two Agents or two bot users.
"""

# Python imports
from datetime import timedelta

# Django imports
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction
from django.utils import timezone

# Module imports
from plane.db.models import Agent, AgentConnection, AgentConnectionState, AgentHarness, BotTypeEnum, User

# A probe with no report after this time reads as failed. It is derived at read time, so no task is needed.
PROBE_ANSWER_SECONDS = 120
WORKER_DID_NOT_ANSWER = "worker_did_not_answer"

HARNESS_ORDER = (AgentHarness.CLAUDE_CODE, AgentHarness.CODEX, AgentHarness.GROK, AgentHarness.OMP)

HARNESS_DEFAULTS = {
    AgentHarness.CLAUDE_CODE: {"name": "Claude Code", "handle": "Claude"},
    AgentHarness.CODEX: {"name": "Codex CLI", "handle": "Codex"},
    AgentHarness.GROK: {"name": "Grok CLI", "handle": "Grok"},
    AgentHarness.OMP: {"name": "Omp", "handle": "Omp"},
}

# Bot users get an address in the reserved ``.invalid`` domain, so no mail can reach a real mailbox.
BOT_EMAIL_DOMAIN = "agents.plane.invalid"


def bot_username(workspace_id, harness):
    return f"agent-{harness}-{workspace_id.hex}"


def _create_agent(workspace, harness):
    defaults = HARNESS_DEFAULTS[harness]
    username = bot_username(workspace.id, harness)
    try:
        with transaction.atomic():
            bot_user = User.objects.create(
                username=username,
                email=f"{username}@{BOT_EMAIL_DOMAIN}",
                display_name=defaults["name"],
                first_name=defaults["name"],
                last_name="",
                is_bot=True,
                bot_type=BotTypeEnum.AGENT,
                password=make_password(None),
                is_password_autoset=True,
            )
            agent = Agent.objects.create(
                workspace=workspace,
                harness=harness,
                name=defaults["name"],
                handle=defaults["handle"],
                bot_user=bot_user,
            )
            AgentConnection.objects.create(agent=agent)
    except IntegrityError:
        # Another request created this Agent first; its row is now committed.
        return Agent.objects.select_related("connection").get(workspace=workspace, harness=harness)
    return Agent.objects.select_related("connection").get(pk=agent.pk)


def ensure_workspace_agents(workspace):
    """Return the four Agents of the workspace in Harness order, creating missing ones."""
    agents = {agent.harness: agent for agent in Agent.objects.filter(workspace=workspace).select_related("connection")}
    for harness in HARNESS_ORDER:
        if harness not in agents:
            agents[harness] = _create_agent(workspace, harness)
    return [agents[harness] for harness in HARNESS_ORDER]


def ensure_workspace_agent(workspace, harness):
    return next(agent for agent in ensure_workspace_agents(workspace) if agent.harness == harness)


def probe_answer_deadline(connection):
    if connection.probe_requested_at is None:
        return None
    return connection.probe_requested_at + timedelta(seconds=PROBE_ANSWER_SECONDS)


def is_probe_expired(connection, now=None):
    deadline = probe_answer_deadline(connection)
    return deadline is not None and (now or timezone.now()) > deadline


def connection_view(connection, now=None):
    """The state and missing action to show. A probe without a report after 120 s reads as failed."""
    if connection.state == AgentConnectionState.CONNECTING and is_probe_expired(connection, now):
        return AgentConnectionState.FAILED, WORKER_DID_NOT_ANSWER
    return connection.state, connection.missing_action


def is_available_for_mentions(agent, now=None):
    """A new Run can start only from a mentionable Agent whose Harness is connected."""
    state, _ = connection_view(agent.connection, now)
    return agent.mentionable and state == AgentConnectionState.CONNECTED
