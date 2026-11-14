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
from plane.agent.git_providers.base import ProviderError
from plane.agent.services import conclusion, harness_probe, lease, run_events
from plane.agent.worker_api.authentication import IsAgentWorker, WorkerTokenAuthentication
from plane.agent.services.agent_settings import probe_answer_deadline
from plane.agent.worker_api.serializers import (
    CloneReportSerializer,
    GitCredentialSerializer,
    HeartbeatSerializer,
    LeaseSerializer,
    ProbeClaimSerializer,
    ProbeReportSerializer,
    RunClaimSerializer,
    RunEventBatchSerializer,
    RunResultSerializer,
)
from plane.db.models import AgentConnection, AgentRun, AgentWorker


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


# Runs


def run_not_found():
    return Response({"error": "run_not_found"}, status=status.HTTP_404_NOT_FOUND)


def lease_conflict(conflict):
    return Response({"error": conflict.code}, status=status.HTTP_409_CONFLICT)


class WorkerRunClaimEndpoint(WorkerAPIView):
    def post(self, request):
        serializer = RunClaimSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        run = lease.claim_run(self.worker, serializer.validated_data["harnesses"])
        if run is None:
            return Response({"run": None}, status=status.HTTP_200_OK)
        run = AgentRun.objects.select_related("workspace", "project", "issue").get(pk=run.pk)
        return Response(
            {
                "run": {
                    "id": str(run.id),
                    "short_id": run.short_id,
                    "harness": run.harness,
                    "lease_generation": run.lease_generation,
                    "lease_expires_at": run.lease_expires_at,
                    "lease_seconds": lease.LEASE_SECONDS,
                    "model": run.model,
                    "instructions": run.instructions,
                    "agent": {"id": str(run.agent_id), "name": run.agent_name, "handle": run.agent_handle},
                    "workspace": {"id": str(run.workspace_id), "slug": run.workspace.slug},
                    "issue": {
                        "id": str(run.issue_id),
                        "identifier": f"{run.project.identifier}-{run.issue.sequence_id}",
                    },
                    "repository": lease.clone_spec(run),
                    "turn": {"index": 0},
                }
            },
            status=status.HTTP_200_OK,
        )


class WorkerRunRenewEndpoint(WorkerAPIView):
    def post(self, request, run_id):
        serializer = LeaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            run = lease.renew(self.worker, run_id, serializer.validated_data["lease_generation"])
        except AgentRun.DoesNotExist:
            return run_not_found()
        except lease.LeaseConflict as conflict:
            return lease_conflict(conflict)
        return Response({"lease_expires_at": run.lease_expires_at}, status=status.HTTP_200_OK)


class WorkerRunCloneEndpoint(WorkerAPIView):
    def post(self, request, run_id):
        serializer = CloneReportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        try:
            lease.report_clone(self.worker, run_id, data["lease_generation"], data)
        except AgentRun.DoesNotExist:
            return run_not_found()
        except lease.LeaseConflict as conflict:
            return lease_conflict(conflict)
        return Response({}, status=status.HTTP_200_OK)


class WorkerRunGitCredentialEndpoint(WorkerAPIView):
    """Hands out a GitLab token. The response carries a secret: never log it."""

    def post(self, request, run_id):
        serializer = GitCredentialSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            credential = lease.fetch_credential(self.worker, run_id, serializer.validated_data["lease_generation"])
        except AgentRun.DoesNotExist:
            return run_not_found()
        except lease.LeaseConflict as conflict:
            return lease_conflict(conflict)
        except ProviderError as error:
            return Response({"error": error.code}, status=error.http_status)
        return Response(credential, status=status.HTTP_200_OK)


class WorkerRunContextEndpoint(WorkerAPIView):
    def get(self, request, run_id):
        serializer = LeaseSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            run = lease.leased_run(self.worker, run_id, serializer.validated_data["lease_generation"])
        except AgentRun.DoesNotExist:
            return run_not_found()
        except lease.LeaseConflict as conflict:
            return lease_conflict(conflict)
        snapshot = run.context_snapshots.order_by("-version").first()
        if snapshot is None:
            return Response({"error": "context_not_found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "version": snapshot.version,
                "payload": snapshot.payload,
                "omitted_comment_count": snapshot.omitted_comment_count,
            },
            status=status.HTTP_200_OK,
        )


class WorkerRunEventsEndpoint(WorkerAPIView):
    def post(self, request, run_id):
        serializer = RunEventBatchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        try:
            events = run_events.append_from_worker(
                self.worker, run_id, data["lease_generation"], data["turn_index"], data["events"]
            )
        except AgentRun.DoesNotExist:
            return run_not_found()
        except lease.LeaseConflict as conflict:
            return lease_conflict(conflict)
        except run_events.TurnNotFound:
            return Response({"error": "turn_not_found"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"events": [{"id": str(event.id), "seq": event.seq, "source_key": event.source_key} for event in events]},
            status=status.HTTP_200_OK,
        )


class WorkerRunResultEndpoint(WorkerAPIView):
    def post(self, request, run_id):
        serializer = RunResultSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            body = conclusion.apply_result(self.worker, run_id, serializer.validated_data)
        except AgentRun.DoesNotExist:
            return run_not_found()
        except lease.LeaseConflict as conflict:
            return lease_conflict(conflict)
        return Response(body, status=status.HTTP_200_OK)
