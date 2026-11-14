# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Agent Runs: one Run per mentioned Agent in a work-item comment, with its durable timeline.

Plane is the only writer of Run state. A Worker holds a Run through a lease;
every Worker write carries the lease generation, and an older generation is
rejected. ``stale`` is not stored: it is derived from an active status and an
expired lease.
"""

# Django imports
from django.conf import settings
from django.db import models
from django.db.models import Q

# Module imports
from .base import BaseModel


class AgentRunStatus(models.TextChoices):
    CREATED = "created", "Created"
    IN_PROGRESS = "in_progress", "In progress"
    AWAITING = "awaiting", "Awaiting"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    STOPPED = "stopped", "Stopped"


class AgentRunTurnStatus(models.TextChoices):
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class AgentRunEventKind(models.TextChoices):
    MESSAGE = "message", "Message"
    THOUGHT = "thought", "Thought"
    TOOL_CALL = "tool_call", "Tool call"
    TOOL_RESULT = "tool_result", "Tool result"
    PLAN = "plan", "Plan"
    QUESTION = "question", "Question"
    ERROR = "error", "Error"
    STATUS = "status", "Status"
    CONCLUSION = "conclusion", "Conclusion"


class AgentRun(BaseModel):
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="agent_runs")
    project = models.ForeignKey("db.Project", on_delete=models.CASCADE, related_name="agent_runs")
    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="agent_runs")
    agent = models.ForeignKey("db.Agent", on_delete=models.CASCADE, related_name="runs")
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_runs")
    trigger_comment = models.ForeignKey("db.IssueComment", on_delete=models.CASCADE, related_name="agent_runs")
    short_id = models.CharField(max_length=16)
    status = models.CharField(max_length=32, choices=AgentRunStatus.choices, default=AgentRunStatus.CREATED)

    # Agent settings at creation time; later setting changes apply only to new Runs.
    agent_name = models.CharField(max_length=64)
    agent_handle = models.CharField(max_length=32)
    harness = models.CharField(max_length=32)
    # An empty model means the Harness default.
    model = models.CharField(max_length=128, blank=True, default="")
    instructions = models.TextField(blank=True, default="")

    # Repository binding at creation time; blank when the project had no binding.
    provider = models.CharField(max_length=16, blank=True, default="")
    host = models.CharField(max_length=255, blank=True, default="")
    external_repository_id = models.CharField(max_length=64, blank=True, default="")
    full_name = models.CharField(max_length=512, blank=True, default="")
    clone_url = models.CharField(max_length=2048, blank=True, default="")
    default_branch = models.CharField(max_length=255, blank=True, default="")
    base_ref = models.CharField(max_length=255, blank=True, default="")

    clone_path = models.CharField(max_length=1024, blank=True, default="")
    lease_generation = models.PositiveIntegerField(default=0)
    lease_worker = models.ForeignKey(
        "db.AgentWorker", on_delete=models.SET_NULL, null=True, blank=True, related_name="leased_runs"
    )
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    last_progress_at = models.DateTimeField(null=True, blank=True)
    next_event_seq = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=64, blank=True, default="")
    failure_message = models.TextField(blank=True, default="")
    conclusion_comment = models.ForeignKey(
        "db.IssueComment", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "Agent Run"
        verbose_name_plural = "Agent Runs"
        db_table = "agent_runs"
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["trigger_comment", "agent"],
                condition=Q(deleted_at__isnull=True),
                name="agent_run_unique_trigger_comment_agent",
            ),
            models.UniqueConstraint(
                fields=["workspace", "short_id"],
                condition=Q(deleted_at__isnull=True),
                name="agent_run_unique_workspace_short_id",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"], name="agent_run_status_created_idx"),
            models.Index(fields=["issue", "created_at"], name="agent_run_issue_created_idx"),
        ]

    def __str__(self):
        return f"Run {self.short_id}"


class AgentRunContextSnapshot(BaseModel):
    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="context_snapshots")
    version = models.PositiveIntegerField(default=1)
    payload = models.JSONField(default=dict)
    omitted_comment_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Agent Run Context Snapshot"
        verbose_name_plural = "Agent Run Context Snapshots"
        db_table = "agent_run_context_snapshots"
        ordering = ("version",)

    def __str__(self):
        return f"Context v{self.version} of run {self.run_id}"


class AgentRunTurn(BaseModel):
    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="turns")
    index = models.PositiveIntegerField()
    status = models.CharField(max_length=32, choices=AgentRunTurnStatus.choices, default=AgentRunTurnStatus.RUNNING)
    lease_generation = models.PositiveIntegerField()
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    driver_session_ref = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        verbose_name = "Agent Run Turn"
        verbose_name_plural = "Agent Run Turns"
        db_table = "agent_run_turns"
        ordering = ("index",)
        constraints = [
            models.UniqueConstraint(
                fields=["run", "index"],
                condition=Q(deleted_at__isnull=True),
                name="agent_run_turn_unique_run_index",
            )
        ]

    def __str__(self):
        return f"Turn {self.index} of run {self.run_id}"


class AgentRunEvent(BaseModel):
    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="events")
    seq = models.PositiveIntegerField()
    source_key = models.CharField(max_length=128)
    turn = models.ForeignKey(AgentRunTurn, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    kind = models.CharField(max_length=32, choices=AgentRunEventKind.choices)
    payload = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Agent Run Event"
        verbose_name_plural = "Agent Run Events"
        db_table = "agent_run_events"
        ordering = ("seq",)
        constraints = [
            models.UniqueConstraint(fields=["run", "seq"], name="agent_run_event_unique_run_seq"),
            models.UniqueConstraint(fields=["run", "source_key"], name="agent_run_event_unique_run_source_key"),
        ]
        indexes = [models.Index(fields=["run", "seq"], name="agent_run_event_run_seq_idx")]

    def __str__(self):
        return f"Event {self.seq} of run {self.run_id}"
