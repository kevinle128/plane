# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Worker endpoints (``api/agent-worker/v1/``).

These views do not extend ``BaseAPIView``: they accept only the Worker token
and have no throttle, because a polling Worker calls them more often than the
API-key limit allows. The Worker principal is not a ``User``, so writes made
here never take audit columns from the request.
"""

# Django imports
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

# Module imports
from plane.agent.services import harness_probe
from plane.agent.worker_api.authentication import IsAgentWorker, WorkerTokenAuthentication
from plane.agent.services.agent_settings import probe_answer_deadline
from plane.agent.worker_api.serializers import HeartbeatSerializer, ProbeClaimSerializer, ProbeReportSerializer
from plane.db.models import AgentConnection, AgentWorker


class WorkerAPIView(APIView):
    authentication_classes = [WorkerTokenAuthentication]
    permission_classes = [IsAgentWorker]
    throttle_classes = []

    @property
    def worker(self):
        return self.request.user.worker


class WorkerHeartbeatEndpoint(WorkerAPIView):
    def post(self, request):
        serializer = HeartbeatSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        now = timezone.now()
        AgentWorker.objects.filter(pk=self.worker.pk).update(last_seen_at=now)
        body = {"worker": self.worker.name, "server_time": now}
        probe = serializer.validated_data.get("probe")
        if probe is not None:
            body["probe_current"] = harness_probe.is_probe_current(self.worker, probe["id"], probe["generation"])
        return Response(body, status=status.HTTP_200_OK)


class WorkerProbeClaimEndpoint(WorkerAPIView):
    def post(self, request):
        serializer = ProbeClaimSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        connection = harness_probe.claim_probe(self.worker, serializer.validated_data["harnesses"])
        if connection is None:
            return Response({"probe": None}, status=status.HTTP_200_OK)
        return Response(
            {
                "probe": {
                    "id": str(connection.id),
                    "harness": connection.agent.harness,
                    "generation": connection.probe_generation,
                    "requested_at": connection.probe_requested_at,
                    "deadline": probe_answer_deadline(connection),
                    "seconds_left": harness_probe.seconds_left(connection),
                }
            },
            status=status.HTTP_200_OK,
        )


class WorkerProbeReportEndpoint(WorkerAPIView):
    def post(self, request, probe_id):
        serializer = ProbeReportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            connection = harness_probe.apply_report(self.worker, probe_id, serializer.validated_data)
        except AgentConnection.DoesNotExist:
            return Response({"error": "probe_not_found"}, status=status.HTTP_404_NOT_FOUND)
        except harness_probe.ProbeConflict as conflict:
            return Response({"error": conflict.code}, status=status.HTTP_409_CONFLICT)
        return Response(
            {"state": connection.state, "missing_action": connection.missing_action}, status=status.HTTP_200_OK
        )
