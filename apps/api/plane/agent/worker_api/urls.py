# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.agent.worker_api.views import (
    WorkerHeartbeatEndpoint,
    WorkerProbeClaimEndpoint,
    WorkerProbeReportEndpoint,
)

urlpatterns = [
    path("heartbeat/", WorkerHeartbeatEndpoint.as_view(), name="agent-worker-heartbeat"),
    path("probes/claim/", WorkerProbeClaimEndpoint.as_view(), name="agent-worker-probe-claim"),
    path(
        "probes/<uuid:probe_id>/report/",
        WorkerProbeReportEndpoint.as_view(),
        name="agent-worker-probe-report",
    ),
]
