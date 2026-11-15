# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Append-only Run timeline.

Plane assigns ``seq`` in input order from ``AgentRun.next_event_seq`` while
it holds the Run row lock, so sequence numbers have no gap and no duplicate.
A ``source_key`` that the Run already has returns the stored event and takes
no new ``seq``, so a Worker can resend a batch safely.
"""

# Django imports
from django.db import transaction
from django.utils import timezone

# Module imports
from plane.agent.services import lease
from plane.db.models import AgentRunEvent, AgentRunTurn


class TurnNotFound(Exception):
    pass


def append_locked(run, items, turn=None):
    """Append ``items`` (``source_key``, ``kind``, ``payload``) to a Run the caller has locked.

    Returns one event per item, in input order.
    """
    keys = [item["source_key"] for item in items]
    by_key = {event.source_key: event for event in AgentRunEvent.objects.filter(run=run, source_key__in=keys)}
    new_events = []
    for item in items:
        if item["source_key"] in by_key:
            continue
        event = AgentRunEvent(
            run=run,
            seq=run.next_event_seq,
            source_key=item["source_key"],
            turn=turn,
            kind=item["kind"],
            payload=item["payload"],
        )
        run.next_event_seq += 1
        by_key[event.source_key] = event
        new_events.append(event)
    if new_events:
        # bulk_create skips save(), so no audit column is taken from a Worker request.
        AgentRunEvent.objects.bulk_create(new_events)
        run.save(update_fields=["next_event_seq"], disable_auto_set_user=True)
    return [by_key[key] for key in keys]


def append_from_worker(worker, run_id, generation, turn_index, items):
    """Append Worker events. Progress also extends the lease."""
    with transaction.atomic():
        run = lease.locked_run(worker, run_id, generation)
        turn = AgentRunTurn.objects.filter(run=run, index=turn_index).first()
        if turn is None:
            raise TurnNotFound
        events = append_locked(run, items, turn)
        now = timezone.now()
        run.last_progress_at = now
        run.lease_expires_at = lease.lease_end(now)
        run.save(update_fields=["last_progress_at", "lease_expires_at"], disable_auto_set_user=True)
    return events
