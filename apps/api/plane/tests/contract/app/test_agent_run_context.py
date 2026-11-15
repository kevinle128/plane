# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from plane.db.models import AgentRunContextSnapshot, IssueComment, User
from plane.tests.agent_run_fixtures import (
    claim_run,
    create_run,
    make_issue,
    worker_run_url,
)


def old_comment(issue, author, html, minutes_ago):
    comment = IssueComment.objects.create(
        workspace=issue.workspace, project=issue.project, issue=issue, actor=author, comment_html=html
    )
    IssueComment.objects.filter(pk=comment.pk).update(created_at=timezone.now() - timedelta(minutes=minutes_ago))
    comment.refresh_from_db()
    return comment


def context_of(run):
    return AgentRunContextSnapshot.objects.get(run=run, version=1)


@pytest.mark.contract
class TestContextSnapshot:
    @pytest.mark.django_db
    def test_snapshot_has_exact_ids_and_only_this_issue(self, session_client, worker_client, run_setup):
        setup = run_setup
        teammate = User.objects.create(email="teammate@plane.so", username="teammate", display_name="Tea")
        first = old_comment(setup.issue, teammate, "<p>First note</p>", 10)
        second = old_comment(setup.issue, setup.user, "<p>Second note</p>", 5)
        other_issue = make_issue(setup.project, name="Other issue")
        old_comment(other_issue, setup.user, "<p>OTHER-ISSUE-SECRET</p>", 7)
        # An earlier Run of the same issue with a timeline message that must not leak into the next context.
        earlier = create_run(session_client, setup, text="Earlier question")
        earlier_claim = claim_run(worker_client)
        worker_client.post(
            worker_run_url(earlier.id, "events"),
            {
                "lease_generation": earlier_claim["lease_generation"],
                "turn_index": 0,
                "events": [
                    {
                        "source_key": "m1",
                        "kind": "message",
                        "payload": {"role": "assistant", "text": "RUN-EVENT-SECRET"},
                    }
                ],
            },
            format="json",
        )

        run = create_run(session_client, setup, text="Why does login fail?")

        payload = context_of(run).payload
        workspace, project, issue = setup.workspace, setup.project, setup.issue
        assert payload["workspace"] == {"id": str(workspace.id), "slug": workspace.slug, "name": workspace.name}
        assert payload["project"] == {"id": str(project.id), "identifier": "AGT", "name": project.name}
        assert payload["issue"]["id"] == str(issue.id)
        assert payload["issue"]["identifier"] == f"AGT-{issue.sequence_id}"
        assert payload["issue"]["sequence_id"] == issue.sequence_id
        assert payload["issue"]["url"].endswith(f"/{workspace.slug}/projects/{project.id}/issues/{issue.id}")
        assert payload["issue"]["title"] == "Login fails after reset"
        assert payload["issue"]["description"] == "Users cannot log in."
        assert payload["issue"]["state"] == {"name": "Todo", "group": "unstarted"}
        assert payload["repository"] == {
            "provider": "github",
            "host": "github.com",
            "full_name": setup.binding.full_name,
            "default_branch": "main",
            "base_ref": "main",
        }
        assert payload["requester"] == {"id": str(setup.user.id), "display_name": setup.user.display_name}
        assert payload["agent"] == {
            "id": str(setup.agent.id),
            "name": "Claude Code",
            "handle": "Claude",
            "instructions": "",
        }
        assert payload["trigger_comment"]["id"] == str(run.trigger_comment_id)
        assert payload["trigger_comment"]["text"] == "Why does login fail?"
        assert payload["trigger_comment"]["author"] == {
            "id": str(setup.user.id),
            "display_name": setup.user.display_name,
        }
        assert [comment["id"] for comment in payload["comments"]] == [
            str(first.id),
            str(second.id),
            str(earlier.trigger_comment_id),
        ]
        assert payload["comments"][0]["author"] == {"id": str(teammate.id), "display_name": "Tea"}
        assert payload["comments"][0]["text"] == "First note"
        assert payload["omitted_comment_count"] == 0
        assert "OTHER-ISSUE-SECRET" not in str(payload)
        assert "RUN-EVENT-SECRET" not in str(payload)

    @pytest.mark.django_db
    def test_oldest_comments_are_dropped_first_and_counted(self, session_client, run_setup):
        texts = ["a" * 25_000, "b" * 25_000, "c" * 25_000]
        comments = [
            old_comment(run_setup.issue, run_setup.user, f"<p>{text}</p>", 30 - index)
            for index, text in enumerate(texts)
        ]

        run = create_run(session_client, run_setup)

        snapshot = context_of(run)
        assert snapshot.omitted_comment_count == 1
        assert snapshot.payload["omitted_comment_count"] == 1
        assert [comment["id"] for comment in snapshot.payload["comments"]] == [
            str(comments[1].id),
            str(comments[2].id),
        ]


@pytest.mark.contract
class TestWorkerContext:
    @pytest.mark.django_db
    def test_worker_reads_the_snapshot_with_its_lease(self, session_client, worker_client, run_setup):
        run = create_run(session_client, run_setup)
        claimed = claim_run(worker_client)

        response = worker_client.get(
            worker_run_url(run.id, "context"), {"lease_generation": claimed["lease_generation"]}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["version"] == 1
        assert response.data["omitted_comment_count"] == 0
        assert response.data["payload"] == context_of(run).payload

    @pytest.mark.django_db
    def test_old_generation_gets_409(self, session_client, worker_client, run_setup):
        run = create_run(session_client, run_setup)
        claimed = claim_run(worker_client)

        response = worker_client.get(
            worker_run_url(run.id, "context"), {"lease_generation": claimed["lease_generation"] + 1}
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data == {"error": "lease_superseded"}

    @pytest.mark.django_db
    def test_unclaimed_run_gets_409(self, session_client, worker_client, run_setup):
        run = create_run(session_client, run_setup)

        response = worker_client.get(worker_run_url(run.id, "context"), {"lease_generation": 1})

        assert response.status_code == status.HTTP_409_CONFLICT
