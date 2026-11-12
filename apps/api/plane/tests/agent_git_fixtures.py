# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Shared fixtures for the Git provider tests.

Import the fixtures you need into a test module, for example
``from plane.tests.agent_git_fixtures import fake_http, github_app_env``.
"""

import logging
from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from plane.db.models import User, WorkspaceMember
from plane.tests.agent_git_fakes import install_fake_http, json_response

GITHUB_ACCESS_TOKEN = "ghu_ACCESS_TOKEN_VALUE_0001"
GITHUB_REFRESH_TOKEN = "ghr_REFRESH_TOKEN_VALUE_0001"
GITHUB_DEVICE_CODE = "device-code-secret-0001"
GITHUB_CLIENT_SECRET = "github-app-client-secret-0001"

AGENT_LOGGERS = ("plane.agent", "plane.app.views.agent", "plane.bgtasks.agent_git_catalog_task")


@pytest.fixture
def fake_http(mocker):
    return install_fake_http(mocker)


@pytest.fixture
def github_app_env(monkeypatch):
    monkeypatch.setenv("GITHUB_APP_CLIENT_ID", "Iv1.testclientid")
    monkeypatch.setenv("GITHUB_APP_CLIENT_SECRET", GITHUB_CLIENT_SECRET)
    monkeypatch.setenv("GITHUB_APP_SLUG", "plane-agents-test")


@pytest.fixture
def agent_caplog(caplog):
    """Capture every record of the agent loggers, whatever their propagation."""
    caplog.set_level(logging.DEBUG)
    loggers = [logging.getLogger(name) for name in AGENT_LOGGERS]
    for logger in loggers:
        logger.addHandler(caplog.handler)
        logger.setLevel(logging.DEBUG)
    yield caplog
    for logger in loggers:
        logger.removeHandler(caplog.handler)


def make_workspace_user(workspace, role, is_active=True):
    user = User.objects.create(
        email=f"user-{uuid4().hex[:8]}@plane.so",
        username=uuid4().hex,
        first_name="Role",
        last_name=str(role),
    )
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role, is_active=is_active)
    return user


def client_for_user(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def member_client(db, workspace):
    return client_for_user(make_workspace_user(workspace, 15))


@pytest.fixture
def guest_client(db, workspace):
    return client_for_user(make_workspace_user(workspace, 5))


def github_device_code_response(expires_in=900, interval=5):
    return json_response(
        200,
        {
            "device_code": GITHUB_DEVICE_CODE,
            "user_code": "WDJB-MJHT",
            "verification_uri": "https://github.com/login/device",
            "expires_in": expires_in,
            "interval": interval,
        },
    )


def github_token_response(access_token=GITHUB_ACCESS_TOKEN, refresh_token=GITHUB_REFRESH_TOKEN):
    return json_response(
        200,
        {
            "access_token": access_token,
            "expires_in": 28800,
            "refresh_token": refresh_token,
            "refresh_token_expires_in": 15897600,
            "scope": "",
            "token_type": "bearer",
        },
    )


def github_error_response(error):
    # GitHub answers device-flow polling errors with HTTP 200 and an error body.
    return json_response(200, {"error": error, "error_description": error})


def github_user_response(login="octo-admin", user_id=101):
    return json_response(200, {"login": login, "id": user_id, "type": "User"})


def add_github_connect_routes(fake, token_response=None, installations=None):
    """Script a full successful device flow (start, token, user, installations)."""
    fake.add("POST", "github.com/login/device/code", github_device_code_response())
    fake.add("POST", "github.com/login/oauth/access_token", token_response or github_token_response())
    fake.add("GET", "api.github.com/user", github_user_response())
    fake.add(
        "GET",
        "api.github.com/user/installations",
        json_response(200, {"total_count": len(installations or []), "installations": installations or []}),
    )
    return fake


def device_authorization_url(slug, auth_id=None, action=None):
    base = f"/api/workspaces/{slug}/agent-git/github/device-authorizations/"
    if auth_id is None:
        return base
    return f"{base}{auth_id}/{action}/"


def connect_github(client, slug, fake, **routes):
    """Run start + poll through the API and return the poll response."""
    add_github_connect_routes(fake, **routes)
    start = client.post(device_authorization_url(slug), {"kind": "user"}, format="json")
    assert start.status_code == 201, start.data
    return client.post(device_authorization_url(slug, start.data["id"], "poll"), {}, format="json")


def expire_connection_token(connection):
    connection.token_expires_at = timezone.now() - timedelta(minutes=1)
    connection.save(update_fields=["token_expires_at"])
