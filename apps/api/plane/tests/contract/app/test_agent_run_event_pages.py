# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.db.models import AgentRun, AgentRunEvent, AgentRunTurn
from plane.tests.agent_run_fixtures import (
    claim_run,
    create_run,
    make_issue,
    runs_url,
)


def events_page(client, issue, run_id, **params):
    return client.get(runs_url(issue, run_id, "events"), params)


def add_events(run, count):
    """Store ``count`` Worker events after the trigger event (seq 1)."""
    turn = AgentRunTurn.objects.filter(run=run, index=0).first()
    AgentRunEvent.objects.bulk_create(
        [
            AgentRunEvent(run=run, seq=seq, source_key=f"e{seq}", turn=turn, kind="message", payload={"text": str(seq)})
            for seq in range(2, count + 2)
        ]
    )
    AgentRun.objects.filter(pk=run.pk).update(next_event_seq=count + 2)


@pytest.mark.contract
class TestMemberEventsPage:
    @pytest.mark.django_db
    def test_first_page_has_the_trigger_event(self, session_client, run_setup):
        run = create_run(session_client, run_setup)

        response = events_page(session_client, run_setup.issue, run.id)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["has_more"] is False
        assert response.data["next_after"] == 1
        (row,) = response.data["events"]
        assert set(row) == {"id", "seq", "kind", "payload", "turn_index", "created_at"}
        assert (row["seq"], row["kind"], row["turn_index"]) == (1, "message", None)
        assert row["payload"]["text"] == "What does the login view do?"

    @pytest.mark.django_db
    def test_cursor_pages_are_stable_across_1000_events(self, session_client, worker_client, run_setup):
        run = create_run(session_client, run_setup)
        claim_run(worker_client)
        add_events(run, 999)
        seen = []
        after = 0
        pages = 0

        while True:
            response = events_page(session_client, run_setup.issue, run.id, after=after, limit=137)
            assert response.status_code == status.HTTP_200_OK
            seqs = [row["seq"] for row in response.data["events"]]
            assert seqs == sorted(seqs)
            seen.extend(seqs)
            pages += 1
            if seqs:
                assert response.data["next_after"] == seqs[-1]
            after = response.data["next_after"]
            if not response.data["has_more"]:
                break

        assert seen == list(range(1, 1001))
        assert pages == 8
        assert events_page(session_client, run_setup.issue, run.id, after=1000).data == {
            "events": [],
            "next_after": 1000,
            "has_more": False,
        }

    @pytest.mark.django_db
    def test_limit_is_capped_at_200_and_defaults_to_100(self, session_client, run_setup):
        run = create_run(session_client, run_setup)
        add_events(run, 499)

        capped = events_page(session_client, run_setup.issue, run.id, limit=5000)
        default = events_page(session_client, run_setup.issue, run.id)

        assert len(capped.data["events"]) == 200
        assert capped.data["has_more"] is True
        assert len(default.data["events"]) == 100
        assert default.data["next_after"] == 100

    @pytest.mark.django_db
    @pytest.mark.parametrize("params", [{"after": "x"}, {"after": -1}, {"limit": 0}, {"limit": "many"}])
    def test_invalid_cursor_gets_400(self, session_client, run_setup, params):
        run = create_run(session_client, run_setup)

        response = events_page(session_client, run_setup.issue, run.id, **params)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_events_of_a_run_of_another_issue_are_not_readable(self, session_client, run_setup):
        run = create_run(session_client, run_setup)
        other = make_issue(run_setup.project, name="Other issue")

        response = events_page(session_client, other, run.id)

        assert response.status_code == status.HTTP_404_NOT_FOUND
