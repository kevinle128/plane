# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Provider-neutral Git connection models for local CLI agents.

Token columns hold Fernet ciphertext from ``encrypt_data``. They are never
serialized; see ``plane/app/serializers/agent_git.py``.
"""

# Django imports
from django.conf import settings
from django.db import models
from django.db.models import Q

# Module imports
from .base import BaseModel


class AgentGitProvider(models.TextChoices):
    GITHUB = "github", "GitHub"
    GITLAB = "gitlab", "GitLab"


class AgentGitConnectionStatus(models.TextChoices):
    CONNECTED = "connected", "Connected"
    DISCONNECTED = "disconnected", "Disconnected"
    RECONNECT_REQUIRED = "reconnect_required", "Reconnect required"


class AgentGitConnection(BaseModel):
    """One Git provider connection per workspace and provider."""

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="agent_git_connections")
    provider = models.CharField(max_length=16, choices=AgentGitProvider.choices)
    base_url = models.CharField(max_length=2048)
    host = models.CharField(max_length=255)
    ca_bundle = models.TextField(null=True, blank=True)
    account_external_id = models.CharField(max_length=255, blank=True, default="")
    account_login = models.CharField(max_length=255, blank=True, default="")
    account_is_bot = models.BooleanField(null=True, blank=True)
    access_token = models.TextField(blank=True, default="")
    refresh_token = models.TextField(blank=True, default="")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    token_name = models.CharField(max_length=255, blank=True, default="")
    token_scopes = models.JSONField(default=list, blank=True)
    server_version = models.CharField(max_length=64, blank=True, default="")
    connected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_git_connections_connected",
    )
    connected_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=AgentGitConnectionStatus.choices,
        default=AgentGitConnectionStatus.DISCONNECTED,
    )
    last_error = models.CharField(max_length=64, blank=True, default="")
    warnings = models.JSONField(default=list, blank=True)
    worker_last_error = models.CharField(max_length=255, blank=True, default="")
    worker_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Agent Git Connection"
        verbose_name_plural = "Agent Git Connections"
        db_table = "agent_git_connections"
        ordering = ("provider",)
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "provider"],
                condition=Q(deleted_at__isnull=True),
                name="agent_git_connection_unique_workspace_provider",
            )
        ]

    def __str__(self):
        return f"{self.provider} connection of {self.workspace_id}"


class AgentGithubDeviceAuthorizationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"
    DENIED = "denied", "Denied"


class AgentGithubDeviceAuthorizationKind(models.TextChoices):
    USER = "user", "User"
    ORGANIZATION = "organization", "Organization"


class AgentGithubDeviceAuthorization(BaseModel):
    """One GitHub device-flow attempt started by a workspace admin."""

    workspace = models.ForeignKey(
        "db.Workspace", on_delete=models.CASCADE, related_name="agent_github_device_authorizations"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_github_device_authorizations",
    )
    kind = models.CharField(
        max_length=16,
        choices=AgentGithubDeviceAuthorizationKind.choices,
        default=AgentGithubDeviceAuthorizationKind.USER,
    )
    device_code = models.TextField()
    user_code = models.CharField(max_length=32)
    verification_uri = models.CharField(max_length=2048)
    expires_at = models.DateTimeField()
    interval = models.PositiveIntegerField(default=5)
    last_polled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=AgentGithubDeviceAuthorizationStatus.choices,
        default=AgentGithubDeviceAuthorizationStatus.PENDING,
    )
    last_error = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        verbose_name = "Agent GitHub Device Authorization"
        verbose_name_plural = "Agent GitHub Device Authorizations"
        db_table = "agent_github_device_authorizations"
        ordering = ("-created_at",)

    def __str__(self):
        return f"device authorization {self.user_code} ({self.status})"


class AgentGitAccountState(models.TextChoices):
    CANDIDATE = "candidate", "Candidate"
    ATTACHED = "attached", "Attached"
    DETACHED = "detached", "Detached"


class AgentGitAccount(BaseModel):
    """A GitHub installation or a GitLab group seen through a connection.

    Only an admin attaches an account. Sync creates new GitHub installations
    as ``candidate`` and never changes ``state``; the repository catalog and
    project bindings read ``attached`` accounts only.
    """

    connection = models.ForeignKey(AgentGitConnection, on_delete=models.CASCADE, related_name="accounts")
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="agent_git_accounts")
    provider = models.CharField(max_length=16, choices=AgentGitProvider.choices)
    external_id = models.CharField(max_length=64)
    login = models.CharField(max_length=255)
    account_type = models.CharField(max_length=32, blank=True, default="")
    repository_selection = models.CharField(max_length=16, blank=True, default="")
    state = models.CharField(
        max_length=16,
        choices=AgentGitAccountState.choices,
        default=AgentGitAccountState.CANDIDATE,
    )
    attached_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_git_accounts_attached",
    )
    attached_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    catalog_refreshed_at = models.DateTimeField(null=True, blank=True)
    catalog_error = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        verbose_name = "Agent Git Account"
        verbose_name_plural = "Agent Git Accounts"
        db_table = "agent_git_accounts"
        ordering = ("login",)
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "external_id"],
                condition=Q(deleted_at__isnull=True),
                name="agent_git_account_unique_connection_external_id",
            )
        ]

    def __str__(self):
        return f"{self.provider} account {self.login} ({self.state})"


class AgentGitRepository(BaseModel):
    """One repository of an attached account: a snapshot row of the catalog."""

    account = models.ForeignKey(AgentGitAccount, on_delete=models.CASCADE, related_name="repositories")
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="agent_git_repositories")
    provider = models.CharField(max_length=16, choices=AgentGitProvider.choices)
    external_id = models.CharField(max_length=64)
    full_name = models.CharField(max_length=512)
    owner_login = models.CharField(max_length=255)
    private = models.BooleanField(default=True)
    default_branch = models.CharField(max_length=255, blank=True, default="")
    clone_url = models.CharField(max_length=2048)
    web_url = models.CharField(max_length=2048, blank=True, default="")

    class Meta:
        verbose_name = "Agent Git Repository"
        verbose_name_plural = "Agent Git Repositories"
        db_table = "agent_git_repositories"
        ordering = ("owner_login", "full_name")
        constraints = [
            models.UniqueConstraint(
                fields=["account", "external_id"],
                condition=Q(deleted_at__isnull=True),
                name="agent_git_repository_unique_account_external_id",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "owner_login", "full_name"], name="agent_git_repo_ws_owner_name"),
        ]

    def __str__(self):
        return self.full_name


class ProjectRepositoryBinding(BaseModel):
    """The one repository a project uses for agent work.

    Fields are copied from the catalog row at bind time, so the binding stays
    readable for audit after the catalog changes. Whether a new Run can use it
    is derived (see ``binding_availability``), never stored.
    """

    project = models.OneToOneField("db.Project", on_delete=models.CASCADE, related_name="repository_binding")
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="project_repository_bindings")
    account = models.ForeignKey(
        AgentGitAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_bindings",
    )
    provider = models.CharField(max_length=16, choices=AgentGitProvider.choices)
    host = models.CharField(max_length=255)
    external_repository_id = models.CharField(max_length=64)
    full_name = models.CharField(max_length=512)
    clone_url = models.CharField(max_length=2048)
    web_url = models.CharField(max_length=2048, blank=True, default="")
    default_branch = models.CharField(max_length=255, blank=True, default="")
    base_ref = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Project Repository Binding"
        verbose_name_plural = "Project Repository Bindings"
        db_table = "project_repository_bindings"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "provider", "host", "external_repository_id"],
                condition=Q(deleted_at__isnull=True),
                name="project_repository_binding_unique_repository",
            )
        ]

    def __str__(self):
        return f"{self.full_name} for project {self.project_id}"
