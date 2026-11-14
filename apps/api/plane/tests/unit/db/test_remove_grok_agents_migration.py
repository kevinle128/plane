# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from importlib import import_module

import pytest
from django.apps import apps

from plane.agent.services.agent_settings import ensure_workspace_agents
from plane.db.models import Agent, AgentConnection, BotTypeEnum, User, Workspace

migration = import_module("plane.db.migrations.0131_remove_grok_harness")


def grok_agent(workspace, deleted=False):
    """A Grok Agent as an earlier build created it, with its bot user and connection."""
    bot_user = User.objects.create(
        username=f"agent-grok-{workspace.id.hex}",
        email=f"agent-grok-{workspace.id.hex}@agents.plane.invalid",
        display_name="Grok CLI",
        is_bot=True,
        bot_type=BotTypeEnum.AGENT,
    )
    agent = Agent.objects.create(workspace=workspace, harness="grok", name="Grok CLI", handle="Grok", bot_user=bot_user)
    AgentConnection.objects.create(agent=agent)
    if deleted:
        agent.delete()
    return agent, bot_user


@pytest.mark.unit
@pytest.mark.django_db
def test_grok_agents_their_connections_and_bot_users_are_removed(create_user):
    workspace = Workspace.objects.create(name="Agents", owner=create_user, slug="agents-workspace")
    kept = ensure_workspace_agents(workspace)
    agent, bot_user = grok_agent(workspace)
    other_workspace = Workspace.objects.create(name="Other", owner=create_user, slug="other-agents")
    deleted_agent, deleted_bot_user = grok_agent(other_workspace, deleted=True)

    migration.remove_grok_agents(apps, None)

    assert not Agent.all_objects.filter(harness="grok").exists()
    assert not AgentConnection.all_objects.filter(agent_id__in=[agent.id, deleted_agent.id]).exists()
    assert not User.objects.filter(id__in=[bot_user.id, deleted_bot_user.id]).exists()
    assert list(Agent.objects.filter(workspace=workspace).order_by("created_at")) == kept
    assert User.objects.filter(id__in=[item.bot_user_id for item in kept]).count() == len(kept)


@pytest.mark.unit
@pytest.mark.django_db
def test_removing_grok_agents_twice_is_safe(create_user):
    workspace = Workspace.objects.create(name="Agents", owner=create_user, slug="agents-workspace")
    grok_agent(workspace)

    migration.remove_grok_agents(apps, None)
    migration.remove_grok_agents(apps, None)

    assert not Agent.all_objects.filter(harness="grok").exists()
