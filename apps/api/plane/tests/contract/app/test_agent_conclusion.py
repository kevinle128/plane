# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.db.models import (
    AgentConnection,
    AgentRun,
    AgentRunEvent,
    AgentRunTurn,
    Description,
    IssueComment,
    ProjectMember,
)
from plane.tests.agent_run_fixtures import (
    claim_run,
    comments_url,
    create_run,
    worker_run_url,
)


def post_result(worker_client, run_id, generation, **body):
    payload = {"lease_generation": generation, "status": "completed", "conclusion": "The view checks the token."}
    payload.update(body)
    return worker_client.post(worker_run_url(run_id, "result"), payload, format="json")


@pytest.fixture
def leased(session_client, worker_client, run_setup):
    run = create_run(session_client, run_setup)
    return run, claim_run(worker_client)["lease_generation"]


def connection_of(agent):
    return AgentConnection.objects.get(agent=agent)


@pytest.mark.contract
class TestCompletedResult:
    @pytest.mark.django_db
    def test_result_writes_one_bot_comment_and_finishes_the_run(self, worker_client, leased, run_setup):
        run, generation = leased
        conclusion = "Line one <script>alert(1)</script>\nline two\n\nSecond paragraph"

        response = post_result(worker_client, run.id, generation, conclusion=conclusion, session_ref="sess-1")

        assert response.status_code == status.HTTP_200_OK
        run.refresh_from_db()
        assert response.data == {"status": "completed", "conclusion_comment_id": run.conclusion_comment_id}
        assert run.status == "completed"
        assert run.ended_at is not None
        comment = IssueComment.objects.get(pk=run.conclusion_comment_id)
        bot_user = run_setup.agent.bot_user
        assert (comment.actor_id, comment.created_by_id, comment.issue_id) == (
            bot_user.id,
            bot_user.id,
            run_setup.issue.id,
        )
        assert Description.objects.get(pk=comment.description_id).created_by_id == bot_user.id
        html = comment.comment_html
        assert html.startswith(f"<p><strong>Answer from Claude Code (Run {run.short_id})</strong></p>")
        assert "<script" not in html and "alert(1)" not in html
        assert "line two" in html and "<p>Second paragraph</p>" in html
        last = AgentRunEvent.objects.filter(run=run).order_by("-seq").first()
        assert (last.kind, last.source_key) == ("conclusion", "conclusion")
        assert last.payload == {"text": conclusion, "comment_id": str(comment.id), "status": "completed"}
        turn = AgentRunTurn.objects.get(run=run, index=0)
        assert (turn.status, turn.driver_session_ref) == ("completed", "sess-1")
        assert turn.ended_at is not None

    @pytest.mark.django_db
    def test_markdown_answer_is_stored_as_sanitized_rich_text(self, worker_client, leased):
        run, generation = leased
        conclusion = (
            "## Cause\n\n"
            "The token check runs **twice**:\n\n"
            "- first in `views.py`\n"
            "- then in the middleware\n\n"
            "1. Remove one check\n"
            "2. Add a test\n\n"
            "```python\nif token:\n    return True\n```\n\n"
            "See [the docs](https://docs.plane.so/auth) and [this](javascript:alert(2)).\n\n"
            "<script>alert(1)</script>"
        )

        post_result(worker_client, run.id, generation, conclusion=conclusion)

        run.refresh_from_db()
        html = IssueComment.objects.get(pk=run.conclusion_comment_id).comment_html
        assert html.startswith(f"<p><strong>Answer from Claude Code (Run {run.short_id})</strong></p>")
        assert "<h2>Cause</h2>" in html
        assert "<strong>twice</strong>" in html
        assert "<ul>" in html and "<li>first in <code>views.py</code></li>" in html
        assert "<ol>" in html and "<li>Add a test</li>" in html
        assert '<pre><code class="language-python">if token:\n    return True\n</code></pre>' in html
        assert 'href="https://docs.plane.so/auth"' in html and ">the docs</a>" in html
        assert "javascript:" not in html
        assert "<script" not in html and "alert(1)" not in html

    @pytest.mark.django_db
    def test_duplicate_result_creates_one_conclusion(self, worker_client, leased):
        run, generation = leased
        first = post_result(worker_client, run.id, generation)

        second = post_result(worker_client, run.id, generation, conclusion="Another answer")

        assert second.status_code == status.HTTP_200_OK
        assert second.data == first.data
        assert IssueComment.objects.filter(actor__is_bot=True).count() == 1
        assert AgentRunEvent.objects.filter(run=run, kind="conclusion").count() == 1

    @pytest.mark.django_db
    def test_old_generation_gets_409(self, worker_client, leased):
        run, generation = leased
        AgentRun.objects.filter(pk=run.pk).update(lease_generation=generation + 1)

        response = post_result(worker_client, run.id, generation)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data == {"error": "lease_superseded"}
        assert not IssueComment.objects.filter(actor__is_bot=True).exists()

    @pytest.mark.django_db
    def test_completed_result_without_conclusion_gets_400(self, worker_client, leased):
        run, generation = leased

        response = post_result(worker_client, run.id, generation, conclusion="  ")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_bot_comment_is_listed_although_the_bot_is_not_a_project_member(
        self, session_client, worker_client, leased, run_setup
    ):
        run, generation = leased
        post_result(worker_client, run.id, generation)
        run.refresh_from_db()
        assert not ProjectMember.objects.filter(member=run_setup.agent.bot_user).exists()
        issue = run_setup.issue
        history_url = f"/api/workspaces/{issue.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}/history/"

        comments = session_client.get(comments_url(issue))
        history = session_client.get(history_url, {"activity_type": "issue-comment"})

        assert comments.status_code == status.HTTP_200_OK
        listed = comments.data["results"] if isinstance(comments.data, dict) else comments.data
        assert str(run.conclusion_comment_id) in [str(row["id"]) for row in listed]
        assert history.status_code == status.HTTP_200_OK
        bot_rows = [row for row in history.data if str(row["id"]) == str(run.conclusion_comment_id)]
        assert len(bot_rows) == 1
        assert bot_rows[0]["actor_detail"]["display_name"] == "Claude Code"


@pytest.mark.contract
class TestFailedResult:
    @pytest.mark.django_db
    def test_failed_result_stores_the_reason(self, worker_client, leased):
        run, generation = leased

        response = post_result(
            worker_client,
            run.id,
            generation,
            status="failed",
            conclusion="",
            failure_code="git_auth_failed",
            failure_message="The repository rejected the credentials.",
        )

        assert response.status_code == status.HTTP_200_OK
        run.refresh_from_db()
        assert (run.status, run.failure_code) == ("failed", "git_auth_failed")
        assert run.failure_message == "The repository rejected the credentials."
        comment = IssueComment.objects.get(pk=run.conclusion_comment_id)
        assert comment.comment_html == (
            f"<p><strong>Run {run.short_id} failed: The repository rejected the credentials.</strong></p>"
        )
        assert AgentRunTurn.objects.get(run=run).status == "failed"

    @pytest.mark.django_db
    def test_failed_result_needs_a_failure_code(self, worker_client, leased):
        run, generation = leased

        response = post_result(worker_client, run.id, generation, status="failed", conclusion="")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
class TestHarnessVersionUnverified:
    def fail_with_version(self, worker_client, run, generation, failed_check):
        return post_result(
            worker_client,
            run.id,
            generation,
            status="failed",
            conclusion="",
            failure_code="harness_version_unverified",
            failure_message="Claude Code 2.2.0 failed the progress check.",
            harness_version="2.2.0",
            failed_check=failed_check,
        )

    @pytest.mark.django_db
    def test_connected_connection_becomes_failed_with_the_check(self, worker_client, leased, run_setup):
        run, generation = leased

        response = self.fail_with_version(worker_client, run, generation, "progress")

        assert response.status_code == status.HTTP_200_OK
        connection = connection_of(run_setup.agent)
        assert (connection.state, connection.missing_action) == ("failed", "progress")
        assert connection.failure_hint == (
            "Claude Code 2.2.0 failed the progress check in a Run. Retry the connection."
        )

    @pytest.mark.django_db
    def test_unknown_check_gives_harness_version_unverified(self, worker_client, leased, run_setup):
        run, generation = leased

        self.fail_with_version(worker_client, run, generation, "something_new")

        connection = connection_of(run_setup.agent)
        assert (connection.state, connection.missing_action) == ("failed", "harness_version_unverified")

    @pytest.mark.django_db
    def test_connecting_connection_is_left_unchanged(self, worker_client, leased, run_setup):
        run, generation = leased
        AgentConnection.objects.filter(agent=run_setup.agent).update(state="connecting", missing_action="")

        self.fail_with_version(worker_client, run, generation, "progress")

        connection = connection_of(run_setup.agent)
        assert (connection.state, connection.missing_action, connection.failure_hint) == ("connecting", "", "")

    @pytest.mark.django_db
    def test_other_failure_codes_leave_the_connection_connected(self, worker_client, leased, run_setup):
        run, generation = leased

        post_result(
            worker_client, run.id, generation, status="failed", conclusion="", failure_code="sandbox_unavailable"
        )

        assert connection_of(run_setup.agent).state == "connected"
