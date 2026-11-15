# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.agent.worker_api.views import (
    WorkerHeartbeatEndpoint,
    WorkerProbeClaimEndpoint,
    WorkerProbeReportEndpoint,
    WorkerRunClaimEndpoint,
    WorkerRunCloneEndpoint,
    WorkerRunContextEndpoint,
    WorkerRunEventsEndpoint,
    WorkerRunGitCredentialEndpoint,
    WorkerRunRenewEndpoint,
    WorkerRunResultEndpoint,
)

urlpatterns = [
    path("heartbeat/", WorkerHeartbeatEndpoint.as_view(), name="agent-worker-heartbeat"),
    path("probes/claim/", WorkerProbeClaimEndpoint.as_view(), name="agent-worker-probe-claim"),
    path(
        "probes/<uuid:probe_id>/report/",
        WorkerProbeReportEndpoint.as_view(),
        name="agent-worker-probe-report",
    ),
    path("runs/claim/", WorkerRunClaimEndpoint.as_view(), name="agent-worker-run-claim"),
    path("runs/<uuid:run_id>/renew/", WorkerRunRenewEndpoint.as_view(), name="agent-worker-run-renew"),
    path("runs/<uuid:run_id>/clone/", WorkerRunCloneEndpoint.as_view(), name="agent-worker-run-clone"),
    path(
        "runs/<uuid:run_id>/git-credential/",
        WorkerRunGitCredentialEndpoint.as_view(),
        name="agent-worker-run-git-credential",
    ),
    path("runs/<uuid:run_id>/context/", WorkerRunContextEndpoint.as_view(), name="agent-worker-run-context"),
    path("runs/<uuid:run_id>/events/", WorkerRunEventsEndpoint.as_view(), name="agent-worker-run-events"),
    path("runs/<uuid:run_id>/result/", WorkerRunResultEndpoint.as_view(), name="agent-worker-run-result"),
]
