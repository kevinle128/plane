# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import threading
from datetime import timedelta

import pytest
from django.db import connection as db_connection
from django.utils import timezone
from rest_framework import status

from plane.db.models import AgentRun, AgentRunEvent
from plane.tests.agent_run_fixtures import (
    claim_run,
    create_run,
    worker_run_url,
)
from plane.tests.agent_settings_fixtures import worker_client_for


def event(source_key, kind="message", **payload):
    return {"source_key": source_key, "kind": kind, "payload": payload or {"role": "assistant", "text": source_key}}


def post_events(worker_client, run_id, generation, events, turn_index=0):
    return worker_client.post(
        worker_run_url(run_id, "events"),
        {"lease_generation": generation, "turn_index": turn_index, "events": events},
        format="json",
    )


@pytest.fixture
def leased(session_client, worker_client, run_setup):
    run = create_run(session_client, run_setup)
    return run, claim_run(worker_client)["lease_generation"]


@pytest.mark.contract
class TestAppendEvents:
    @pytest.mark.django_db
    def test_events_get_sequence_numbers_in_input_order(self, worker_client, leased):
        run, generation = leased
        AgentRun.objects.filter(pk=run.pk).update(lease_expires_at=timezone.now() + timedelta(seconds=5))

        response = post_events(
            worker_client,
            run.id,
            generation,
            [
                event("status-1", "status", code="cloning", text="Cloning"),
                event("tool-1", "tool_call", call_id="c1", name="Read", input={"path": "README.md"}),
                event("msg-1"),
            ],
        )

        assert response.status_code == status.HTTP_200_OK
        assert [(row["seq"], row["source_key"]) for row in response.data["events"]] == [
            (2, "status-1"),
            (3, "tool-1"),
            (4, "msg-1"),
        ]
        stored = AgentRunEvent.objects.get(run=run, seq=3)
        assert (stored.kind, stored.payload["name"], stored.turn.index) == ("tool_call", "Read", 0)
        run.refresh_from_db()
        assert run.next_event_seq == 5
        assert run.last_progress_at is not None
        assert run.lease_expires_at >= timezone.now() + timedelta(seconds=290)

    @pytest.mark.django_db
    def test_repeated_source_key_creates_one_event(self, worker_client, leased):
        run, generation = leased
        first = post_events(worker_client, run.id, generation, [event("msg-1")])

        again = post_events(worker_client, run.id, generation, [event("msg-1"), event("msg-2"), event("msg-2")])

        assert again.status_code == status.HTTP_200_OK
        assert again.data["events"][0] == first.data["events"][0]
        assert [row["seq"] for row in again.data["events"]] == [2, 3, 3]
        assert AgentRunEvent.objects.filter(run=run).count() == 3
        assert AgentRunEvent.objects.filter(run=run, source_key="msg-1").count() == 1

    @pytest.mark.django_db
    def test_old_generation_gets_409_and_stores_nothing(self, worker_client, leased):
        run, generation = leased
        AgentRun.objects.filter(pk=run.pk).update(lease_generation=generation + 1)

        response = post_events(worker_client, run.id, generation, [event("msg-1")])

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data == {"error": "lease_superseded"}
        assert AgentRunEvent.objects.filter(run=run).count() == 1

    @pytest.mark.django_db
    def test_unknown_turn_gets_400(self, worker_client, leased):
        run, generation = leased

        response = post_events(worker_client, run.id, generation, [event("msg-1")], turn_index=3)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {"error": "turn_not_found"}

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "events",
        [
            [],
            [event(f"m{index}") for index in range(101)],
            [event("big", text="x" * (64 * 1024))],
            [{"source_key": "c", "kind": "conclusion", "payload": {"text": "fake"}}],
            [{"source_key": "p", "kind": "message", "payload": ["not", "an", "object"]}],
            [{"source_key": "k" * 129, "kind": "message", "payload": {}}],
        ],
        ids=["empty", "too-many", "payload-too-large", "conclusion-kind", "payload-not-object", "key-too-long"],
    )
    def test_invalid_batch_gets_400(self, worker_client, leased, events):
        run, generation = leased

        response = post_events(worker_client, run.id, generation, events)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert AgentRunEvent.objects.filter(run=run).count() == 1


@pytest.mark.contract
class TestConcurrentAppend:
    @pytest.mark.django_db(transaction=True)
    def test_concurrent_batches_get_distinct_contiguous_sequence_numbers(
        self, session_client, worker_client, agent_worker, run_setup
    ):
        run = create_run(session_client, run_setup)
        generation = claim_run(worker_client)["lease_generation"]
        token = agent_worker[1]
        batches = 4
        barrier = threading.Barrier(batches)
        errors = []

        def send(batch):
            try:
                barrier.wait()
                response = post_events(
                    worker_client_for(token), run.id, generation, [event(f"b{batch}-e{index}") for index in range(5)]
                )
                assert response.status_code == status.HTTP_200_OK, response.data
            except Exception as error:  # noqa: BLE001 - collected and asserted below
                errors.append(error)
            finally:
                db_connection.close()

        threads = [threading.Thread(target=send, args=(batch,)) for batch in range(batches)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        seqs = list(AgentRunEvent.objects.filter(run=run).order_by("seq").values_list("seq", flat=True))
        assert seqs == list(range(1, 2 + batches * 5))
        assert AgentRun.objects.get(pk=run.pk).next_event_seq == 2 + batches * 5
