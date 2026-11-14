# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Run leases held by a Worker.

A claim gives one ``created`` Run to one Worker and starts a new lease
generation. Every later Worker write names that generation; a write for
another generation or from another Worker is rejected with ``lease_superseded``,
and a write to a finished Run with ``run_finished``. A Worker is not a
``User``, so rows written here never take audit columns from the request.
"""

# Python imports
from datetime import timedelta

# Third party imports
from crum import impersonate

# Django imports
from django.db import transaction
from django.utils import timezone

# Module imports
from plane.agent.git_providers.base import ProviderError
from plane.agent.services import gitlab_connection
from plane.agent.services.git_connection import get_connection
from plane.db.models import (
    AgentConnectionState,
    AgentGitConnection,
    AgentGitProvider,
    AgentRun,
    AgentRunStatus,
    AgentRunTurn,
)

LEASE_SECONDS = 300
ACTIVE_STATUSES = (AgentRunStatus.IN_PROGRESS, AgentRunStatus.AWAITING)
FINISHED_STATUSES = (AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.STOPPED)


class LeaseConflict(Exception):
    """The Worker does not hold the current lease. ``code`` is the API error code."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def lease_end(now=None):
    return (now or timezone.now()) + timedelta(seconds=LEASE_SECONDS)


def is_stale(run, now=None):
    return (
        run.status in ACTIVE_STATUSES
        and run.lease_expires_at is not None
        and run.lease_expires_at < (now or timezone.now())
    )


def check_lease(run, worker, generation):
    """Raise ``LeaseConflict`` unless ``worker`` holds lease ``generation`` of an unfinished ``run``."""
    if run.status in FINISHED_STATUSES:
        raise LeaseConflict("run_finished")
    if run.status not in ACTIVE_STATUSES or run.lease_generation != generation or run.lease_worker_id != worker.id:
        raise LeaseConflict("lease_superseded")


def locked_run(worker, run_id, generation):
    """The Run row locked for update, after the lease check. Call inside a transaction."""
    run = AgentRun.objects.select_for_update().get(pk=run_id)
    check_lease(run, worker, generation)
    return run


def leased_run(worker, run_id, generation):
    """The Run after the lease check, without a lock (for reads)."""
    run = AgentRun.objects.get(pk=run_id)
    check_lease(run, worker, generation)
    return run


def claim_run(worker, harnesses):
    """Lease the oldest ``created`` Run of a listed Harness whose Agent is connected, or return ``None``."""
    now = timezone.now()
    with transaction.atomic():
        run = (
            AgentRun.objects.select_for_update(skip_locked=True, of=("self",))
            .filter(
                status=AgentRunStatus.CREATED,
                harness__in=harnesses,
                agent__deleted_at__isnull=True,
                agent__connection__state=AgentConnectionState.CONNECTED,
            )
            .order_by("created_at")
            .first()
        )
        if run is None:
            return None
        run.status = AgentRunStatus.IN_PROGRESS
        run.started_at = now
        run.lease_worker = worker
        run.lease_generation += 1
        run.lease_expires_at = lease_end(now)
        run.save(
            update_fields=["status", "started_at", "lease_worker", "lease_generation", "lease_expires_at"],
            disable_auto_set_user=True,
        )
        AgentRunTurn(run=run, index=0, lease_generation=run.lease_generation, started_at=now).save(
            disable_auto_set_user=True
        )
    return run


def renew(worker, run_id, generation):
    with transaction.atomic():
        run = locked_run(worker, run_id, generation)
        run.lease_expires_at = lease_end()
        run.save(update_fields=["lease_expires_at"], disable_auto_set_user=True)
    return run


def report_clone(worker, run_id, generation, report):
    """Store the clone path, and the Worker's last git result on the provider connection."""
    now = timezone.now()
    with transaction.atomic():
        run = locked_run(worker, run_id, generation)
        if report["ok"]:
            run.clone_path = report["clone_path"]
            run.save(update_fields=["clone_path"], disable_auto_set_user=True)
        connection = get_connection(run.workspace_id, run.provider) if run.provider else None
        if connection is not None:
            AgentGitConnection.objects.filter(pk=connection.pk).update(
                worker_last_error="" if report["ok"] else report["error_code"], worker_checked_at=now
            )
    return run


def clone_spec(run):
    """The neutral clone spec of a claimed Run. GitLab clones fetch a token from Plane; GitHub clones use the host."""
    connection = get_connection(run.workspace_id, run.provider)
    is_gitlab = run.provider == AgentGitProvider.GITLAB
    return {
        "provider": run.provider,
        "host": run.host,
        "clone_url": run.clone_url,
        "full_name": run.full_name,
        "external_repository_id": run.external_repository_id,
        "default_branch": run.default_branch,
        "base_ref": run.base_ref,
        "credential_mode": "plane_token" if is_gitlab else "host",
        "ca_bundle": (connection.ca_bundle or None) if is_gitlab and connection else None,
    }


def fetch_credential(worker, run_id, generation):
    """The GitLab token for one fetch of a leased Run. Never log the result.

    Raises ``LeaseConflict`` without the current lease and ``ProviderError``
    for a GitHub Run (``credential_mode_host``) or an unusable connection.
    """
    run = leased_run(worker, run_id, generation)
    if run.provider != AgentGitProvider.GITLAB:
        raise ProviderError("credential_mode_host", run.provider, http_status=400)
    connection = get_connection(run.workspace_id, run.provider)
    if connection is None:
        raise ProviderError("provider_disconnected", run.provider, http_status=409)
    # A Worker request has no User; a status change on the connection must not take one from the request.
    with impersonate(None):
        token = gitlab_connection.usable_token(connection.id)
    return {"username": "oauth2", "password": token}
