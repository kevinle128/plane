# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Read-only Run views for members who can read the work item."""

# Django imports
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.agent.services.lease import is_stale
from plane.app.permissions import ROLE, allow_permission, issue_hidden_from_guest
from plane.app.views.base import BaseAPIView
from plane.app.views.issue.relation import issue_in_project
from plane.db.models import AgentRun


def run_view(run, now):
    return {
        "id": str(run.id),
        "short_id": run.short_id,
        "status": "stale" if is_stale(run, now) else run.status,
        "agent": {"id": str(run.agent_id), "name": run.agent_name, "handle": run.agent_handle, "harness": run.harness},
        "requester_id": str(run.requester_id),
        "trigger_comment_id": str(run.trigger_comment_id),
        "conclusion_comment_id": str(run.conclusion_comment_id) if run.conclusion_comment_id else None,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "ended_at": run.ended_at,
        "last_progress_at": run.last_progress_at,
        "failure_code": run.failure_code,
        "failure_message": run.failure_message,
        "provider": run.provider,
        "repository_full_name": run.full_name,
        "clone_path": run.clone_path,
        "model": run.model,
        # Sequence numbers have no gap, so the count needs no query.
        "event_count": run.next_event_seq - 1,
        "sandbox": "read_only",
    }


class IssueRunBaseEndpoint(BaseAPIView):
    def issue_error(self, request, slug, project_id, issue_id):
        """The same visibility rule as the issue comment list."""
        if not issue_in_project(issue_id, slug, project_id, include_archived=True):
            return Response({"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND)
        if issue_hidden_from_guest(request, slug, project_id, issue_id):
            return Response({"error": "You are not allowed to view this issue"}, status=status.HTTP_403_FORBIDDEN)
        return None

    def runs(self, slug, project_id, issue_id):
        return AgentRun.objects.filter(workspace__slug=slug, project_id=project_id, issue_id=issue_id)


class IssueRunsEndpoint(IssueRunBaseEndpoint):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, issue_id):
        error = self.issue_error(request, slug, project_id, issue_id)
        if error:
            return error
        now = timezone.now()
        runs = self.runs(slug, project_id, issue_id).order_by("created_at")
        return Response([run_view(run, now) for run in runs], status=status.HTTP_200_OK)


class IssueRunDetailEndpoint(IssueRunBaseEndpoint):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, issue_id, run_id):
        error = self.issue_error(request, slug, project_id, issue_id)
        if error:
            return error
        run = self.runs(slug, project_id, issue_id).filter(pk=run_id).first()
        if run is None:
            return Response({"error": "Run not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(run_view(run, timezone.now()), status=status.HTTP_200_OK)
