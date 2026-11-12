# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Refresh the repository catalog of a Git provider connection.

The task takes a connection ID only, never a token, so no token reaches the
broker or task logs. Each attached account is read page by page, and its
snapshot is replaced only after the last page succeeded; a failure keeps
the previous snapshot unchanged.
"""

# Python imports
import logging

# Third party imports
from celery import shared_task

# Django imports
from django.db import transaction
from django.utils import timezone

# Module imports
from plane.agent.git_providers import client_for
from plane.agent.git_providers.base import ProviderError
from plane.agent.services import git_connection
from plane.db.models import AgentGitAccount, AgentGitAccountState, AgentGitConnection, AgentGitRepository

logger = logging.getLogger("plane.bgtasks.agent_git_catalog_task")

MAX_PAGES = 200
TOKEN_INVALID_CODES = {"github_token_invalid", "gitlab_token_invalid"}


def _unexpected(account, detail=""):
    return ProviderError(f"{account.provider}_unexpected_response", account.provider, detail, http_status=502)


def _fetch_all(client, account):
    repositories = []
    cursor = None
    for _ in range(MAX_PAGES):
        page = client.list_repositories(account, cursor)
        repositories.extend(page.repositories)
        if not page.next_cursor:
            return repositories
        cursor = page.next_cursor
    raise _unexpected(account, "too_many_pages")


@transaction.atomic
def _swap_snapshot(account_id, repositories):
    account = AgentGitAccount.objects.select_for_update().filter(pk=account_id).first()
    if account is None or account.state != AgentGitAccountState.ATTACHED:
        return
    seen = set()
    for info in repositories:
        if info.external_id in seen:
            continue
        seen.add(info.external_id)
        AgentGitRepository.objects.update_or_create(
            account=account,
            external_id=info.external_id,
            defaults={
                "workspace_id": account.workspace_id,
                "provider": account.provider,
                "full_name": info.full_name,
                "owner_login": info.owner_login,
                "private": info.private,
                "default_branch": info.default_branch,
                "clone_url": info.clone_url,
                "web_url": info.web_url,
            },
        )
    # Catalog rows are a snapshot, so rows that are no longer granted are removed for good.
    AgentGitRepository.all_objects.filter(account=account).exclude(external_id__in=seen).delete()
    account.catalog_error = ""
    account.catalog_refreshed_at = timezone.now()
    account.save(update_fields=["catalog_error", "catalog_refreshed_at", "updated_at"])


def _record_failure(connection, account, error):
    if error.code in TOKEN_INVALID_CODES:
        with transaction.atomic():
            locked = AgentGitConnection.objects.select_for_update().get(pk=connection.pk)
            git_connection.mark_reconnect_required(locked, error.code)
        return False
    AgentGitAccount.objects.filter(pk=account.pk).update(catalog_error=error.code[:64])
    return True


def refresh_catalog(connection_id):
    connection = AgentGitConnection.objects.filter(pk=connection_id).first()
    if connection is None or git_connection.status_error(connection) is not None:
        logger.info("catalog refresh skipped for connection %s: not connected", connection_id)
        return
    accounts = list(AgentGitAccount.objects.filter(connection=connection, state=AgentGitAccountState.ATTACHED))
    if not accounts:
        return
    try:
        client = client_for(connection)
    except ProviderError as error:
        logger.warning("catalog refresh for connection %s stopped: %s", connection_id, error.code)
        return
    for account in accounts:
        try:
            repositories = _fetch_all(client, account)
            _swap_snapshot(account.id, repositories)
        except ProviderError as error:
            logger.warning("catalog refresh for account %s failed: %s", account.id, error.code)
            if not _record_failure(connection, account, error):
                return
            continue
        except Exception:
            # Provider answers are untrusted: any other failure is recorded on the
            # account, so the admin sees a reason, and the next account is read.
            logger.exception("catalog refresh for account %s failed unexpectedly", account.id)
            _record_failure(connection, account, _unexpected(account))
            continue
        logger.info("catalog of account %s refreshed with %s repositories", account.id, len(repositories))


@shared_task
def refresh_agent_git_catalog(connection_id):
    refresh_catalog(connection_id)
