# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The terminal result of a Run: one conclusion comment by the Agent bot user.

The result is applied once. A repeated result for a finished Run returns the
stored outcome and writes nothing, so a Worker can retry safely.
"""

# Python imports
from html import escape

# Third party imports
from crum import impersonate

# Django imports
from django.db import transaction
from django.utils import timezone

# Module imports
from plane.agent.services import harness_probe, lease, run_events
from plane.db.models import AgentRun, AgentRunEventKind, AgentRunStatus, AgentRunTurn, AgentRunTurnStatus, IssueComment

HARNESS_VERSION_UNVERIFIED = "harness_version_unverified"


def conclusion_html(run, status, conclusion, failure_message):
    if status == AgentRunStatus.COMPLETED:
        heading = f"Answer from {run.agent_name} (Run {run.short_id})"
    else:
        heading = f"Run {run.short_id} failed: {failure_message}"
    paragraphs = [part.strip() for part in conclusion.replace("\r\n", "\n").split("\n\n") if part.strip()]
    body = "".join(f"<p>{escape(part).replace(chr(10), '<br />')}</p>" for part in paragraphs)
    return f"<p><strong>{escape(heading)}</strong></p>{body}"


def result_body(run):
    return {"status": run.status, "conclusion_comment_id": run.conclusion_comment_id}


def apply_result(worker, run_id, result):
    """Finish a leased Run with a validated ``result``. Returns the response body."""
    with transaction.atomic():
        run = AgentRun.objects.select_for_update().select_related("agent__bot_user").get(pk=run_id)
        if run.status in lease.FINISHED_STATUSES:
            return result_body(run)
        lease.check_lease(run, worker, result["lease_generation"])

        status = result["status"]
        now = timezone.now()
        bot_user = run.agent.bot_user
        # The bot user writes the comment, so it is also the audit user of the comment and its description.
        with impersonate(bot_user):
            comment = IssueComment.objects.create(
                workspace_id=run.workspace_id,
                project_id=run.project_id,
                issue_id=run.issue_id,
                actor=bot_user,
                comment_html=conclusion_html(run, status, result["conclusion"], result["failure_message"]),
            )
        run.status = status
        run.ended_at = now
        run.conclusion_comment = comment
        if status == AgentRunStatus.FAILED:
            run.failure_code = result["failure_code"]
            run.failure_message = result["failure_message"]
        run.save(
            update_fields=["status", "ended_at", "conclusion_comment", "failure_code", "failure_message"],
            disable_auto_set_user=True,
        )
        turn = AgentRunTurn.objects.filter(run=run, lease_generation=run.lease_generation).order_by("-index").first()
        if turn is not None:
            turn.status = (
                AgentRunTurnStatus.COMPLETED if status == AgentRunStatus.COMPLETED else AgentRunTurnStatus.FAILED
            )
            turn.ended_at = now
            turn.driver_session_ref = result["session_ref"]
            turn.save(update_fields=["status", "ended_at", "driver_session_ref"], disable_auto_set_user=True)
        run_events.append_locked(
            run,
            [
                {
                    "source_key": "conclusion",
                    "kind": AgentRunEventKind.CONCLUSION,
                    "payload": {"text": result["conclusion"], "comment_id": str(comment.id), "status": status},
                }
            ],
            turn,
        )
        if status == AgentRunStatus.FAILED and result["failure_code"] == HARNESS_VERSION_UNVERIFIED:
            harness_probe.mark_version_unverified(run.agent, result["harness_version"], result["failed_check"])
    return result_body(run)
