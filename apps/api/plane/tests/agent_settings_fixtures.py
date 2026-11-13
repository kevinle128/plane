# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Shared fixtures and helpers for the workspace Agent and Worker tests."""

import hashlib
import secrets

import pytest
from rest_framework.test import APIClient

from plane.db.models import AgentWorker

REQUIRED_CHECK_NAMES = (
    "authentication",
    "model_report",
    "follow_up",
    "progress",
    "interruption",
    "permission",
    "recovery",
)

REPORTED_MODELS = [
    {"id": "default", "label": "Default (recommended)", "description": "Use the default model"},
    {"id": "sonnet", "label": "Sonnet", "description": "Efficient for routine tasks"},
    {"id": "haiku", "label": "Haiku", "description": "Fastest model"},
]


def agents_url(slug, harness=None, action=None):
    url = f"/api/workspaces/{slug}/agents/"
    if harness:
        url += f"{harness}/"
    if action:
        url += f"{action}/"
    return url


def make_worker(name="mini", revoked_at=None):
    """Create an Agent Worker and return it with its raw token."""
    token = "plane_aw_" + secrets.token_urlsafe(32)
    worker = AgentWorker.objects.create(
        name=name,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        revoked_at=revoked_at,
    )
    return worker, token


def worker_client_for(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def agent_worker(db):
    return make_worker()


@pytest.fixture
def worker_client(agent_worker):
    _, token = agent_worker
    return worker_client_for(token)


def probe_report(generation, **overrides):
    """A complete, passing version 1 probe report."""
    report = {
        "version": 1,
        "generation": generation,
        "harness_version": "2.1.289",
        "location": "/opt/homebrew/bin/claude",
        "checks": [{"name": name, "passed": True, "detail": ""} for name in REQUIRED_CHECK_NAMES],
        "models": REPORTED_MODELS,
        "capabilities": {"midturn_input": False, "native_resume": True, "permission_prompt": True},
        "failure_hint": "",
    }
    report.update(overrides)
    return report


def failing_checks(failed_name, detail="claude exited 1 · not logged in"):
    return [
        {"name": name, "passed": name != failed_name, "detail": detail if name == failed_name else ""}
        for name in REQUIRED_CHECK_NAMES
    ]
