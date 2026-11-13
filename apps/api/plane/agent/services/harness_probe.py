# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Harness connection probes.

Connect or Retry sets ``connecting`` and starts a new probe generation. A Worker
claims the probe, runs it on the Mini and posts a versioned report. Plane fences
the report by generation, claimant and answer deadline, and decides
``connected`` itself from the reported checks and models: the Worker sends
evidence, not a verdict.
"""

# Python imports
from datetime import timedelta

# Django imports
from django.db import transaction
from django.utils import timezone

# Module imports
from plane.agent.services.agent_settings import PROBE_ANSWER_SECONDS, is_probe_expired
from plane.db.models import Agent, AgentConnection, AgentConnectionState, AgentHarness

# Harnesses with a Worker probe. The other Harnesses can be configured but not connected yet.
PROBE_HARNESSES = frozenset({AgentHarness.CLAUDE_CODE})

# Every check must pass before a Harness reads as connected. The order is the order of the missing action.
REQUIRED_CHECKS = (
    "authentication",
    "model_report",
    "follow_up",
    "progress",
    "interruption",
    "permission",
    "recovery",
)

CAPABILITY_FLAGS = ("midturn_input", "native_resume", "permission_prompt")

# Problems that stop the probe before any check can run.
BLOCKING_ISSUES = ("harness_not_found", "unsupported_version")


class ProbeConflict(Exception):
    """A request that the current probe state does not allow. ``code`` is the API error code."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _reset_report(connection):
    connection.harness_version = ""
    connection.location = ""
    connection.reported_models = []
    connection.capabilities = {}
    connection.checks = []
    connection.missing_action = ""
    connection.failure_hint = ""
    connection.verified_at = None
    connection.probe_claimed_at = None
    connection.probe_worker = None


def request_probe(agent):
    """Start a new probe generation. Any report for an older generation is rejected later."""
    if agent.harness not in PROBE_HARNESSES:
        raise ProbeConflict("harness_probe_unavailable")
    with transaction.atomic():
        connection = AgentConnection.objects.select_for_update().get(agent=agent)
        _reset_report(connection)
        connection.state = AgentConnectionState.CONNECTING
        connection.probe_generation += 1
        connection.probe_requested_at = timezone.now()
        connection.save()
    return connection


def disconnect(agent):
    """Stop using the Harness. The generation moves on, so an in-flight report cannot connect it again."""
    with transaction.atomic():
        connection = AgentConnection.objects.select_for_update().get(agent=agent)
        _reset_report(connection)
        connection.state = AgentConnectionState.NOT_CONNECTED
        connection.probe_generation += 1
        connection.probe_requested_at = None
        connection.save()
    return connection


def claim_probe(worker, harnesses):
    """Give the oldest pending, unclaimed and unexpired probe for one of ``harnesses`` to ``worker``."""
    now = timezone.now()
    oldest_request = now - timedelta(seconds=PROBE_ANSWER_SECONDS)
    with transaction.atomic():
        connection = (
            AgentConnection.objects.select_for_update(skip_locked=True, of=("self",))
            .select_related("agent")
            .filter(
                state=AgentConnectionState.CONNECTING,
                probe_claimed_at__isnull=True,
                probe_requested_at__gte=oldest_request,
                agent__harness__in=[harness for harness in harnesses if harness in PROBE_HARNESSES],
                agent__deleted_at__isnull=True,
            )
            .order_by("probe_requested_at")
            .first()
        )
        if connection is None:
            return None
        # A Worker is not a User, so the audit columns are not set from the request.
        connection.probe_claimed_at = now
        connection.probe_worker = worker
        connection.save(update_fields=["probe_claimed_at", "probe_worker"], disable_auto_set_user=True)
    return connection


def _missing_action(checks, models, blocking_issue):
    if blocking_issue:
        return blocking_issue
    passed = {check["name"] for check in checks if check["passed"]}
    for name in REQUIRED_CHECKS:
        if name not in passed:
            return name
    if not models:
        return "model_report"
    return ""


def apply_report(worker, probe_id, report):
    """Apply a validated report to the probe ``probe_id``. Raises ``ProbeConflict`` when it is not current."""
    with transaction.atomic():
        connection = AgentConnection.objects.select_for_update().get(pk=probe_id, agent__deleted_at__isnull=True)
        if connection.probe_generation != report["generation"]:
            raise ProbeConflict("probe_superseded")
        if connection.state != AgentConnectionState.CONNECTING:
            raise ProbeConflict("probe_not_pending")
        if connection.probe_worker_id != worker.id:
            raise ProbeConflict("probe_not_claimed")
        if is_probe_expired(connection):
            raise ProbeConflict("probe_expired")

        missing_action = _missing_action(report["checks"], report["models"], report.get("blocking_issue"))
        connected = missing_action == ""
        connection.state = AgentConnectionState.CONNECTED if connected else AgentConnectionState.FAILED
        connection.missing_action = missing_action
        connection.harness_version = report["harness_version"]
        connection.location = report["location"]
        connection.checks = report["checks"]
        connection.capabilities = report["capabilities"]
        connection.failure_hint = report["failure_hint"]
        # Models are usable only from a verified Harness; a failed probe shows none.
        connection.reported_models = report["models"] if connected else []
        connection.verified_at = timezone.now() if connected else None
        connection.save(disable_auto_set_user=True)
        if connected:
            # A model the Harness no longer reports cannot stay selected; new Runs then use the Harness default.
            reported = {model["id"] for model in connection.reported_models}
            Agent.objects.filter(pk=connection.agent_id).exclude(selected_model="").exclude(
                selected_model__in=reported
            ).update(selected_model="")
    return connection
