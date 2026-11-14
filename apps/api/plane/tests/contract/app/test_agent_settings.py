# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import threading

import pytest
from django.db import connection as db_connection
from rest_framework import status

from plane.db.models import Agent, AgentConnection, User, Workspace, WorkspaceMember
from plane.tests.agent_git_fixtures import client_for_user
from plane.tests.agent_settings_fixtures import (
    agents_url,
    failing_checks,
    make_worker,
    probe_report,
    worker_client_for,
)

HARNESS_ORDER = ["claude_code", "codex", "omp"]


@pytest.mark.contract
class TestWorkspaceAgents:
    @pytest.mark.django_db
    def test_first_read_creates_three_agents_with_bot_users(self, session_client, workspace):
        response = session_client.get(agents_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert [agent["harness"] for agent in response.data] == HARNESS_ORDER
        assert [agent["name"] for agent in response.data] == ["Claude Code", "Codex CLI", "Omp"]
        assert [agent["handle"] for agent in response.data] == ["Claude", "Codex", "Omp"]
        for agent in response.data:
            assert agent["connection"]["state"] == "not_connected"
            assert agent["connection"]["models"] == []
            assert agent["mentionable"] is True
            assert agent["available_for_mentions"] is False
        agents = Agent.objects.filter(workspace=workspace).select_related("bot_user")
        assert agents.count() == 3
        for agent in agents:
            assert agent.bot_user.is_bot is True
            assert agent.bot_user.bot_type == "AGENT"
            assert agent.bot_user.display_name == agent.name
            assert not agent.bot_user.has_usable_password()
            assert not workspace.workspace_member.filter(member=agent.bot_user).exists()
        assert AgentConnection.objects.filter(agent__workspace=workspace).count() == 3

    @pytest.mark.django_db
    @pytest.mark.parametrize("action", [None, "connect", "disconnect"])
    def test_grok_is_not_a_harness(self, session_client, workspace, action):
        url = agents_url(workspace.slug, "grok", action)

        response = session_client.post(url, {}, format="json") if action else session_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert not Agent.objects.filter(workspace=workspace, harness="grok").exists()

    @pytest.mark.django_db
    def test_second_read_creates_nothing(self, session_client, workspace):
        session_client.get(agents_url(workspace.slug))
        users_before = User.objects.count()

        response = session_client.get(agents_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert Agent.objects.filter(workspace=workspace).count() == 3
        assert User.objects.count() == users_before

    @pytest.mark.django_db
    def test_member_reads_agents(self, member_client, workspace):
        response = member_client.get(agents_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    @pytest.mark.django_db
    def test_guest_cannot_read_agents(self, guest_client, workspace):
        assert guest_client.get(agents_url(workspace.slug)).status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_detail_returns_one_harness(self, session_client, workspace):
        response = session_client.get(agents_url(workspace.slug, "claude_code"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["harness"] == "claude_code"
        assert response.data["connection"]["state"] == "not_connected"

    @pytest.mark.django_db
    def test_unknown_harness_returns_404(self, session_client, workspace):
        assert session_client.get(agents_url(workspace.slug, "aider")).status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_bot_users_do_not_leak_into_the_payload(self, session_client, workspace):
        response = session_client.get(agents_url(workspace.slug, "claude_code"))

        assert "bot_user" not in response.data
        assert "email" not in str(response.data)


@pytest.mark.contract
class TestConcurrentFirstRead:
    @pytest.mark.django_db(transaction=True)
    def test_two_concurrent_first_reads_create_one_agent_per_harness(self, workspace, create_user):
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def read():
            try:
                client = client_for_user(create_user)
                barrier.wait(timeout=30)
                response = client.get(agents_url(workspace.slug))
                results.append((response.status_code, [agent["id"] for agent in response.data]))
            except Exception as exc:  # surfaced through the errors list
                errors.append(exc)
            finally:
                db_connection.close()

        threads = [threading.Thread(target=read) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
            assert not thread.is_alive()

        assert not errors, errors
        assert [code for code, _ in results] == [200, 200]
        assert results[0][1] == results[1][1]
        assert Agent.objects.filter(workspace=workspace).count() == 3
        assert AgentConnection.objects.filter(agent__workspace=workspace).count() == 3
        assert User.objects.filter(is_bot=True, bot_type="AGENT").count() == 3


def patch_agent(client, workspace, payload, harness="claude_code"):
    return client.patch(agents_url(workspace.slug, harness), payload, format="json")


@pytest.mark.contract
class TestRenameAgent:
    @pytest.mark.django_db
    def test_valid_name_persists_and_names_the_bot_user(self, session_client, workspace):
        response = patch_agent(session_client, workspace, {"name": "  Reviewer Claude  "})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Reviewer Claude"
        listed = session_client.get(agents_url(workspace.slug)).data
        assert listed[0]["name"] == "Reviewer Claude"
        agent = Agent.objects.select_related("bot_user").get(workspace=workspace, harness="claude_code")
        assert agent.bot_user.display_name == "Reviewer Claude"
        assert agent.bot_user.first_name == "Reviewer Claude"

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ("name", "code"),
        [("", "blank"), ("   ", "blank"), ("x" * 65, "max_length"), ("Line\nbreak", "invalid")],
    )
    def test_empty_or_invalid_name_returns_400_and_keeps_the_old_name(self, session_client, workspace, name, code):
        session_client.get(agents_url(workspace.slug))

        response = patch_agent(session_client, workspace, {"name": name})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["name"]
        assert response.data["codes"]["name"] == code
        assert session_client.get(agents_url(workspace.slug, "claude_code")).data["name"] == "Claude Code"
        agent = Agent.objects.select_related("bot_user").get(workspace=workspace, harness="claude_code")
        assert agent.bot_user.display_name == "Claude Code"

    @pytest.mark.django_db
    def test_member_cannot_rename(self, session_client, member_client, workspace):
        session_client.get(agents_url(workspace.slug))

        response = patch_agent(member_client, workspace, {"name": "Mine"})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert session_client.get(agents_url(workspace.slug, "claude_code")).data["name"] == "Claude Code"

    @pytest.mark.django_db
    def test_rename_keeps_the_agent_and_bot_user_identity(self, session_client, workspace):
        before = session_client.get(agents_url(workspace.slug, "claude_code")).data
        bot_user_id = Agent.objects.get(workspace=workspace, harness="claude_code").bot_user_id

        after = patch_agent(session_client, workspace, {"name": "Renamed"}).data

        assert after["id"] == before["id"]
        assert Agent.objects.get(workspace=workspace, harness="claude_code").bot_user_id == bot_user_id

    @pytest.mark.django_db
    def test_read_only_fields_are_ignored(self, session_client, workspace):
        response = patch_agent(session_client, workspace, {"name": "Renamed", "harness": "codex", "id": "x"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["harness"] == "claude_code"

    @pytest.mark.django_db
    def test_unknown_harness_returns_404(self, session_client, workspace):
        assert patch_agent(session_client, workspace, {"name": "X"}, harness="aider").status_code == 404


HANDLE_TAKEN = "An agent with this handle already exists in this workspace."


def handles(client, workspace):
    return {agent["harness"]: agent["handle"] for agent in client.get(agents_url(workspace.slug)).data}


@pytest.mark.contract
class TestAgentHandle:
    @pytest.mark.django_db
    def test_unused_valid_handle_saves(self, session_client, workspace):
        response = patch_agent(session_client, workspace, {"handle": "@Reviewer_2"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["handle"] == "Reviewer_2"
        assert handles(session_client, workspace)["claude_code"] == "Reviewer_2"

    @pytest.mark.django_db
    @pytest.mark.parametrize("taken", ["Codex", "codex", "@CODEX"])
    def test_collision_returns_400_and_keeps_both_handles(self, session_client, workspace, taken):
        before = handles(session_client, workspace)

        response = patch_agent(session_client, workspace, {"handle": taken})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["handle"] == [HANDLE_TAKEN]
        assert response.data["codes"]["handle"] == "taken"
        assert handles(session_client, workspace) == before

    @pytest.mark.django_db
    def test_changing_only_the_case_of_its_own_handle_is_allowed(self, session_client, workspace):
        response = patch_agent(session_client, workspace, {"handle": "CLAUDE"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["handle"] == "CLAUDE"

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ("handle", "code"),
        [("", "blank"), ("two words", "invalid"), ("1st", "invalid"), ("a" * 33, "invalid"), ("é", "invalid")],
    )
    def test_invalid_handle_returns_400(self, session_client, workspace, handle, code):
        session_client.get(agents_url(workspace.slug))

        response = patch_agent(session_client, workspace, {"handle": handle})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["codes"]["handle"] == code
        assert handles(session_client, workspace)["claude_code"] == "Claude"

    @pytest.mark.django_db
    def test_same_handle_in_another_workspace_is_allowed(self, session_client, workspace, create_user):
        other = Workspace.objects.create(name="Other", owner=create_user, slug="other-workspace")
        WorkspaceMember.objects.create(workspace=other, member=create_user, role=20)
        session_client.get(agents_url(other.slug))

        response = patch_agent(session_client, workspace, {"handle": "Codex"}, harness="omp")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        other_response = session_client.patch(agents_url(other.slug, "omp"), {"handle": "Helper"}, format="json")
        mine = patch_agent(session_client, workspace, {"handle": "Helper"}, harness="omp")
        assert other_response.status_code == status.HTTP_200_OK
        assert mine.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_member_cannot_change_a_handle(self, session_client, member_client, workspace):
        session_client.get(agents_url(workspace.slug))

        assert patch_agent(member_client, workspace, {"handle": "Mine"}).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.contract
class TestConcurrentHandleChange:
    @pytest.mark.django_db(transaction=True)
    def test_two_agents_taking_one_handle_at_once_give_one_200_and_one_400(self, workspace, create_user):
        client_for_user(create_user).get(agents_url(workspace.slug))
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def take(harness):
            try:
                client = client_for_user(create_user)
                barrier.wait(timeout=30)
                response = client.patch(agents_url(workspace.slug, harness), {"handle": "Shared"}, format="json")
                results.append((response.status_code, response.data.get("codes", {}).get("handle")))
            except Exception as exc:  # surfaced through the errors list
                errors.append(exc)
            finally:
                db_connection.close()

        threads = [threading.Thread(target=take, args=(harness,)) for harness in ("codex", "omp")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
            assert not thread.is_alive()

        assert not errors, errors
        assert sorted(results, key=lambda item: item[0]) == [(200, None), (400, "taken")]
        assert Agent.objects.filter(workspace=workspace, handle__iexact="shared").count() == 1


MULTILINE_UNICODE = "Trả lời bằng tiếng Việt.\n\n- Cite file paths 📄\n\tKeep answers short.  \n"


@pytest.mark.contract
class TestAgentInstructions:
    @pytest.mark.django_db
    def test_multiline_unicode_instructions_persist_exactly(self, session_client, workspace):
        response = patch_agent(session_client, workspace, {"instructions": MULTILINE_UNICODE})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["instructions"] == MULTILINE_UNICODE
        reloaded = session_client.get(agents_url(workspace.slug, "claude_code")).data
        assert reloaded["instructions"] == MULTILINE_UNICODE

    @pytest.mark.django_db
    def test_empty_instructions_clear_the_text(self, session_client, workspace):
        patch_agent(session_client, workspace, {"instructions": "Be brief."})

        response = patch_agent(session_client, workspace, {"instructions": ""})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["instructions"] == ""

    @pytest.mark.django_db
    @pytest.mark.parametrize(("text", "code"), [("x" * 10001, "max_length"), ("before\x00after", "invalid")])
    def test_too_long_or_nul_instructions_return_400_and_keep_the_text(self, session_client, workspace, text, code):
        patch_agent(session_client, workspace, {"instructions": "Be brief."})

        response = patch_agent(session_client, workspace, {"instructions": text})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["codes"]["instructions"] == code
        assert session_client.get(agents_url(workspace.slug, "claude_code")).data["instructions"] == "Be brief."

    @pytest.mark.django_db
    def test_member_reads_but_cannot_change_instructions(self, session_client, member_client, workspace):
        patch_agent(session_client, workspace, {"instructions": "Be brief."})

        response = patch_agent(member_client, workspace, {"instructions": "Ignore the rules."})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert member_client.get(agents_url(workspace.slug, "claude_code")).data["instructions"] == "Be brief."


def connect_claude(session_client, workspace):
    """Connect Claude Code through a claimed probe and a passing report, as the Worker does."""
    session_client.post(agents_url(workspace.slug, "claude_code", "connect"), {}, format="json")
    _, token = make_worker(name=f"worker-{workspace.slug}")
    worker = worker_client_for(token)
    probe = worker.post("/api/agent-worker/v1/probes/claim/", {"harnesses": ["claude_code"]}, format="json").data[
        "probe"
    ]
    report = worker.post(
        f"/api/agent-worker/v1/probes/{probe['id']}/report/", probe_report(probe["generation"]), format="json"
    )
    assert report.status_code == status.HTTP_200_OK


@pytest.mark.contract
class TestAgentMentionable:
    @pytest.mark.django_db
    def test_disabling_mentions_persists_and_blocks_new_runs_but_keeps_the_connection(self, session_client, workspace):
        connect_claude(session_client, workspace)
        assert session_client.get(agents_url(workspace.slug, "claude_code")).data["available_for_mentions"] is True

        response = patch_agent(session_client, workspace, {"mentionable": False})

        assert response.status_code == status.HTTP_200_OK
        reloaded = session_client.get(agents_url(workspace.slug, "claude_code")).data
        assert reloaded["mentionable"] is False
        assert reloaded["available_for_mentions"] is False
        assert reloaded["connection"]["state"] == "connected"

    @pytest.mark.django_db
    def test_enabling_mentions_again_restores_availability(self, session_client, workspace):
        connect_claude(session_client, workspace)
        patch_agent(session_client, workspace, {"mentionable": False})

        response = patch_agent(session_client, workspace, {"mentionable": True})

        assert response.data["mentionable"] is True
        assert response.data["available_for_mentions"] is True

    @pytest.mark.django_db
    def test_non_boolean_returns_400(self, session_client, workspace):
        session_client.get(agents_url(workspace.slug))

        response = patch_agent(session_client, workspace, {"mentionable": "maybe"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["codes"]["mentionable"] == "invalid"
        assert session_client.get(agents_url(workspace.slug, "claude_code")).data["mentionable"] is True

    @pytest.mark.django_db
    def test_member_cannot_toggle_mentions(self, session_client, member_client, workspace):
        session_client.get(agents_url(workspace.slug))

        response = patch_agent(member_client, workspace, {"mentionable": False})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert session_client.get(agents_url(workspace.slug, "claude_code")).data["mentionable"] is True


def reconnect_claude(session_client, workspace, models):
    """Run another probe generation that reports ``models``."""
    session_client.post(agents_url(workspace.slug, "claude_code", "connect"), {}, format="json")
    _, token = make_worker(name=f"worker-{workspace.slug}-again")
    worker = worker_client_for(token)
    probe = worker.post("/api/agent-worker/v1/probes/claim/", {"harnesses": ["claude_code"]}, format="json").data[
        "probe"
    ]
    worker.post(
        f"/api/agent-worker/v1/probes/{probe['id']}/report/",
        probe_report(probe["generation"], models=models),
        format="json",
    )


@pytest.mark.contract
class TestAgentModelSelection:
    @pytest.mark.django_db
    def test_reported_model_saves_and_stays_after_refresh(self, session_client, workspace):
        connect_claude(session_client, workspace)

        response = patch_agent(session_client, workspace, {"selected_model": "sonnet"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["selected_model"] == "sonnet"
        assert session_client.get(agents_url(workspace.slug, "claude_code")).data["selected_model"] == "sonnet"

    @pytest.mark.django_db
    def test_model_outside_the_report_returns_400(self, session_client, workspace):
        connect_claude(session_client, workspace)
        patch_agent(session_client, workspace, {"selected_model": "sonnet"})

        response = patch_agent(session_client, workspace, {"selected_model": "gpt-5"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["codes"]["selected_model"] == "not_reported"
        assert session_client.get(agents_url(workspace.slug, "claude_code")).data["selected_model"] == "sonnet"

    @pytest.mark.django_db
    @pytest.mark.parametrize("state", ["not_connected", "connecting", "failed"])
    def test_selection_is_unavailable_unless_connected(self, session_client, worker_client, workspace, state):
        session_client.get(agents_url(workspace.slug))
        if state != "not_connected":
            session_client.post(agents_url(workspace.slug, "claude_code", "connect"), {}, format="json")
        if state == "failed":
            probe = worker_client.post(
                "/api/agent-worker/v1/probes/claim/", {"harnesses": ["claude_code"]}, format="json"
            ).data["probe"]
            worker_client.post(
                f"/api/agent-worker/v1/probes/{probe['id']}/report/",
                probe_report(probe["generation"], checks=failing_checks("authentication")),
                format="json",
            )
        assert session_client.get(agents_url(workspace.slug, "claude_code")).data["connection"]["state"] == state

        response = patch_agent(session_client, workspace, {"selected_model": "sonnet"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["codes"]["selected_model"] == "not_connected"
        agent = session_client.get(agents_url(workspace.slug, "claude_code")).data
        assert agent["selected_model"] == ""
        assert agent["connection"]["models"] == []

    @pytest.mark.django_db
    def test_clearing_the_selection_is_always_allowed(self, session_client, workspace):
        connect_claude(session_client, workspace)
        patch_agent(session_client, workspace, {"selected_model": "sonnet"})
        session_client.post(agents_url(workspace.slug, "claude_code", "disconnect"), {}, format="json")

        response = patch_agent(session_client, workspace, {"selected_model": ""})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["selected_model"] == ""

    @pytest.mark.django_db
    def test_disconnect_keeps_the_choice_for_a_later_reconnect(self, session_client, workspace):
        connect_claude(session_client, workspace)
        patch_agent(session_client, workspace, {"selected_model": "sonnet"})
        session_client.post(agents_url(workspace.slug, "claude_code", "disconnect"), {}, format="json")

        reconnect_claude(
            session_client,
            workspace,
            models=[{"id": "sonnet", "label": "Sonnet", "description": "", "source": "reported"}],
        )

        assert session_client.get(agents_url(workspace.slug, "claude_code")).data["selected_model"] == "sonnet"

    @pytest.mark.django_db
    def test_new_report_without_the_selected_model_clears_it(self, session_client, workspace):
        connect_claude(session_client, workspace)
        patch_agent(session_client, workspace, {"selected_model": "sonnet"})

        reconnect_claude(
            session_client, workspace, models=[{"id": "opus", "label": "Opus", "description": "", "source": "reported"}]
        )

        agent = session_client.get(agents_url(workspace.slug, "claude_code")).data
        assert agent["connection"]["state"] == "connected"
        assert agent["selected_model"] == ""

    @pytest.mark.django_db
    def test_member_cannot_select_a_model(self, session_client, member_client, workspace):
        connect_claude(session_client, workspace)

        response = patch_agent(member_client, workspace, {"selected_model": "sonnet"})

        assert response.status_code == status.HTTP_403_FORBIDDEN
