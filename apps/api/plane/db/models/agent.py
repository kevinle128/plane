# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Workspace Agents for local CLI Harnesses, their connection state and the Worker identity.

Each workspace has one ``Agent`` per Harness. Each Agent owns one bot ``User``
that writes its comments; the bot user is not a workspace member. The
connection state is written only by Plane: from an admin action or from a
Worker probe report for the current probe generation.
"""

# Django imports
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

# Module imports
from .base import BaseModel


class AgentHarness(models.TextChoices):
    CLAUDE_CODE = "claude_code", "Claude Code"
    CODEX = "codex", "Codex CLI"
    OMP = "omp", "Omp"


class AgentConnectionState(models.TextChoices):
    NOT_CONNECTED = "not_connected", "Not connected"
    CONNECTING = "connecting", "Connecting"
    CONNECTED = "connected", "Connected"
    FAILED = "failed", "Connection failed"


class AgentWorker(BaseModel):
    """A Worker process on the Mini. Only the SHA-256 hash of its token is stored."""

    name = models.CharField(max_length=64)
    token_hash = models.CharField(max_length=64, unique=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Agent Worker"
        verbose_name_plural = "Agent Workers"
        db_table = "agent_workers"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=Q(deleted_at__isnull=True),
                name="agent_worker_unique_name",
            )
        ]

    def __str__(self):
        return self.name


class Agent(BaseModel):
    """The mentionable identity of one Harness in one workspace."""

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="agents")
    harness = models.CharField(max_length=32, choices=AgentHarness.choices)
    name = models.CharField(max_length=64)
    handle = models.CharField(max_length=32)
    instructions = models.TextField(blank=True, default="")
    mentionable = models.BooleanField(default=True)
    selected_model = models.CharField(max_length=128, blank=True, default="")
    bot_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="agent")

    class Meta:
        verbose_name = "Agent"
        verbose_name_plural = "Agents"
        db_table = "agents"
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "harness"],
                condition=Q(deleted_at__isnull=True),
                name="agent_unique_workspace_harness",
            ),
            models.UniqueConstraint(
                Lower("handle"),
                "workspace",
                condition=Q(deleted_at__isnull=True),
                name="agent_unique_workspace_handle_ci",
            ),
        ]

    def __str__(self):
        return f"{self.harness} agent of {self.workspace_id}"


class AgentConnection(BaseModel):
    """Connection state of one Agent, from its latest probe generation."""

    agent = models.OneToOneField(Agent, on_delete=models.CASCADE, related_name="connection")
    state = models.CharField(
        max_length=32,
        choices=AgentConnectionState.choices,
        default=AgentConnectionState.NOT_CONNECTED,
    )
    probe_generation = models.PositiveIntegerField(default=0)
    probe_requested_at = models.DateTimeField(null=True, blank=True)
    probe_claimed_at = models.DateTimeField(null=True, blank=True)
    probe_worker = models.ForeignKey(
        AgentWorker,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claimed_probes",
    )
    harness_version = models.CharField(max_length=64, blank=True, default="")
    location = models.CharField(max_length=1024, blank=True, default="")
    # Named so it does not shadow ``django.db.models`` in the class body; the API field is ``models``.
    reported_models = models.JSONField(default=list, blank=True)
    capabilities = models.JSONField(default=dict, blank=True)
    checks = models.JSONField(default=list, blank=True)
    missing_action = models.CharField(max_length=64, blank=True, default="")
    failure_hint = models.TextField(blank=True, default="")
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Agent Connection"
        verbose_name_plural = "Agent Connections"
        db_table = "agent_connections"
        ordering = ("created_at",)
        indexes = [models.Index(fields=["state", "probe_requested_at"], name="agent_connection_probe_idx")]

    def __str__(self):
        return f"{self.state} connection of agent {self.agent_id}"
