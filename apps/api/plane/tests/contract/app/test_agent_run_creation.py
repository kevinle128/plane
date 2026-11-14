# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import re

import pytest
from rest_framework import status

from plane.db.models import (
    AgentGitAccountState,
    AgentGitConnection,
    AgentRun,
    AgentRunContextSnapshot,
    AgentRunEvent,
    Issue,
    IssueComment,
    Project,
    ProjectMember,
    ProjectRepositoryBinding,
    State,
    WorkspaceMember,
)
from plane.tests.agent_git_fixtures import client_for_user, make_workspace_user
from plane.tests.agent_run_fixtures import (
    agent_mention,
    ask,
    claim,
    connected_agent,
    create_run,
    make_issue,
    post_comment,
    runs_url,
)
from plane.tests.agent_settings_fixtures import agents_url

COMMENT_RESPONSE_KEYS = {
    "id",
    "actor_detail",
    "issue_detail",
    "project_detail",
    "workspace_detail",
    "comment_reactions",
    "created_at",
    "updated_at",
    "deleted_at",
    "comment_stripped",
    "comment_json",
    "comment_html",
    "attachments",
    "access",
    "external_source",
    "external_id",
    "edited_at",
    "created_by",
    "updated_by",
    "project",
    "workspace",
    "issue",
    "actor",
    "parent",
    "description",
}


def comments_url(issue):
    return f"/api/workspaces/{issue.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}/comments/"


def nothing_saved(issue):
    return not IssueComment.objects.filter(issue=issue).exists() and not AgentRun.objects.filter(issue=issue).exists()


@pytest.fixture
def plain_issue(db, workspace, create_user):
    project = Project.objects.create(name="Plain", identifier="PLN", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    state = State.objects.create(name="Todo", project=project, group="unstarted", default=True)
    return Issue.objects.create(name="Plain", workspace=workspace, project=project, state=state)


@pytest.mark.contract
class TestCommentCreateWithoutAgentMention:
    @pytest.mark.django_db
    def test_response_body_and_both_background_calls_are_unchanged(
        self, session_client, plain_issue, create_user, mocker
    ):
        issue_activity = mocker.patch("plane.app.views.issue.comment.issue_activity.delay")
        model_activity = mocker.patch("plane.app.views.issue.comment.model_activity.delay")

        response = session_client.post(
            comments_url(plain_issue), {"comment_html": "<p>Plain comment</p>"}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert set(response.data) == COMMENT_RESPONSE_KEYS
        assert response.data["comment_html"] == "<p>Plain comment</p>"
        assert response.data["comment_stripped"] == "Plain comment"
        assert str(response.data["actor"]) == str(create_user.id)
        assert str(response.data["issue"]) == str(plain_issue.id)
        assert IssueComment.objects.filter(issue=plain_issue).count() == 1

        issue_activity.assert_called_once()
        activity_kwargs = issue_activity.call_args.kwargs
        assert activity_kwargs["type"] == "comment.activity.created"
        assert activity_kwargs["actor_id"] == str(create_user.id)
        assert activity_kwargs["issue_id"] == str(plain_issue.id)
        assert activity_kwargs["project_id"] == str(plain_issue.project_id)
        assert activity_kwargs["current_instance"] is None
        assert activity_kwargs["notification"] is True

        model_activity.assert_called_once()
        model_kwargs = model_activity.call_args.kwargs
        assert model_kwargs["model_name"] == "issue_comment"
        assert model_kwargs["model_id"] == str(response.data["id"])
        assert model_kwargs["requested_data"] == {"comment_html": "<p>Plain comment</p>"}
        assert model_kwargs["current_instance"] is None
        assert model_kwargs["actor_id"] == create_user.id
        assert model_kwargs["slug"] == plain_issue.workspace.slug


@pytest.mark.contract
class TestRunCreation:
    @pytest.mark.django_db
    def test_comment_and_run_are_saved_together_with_snapshots(self, session_client, run_setup, mocker):
        issue_activity = mocker.patch("plane.app.views.issue.comment.issue_activity.delay")
        model_activity = mocker.patch("plane.app.views.issue.comment.model_activity.delay")
        agent = run_setup.agent
        agent.instructions = "Answer in English."
        agent.selected_model = "sonnet"
        agent.save()

        response = ask(session_client, run_setup.issue, agent)

        assert response.status_code == status.HTTP_201_CREATED
        assert set(response.data) == COMMENT_RESPONSE_KEYS
        issue_activity.assert_called_once()
        model_activity.assert_called_once()
        run = AgentRun.objects.get(trigger_comment_id=response.data["id"])
        assert run.status == "created"
        assert re.fullmatch(r"R-[A-Z2-7]{6}", run.short_id)
        assert (run.workspace_id, run.project_id, run.issue_id) == (
            run_setup.workspace.id,
            run_setup.project.id,
            run_setup.issue.id,
        )
        assert (run.agent_id, run.requester_id) == (agent.id, run_setup.user.id)
        assert (run.agent_name, run.agent_handle, run.harness) == ("Claude Code", "Claude", "claude_code")
        assert (run.model, run.instructions) == ("sonnet", "Answer in English.")
        binding = run_setup.binding
        assert (run.provider, run.host, run.external_repository_id) == (
            "github",
            "github.com",
            binding.external_repository_id,
        )
        assert (run.full_name, run.clone_url, run.default_branch, run.base_ref) == (
            binding.full_name,
            binding.clone_url,
            "main",
            "main",
        )
        assert run.failure_code == ""
        assert AgentRunContextSnapshot.objects.filter(run=run, version=1).count() == 1
        trigger = AgentRunEvent.objects.get(run=run)
        assert (trigger.seq, trigger.kind, trigger.source_key) == (1, "message", "trigger")
        assert trigger.payload == {
            "role": "user",
            "text": "What does the login view do?",
            "comment_id": str(response.data["id"]),
            "author_id": str(run_setup.user.id),
        }
        run.refresh_from_db()
        assert run.next_event_seq == 2

    @pytest.mark.django_db
    def test_forced_failure_after_the_comment_save_rolls_back_both(self, session_client, run_setup, mocker):
        mocker.patch("plane.agent.services.context_snapshot.build_payload", side_effect=RuntimeError("snapshot failed"))
        session_client.raise_request_exception = False

        response = ask(session_client, run_setup.issue, run_setup.agent)

        assert response.status_code >= 500
        assert nothing_saved(run_setup.issue)

    @pytest.mark.django_db
    def test_two_agents_in_one_comment_create_two_runs(self, session_client, run_setup):
        codex = connected_agent(run_setup.workspace, "codex")

        response = ask(session_client, run_setup.issue, run_setup.agent, codex, run_setup.agent)

        assert response.status_code == status.HTTP_201_CREATED
        runs = AgentRun.objects.filter(trigger_comment_id=response.data["id"]).order_by("created_at")
        assert [run.agent_id for run in runs] == [run_setup.agent.id, codex.id]
        assert len({run.short_id for run in runs}) == 2
        assert IssueComment.objects.filter(issue=run_setup.issue).count() == 1

    @pytest.mark.django_db
    def test_comment_without_agent_mention_creates_no_run(self, session_client, run_setup):
        response = post_comment(session_client, run_setup.issue, "<p>No agent here</p>")

        assert response.status_code == status.HTTP_201_CREATED
        assert not AgentRun.objects.exists()

    @pytest.mark.django_db
    def test_comment_edit_never_creates_a_run(self, session_client, run_setup):
        response = post_comment(session_client, run_setup.issue, "<p>Draft</p>")
        url = f"{comments_url(run_setup.issue)}{response.data['id']}/"

        edit = session_client.patch(
            url, {"comment_html": f"<p>{agent_mention(run_setup.agent)} now</p>"}, format="json"
        )

        assert edit.status_code == status.HTTP_200_OK
        assert not AgentRun.objects.exists()


@pytest.mark.contract
class TestUnavailableAgent:
    @pytest.mark.django_db
    def test_disconnected_agent_returns_400_and_saves_nothing(self, session_client, run_setup):
        connection = run_setup.agent.connection
        connection.state = "not_connected"
        connection.save()

        response = ask(session_client, run_setup.issue, run_setup.agent)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {"error": "agent_unavailable", "agent": "Claude Code", "reason": "not_connected"}
        assert nothing_saved(run_setup.issue)

    @pytest.mark.django_db
    def test_non_mentionable_agent_returns_400_and_saves_nothing(self, session_client, run_setup):
        run_setup.agent.mentionable = False
        run_setup.agent.save()

        response = ask(session_client, run_setup.issue, run_setup.agent)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {"error": "agent_unavailable", "agent": "Claude Code", "reason": "not_mentionable"}
        assert nothing_saved(run_setup.issue)

    @pytest.mark.django_db
    def test_one_unavailable_agent_fails_the_whole_comment(self, session_client, run_setup):
        codex = connected_agent(run_setup.workspace, "codex")
        codex.mentionable = False
        codex.save()

        response = ask(session_client, run_setup.issue, run_setup.agent, codex)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["agent"] == "Codex CLI"
        assert nothing_saved(run_setup.issue)

    @pytest.mark.django_db
    def test_agent_of_another_workspace_is_not_found(self, session_client, run_setup, create_user):
        from plane.db.models import Workspace

        other = Workspace.objects.create(name="Other", owner=create_user, slug="other-workspace")
        foreign = connected_agent(other)

        response = ask(session_client, run_setup.issue, foreign)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {"error": "agent_unavailable", "agent": str(foreign.id), "reason": "not_found"}
        assert nothing_saved(run_setup.issue)

    @pytest.mark.django_db
    def test_guest_without_comment_right_gets_400_and_no_run(self, run_setup):
        guest = make_workspace_user(run_setup.workspace, 5)
        ProjectMember.objects.create(project=run_setup.project, member=guest, workspace=run_setup.workspace, role=5)

        response = ask(client_for_user(guest), run_setup.issue, run_setup.agent)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {"error": "You are not allowed to comment on the issue"}
        assert nothing_saved(run_setup.issue)


@pytest.mark.contract
class TestRepositoryNotUsable:
    """The Run is saved as failed and is never claimed when the repository cannot be used."""

    def assert_failed_run(self, session_client, worker_client, setup, failure_code, provider):
        response = ask(session_client, setup.issue, setup.agent)

        assert response.status_code == status.HTTP_201_CREATED
        run = AgentRun.objects.get(trigger_comment_id=response.data["id"])
        assert (run.status, run.failure_code, run.provider) == ("failed", failure_code, provider)
        assert run.ended_at is not None
        assert run.conclusion_comment_id is None
        assert claim(worker_client).data == {"run": None}
        listed = session_client.get(runs_url(setup.issue)).data
        assert [(row["status"], row["failure_code"], row["provider"]) for row in listed] == [
            ("failed", failure_code, provider)
        ]
        return run

    @pytest.mark.django_db
    def test_disconnected_provider_gives_provider_disconnected(self, session_client, worker_client, run_setup):
        AgentGitConnection.objects.filter(workspace=run_setup.workspace).update(status="disconnected")

        run = self.assert_failed_run(session_client, worker_client, run_setup, "provider_disconnected", "github")

        assert "GitHub" in run.failure_message

    @pytest.mark.django_db
    def test_demoted_connecting_admin_gives_provider_reconnect_required(self, session_client, worker_client, run_setup):
        WorkspaceMember.objects.filter(workspace=run_setup.workspace, member=run_setup.user).update(role=15)

        run = self.assert_failed_run(session_client, worker_client, run_setup, "provider_reconnect_required", "github")

        assert "GitHub" in run.failure_message
        connection = AgentGitConnection.objects.get(workspace=run_setup.workspace)
        assert (connection.status, connection.last_error) == ("reconnect_required", "connected_admin_lost")

    @pytest.mark.django_db
    def test_removed_grant_gives_repository_unavailable(self, session_client, worker_client, run_setup):
        account = run_setup.binding.account
        account.state = AgentGitAccountState.DETACHED
        account.save()

        run = self.assert_failed_run(session_client, worker_client, run_setup, "repository_unavailable", "github")

        assert run.full_name == run_setup.binding.full_name

    @pytest.mark.django_db
    def test_project_without_binding_gives_repository_unavailable(self, session_client, worker_client, run_setup):
        ProjectRepositoryBinding.objects.filter(project=run_setup.project).delete()

        run = self.assert_failed_run(session_client, worker_client, run_setup, "repository_unavailable", "")

        assert (run.full_name, run.clone_url) == ("", "")


@pytest.mark.contract
class TestRunSnapshotsOfAgentSettings:
    @pytest.mark.django_db
    def test_rename_and_handle_change_keep_the_run_agent_and_its_events(self, session_client, run_setup):
        run = create_run(session_client, run_setup)

        response = session_client.patch(
            agents_url(run_setup.workspace.slug, "claude_code"), {"name": "Claude", "handle": "cc"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        row = session_client.get(runs_url(run_setup.issue, run.id)).data
        assert row["agent"] == {
            "id": str(run_setup.agent.id),
            "name": "Claude Code",
            "handle": "Claude",
            "harness": "claude_code",
        }
        assert row["event_count"] == 1
        assert AgentRunEvent.objects.filter(run=run).count() == 1

    @pytest.mark.django_db
    def test_new_instructions_affect_only_new_runs(self, session_client, run_setup):
        first = create_run(session_client, run_setup)
        session_client.patch(
            agents_url(run_setup.workspace.slug, "claude_code"), {"instructions": "Be brief."}, format="json"
        )

        second = create_run(session_client, run_setup, text="And the logout view?")

        first.refresh_from_db()
        assert first.instructions == ""
        assert second.instructions == "Be brief."
        payloads = {
            snapshot.run_id: snapshot.payload["agent"]["instructions"]
            for snapshot in AgentRunContextSnapshot.objects.all()
        }
        assert payloads == {first.id: "", second.id: "Be brief."}

    @pytest.mark.django_db
    def test_disabling_mentionable_keeps_an_active_run_readable(self, session_client, worker_client, run_setup):
        run = create_run(session_client, run_setup)
        claim(worker_client)
        session_client.patch(agents_url(run_setup.workspace.slug, "claude_code"), {"mentionable": False}, format="json")

        detail = session_client.get(runs_url(run_setup.issue, run.id))
        listed = session_client.get(runs_url(run_setup.issue))

        assert detail.status_code == status.HTTP_200_OK
        assert detail.data["status"] == "in_progress"
        assert [row["id"] for row in listed.data] == [str(run.id)]


@pytest.mark.contract
class TestMemberRunRead:
    @pytest.mark.django_db
    def test_run_object_has_the_contract_fields(self, session_client, run_setup):
        run = create_run(session_client, run_setup)

        response = session_client.get(runs_url(run_setup.issue, run.id))

        assert response.status_code == status.HTTP_200_OK
        assert set(response.data) == {
            "id",
            "short_id",
            "status",
            "agent",
            "requester_id",
            "trigger_comment_id",
            "conclusion_comment_id",
            "created_at",
            "started_at",
            "ended_at",
            "last_progress_at",
            "failure_code",
            "failure_message",
            "provider",
            "repository_full_name",
            "clone_path",
            "model",
            "event_count",
            "sandbox",
        }
        assert response.data["short_id"] == run.short_id
        assert response.data["status"] == "created"
        assert response.data["requester_id"] == str(run_setup.user.id)
        assert response.data["trigger_comment_id"] == str(run.trigger_comment_id)
        assert response.data["repository_full_name"] == run_setup.binding.full_name
        assert response.data["sandbox"] == "read_only"

    @pytest.mark.django_db
    def test_expired_lease_of_an_active_run_reads_as_stale(self, session_client, worker_client, run_setup):
        from datetime import timedelta

        from django.utils import timezone

        run = create_run(session_client, run_setup)
        claim(worker_client)
        AgentRun.objects.filter(pk=run.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))

        assert session_client.get(runs_url(run_setup.issue, run.id)).data["status"] == "stale"
        run.refresh_from_db()
        assert run.status == "in_progress"

    @pytest.mark.django_db
    def test_runs_of_another_issue_are_not_listed_or_readable(self, session_client, run_setup):
        run = create_run(session_client, run_setup)
        other = make_issue(run_setup.project, name="Other issue")

        assert session_client.get(runs_url(other)).data == []
        assert session_client.get(runs_url(other, run.id)).status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_restricted_guest_cannot_read_runs_of_a_hidden_issue(self, session_client, run_setup):
        run = create_run(session_client, run_setup)
        guest = make_workspace_user(run_setup.workspace, 5)
        ProjectMember.objects.create(project=run_setup.project, member=guest, workspace=run_setup.workspace, role=5)

        response = client_for_user(guest).get(runs_url(run_setup.issue, run.id))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_non_member_cannot_read_runs(self, session_client, run_setup):
        create_run(session_client, run_setup)
        outsider = make_workspace_user(run_setup.workspace, 15)

        response = client_for_user(outsider).get(runs_url(run_setup.issue))

        assert response.status_code == status.HTTP_403_FORBIDDEN


def search(client, setup, query="", query_type="agent_mention"):
    return client.get(
        f"/api/workspaces/{setup.workspace.slug}/entity-search/",
        {"query_type": query_type, "query": query, "project_id": str(setup.project.id)},
    )


@pytest.mark.contract
class TestAgentMentionSearch:
    @pytest.mark.django_db
    def test_all_agents_are_listed_and_unavailable_ones_are_disabled(self, session_client, run_setup):
        response = search(session_client, run_setup)

        assert response.status_code == status.HTTP_200_OK
        rows = {row["harness"]: row for row in response.data["agent_mention"]}
        assert set(rows) == {"claude_code", "codex", "omp"}
        assert rows["claude_code"] == {
            "id": str(run_setup.agent.id),
            "name": "Claude Code",
            "handle": "Claude",
            "harness": "claude_code",
            "disabled": False,
            "disabled_reason": "",
        }
        assert (rows["codex"]["disabled"], rows["codex"]["disabled_reason"]) == (True, "not_connected")

    @pytest.mark.django_db
    def test_query_matches_name_or_handle(self, session_client, run_setup):
        by_name = search(session_client, run_setup, query="codex cli")
        by_handle = search(session_client, run_setup, query="omp")

        assert [row["harness"] for row in by_name.data["agent_mention"]] == ["codex"]
        assert [row["harness"] for row in by_handle.data["agent_mention"]] == ["omp"]

    @pytest.mark.django_db
    def test_non_mentionable_agent_is_disabled(self, session_client, run_setup):
        run_setup.agent.mentionable = False
        run_setup.agent.save()

        row = search(session_client, run_setup, query="claude").data["agent_mention"][0]

        assert (row["disabled"], row["disabled_reason"]) == (True, "not_mentionable")

    @pytest.mark.django_db
    def test_project_without_repository_disables_connected_agents(self, session_client, run_setup):
        ProjectRepositoryBinding.objects.filter(project=run_setup.project).delete()

        row = search(session_client, run_setup, query="claude").data["agent_mention"][0]

        assert (row["disabled"], row["disabled_reason"]) == (True, "no_repository")

    @pytest.mark.django_db
    def test_user_mention_is_unchanged_next_to_agent_mention(self, session_client, run_setup):
        response = search(session_client, run_setup, query_type="user_mention,agent_mention")

        assert [str(row["member__id"]) for row in response.data["user_mention"]] == [str(run_setup.user.id)]
        assert len(response.data["agent_mention"]) == 3

    @pytest.mark.django_db
    def test_non_member_of_the_project_gets_nothing(self, run_setup):
        outsider = make_workspace_user(run_setup.workspace, 15)

        response = search(client_for_user(outsider), run_setup)

        assert response.data == {"agent_mention": []}
