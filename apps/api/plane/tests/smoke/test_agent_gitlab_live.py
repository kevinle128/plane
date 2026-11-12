# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Read-only live check against a real GitLab server.

Runs only when PLANE_TEST_GITLAB_TOKEN is set; it skips otherwise. With
PLANE_TEST_GITLAB_REQUIRED=1 a missing token fails the module instead,
because a skip exits 0 and must not count as evidence. The test only reads:
version, token self, user and one page of group projects.
"""

import os
from types import SimpleNamespace
from urllib.parse import quote, urlsplit

import pytest

from plane.agent.git_providers.gitlab import GitlabClient, parse_gitlab_version

TOKEN = os.environ.get("PLANE_TEST_GITLAB_TOKEN", "")
BASE_URL = os.environ.get("PLANE_TEST_GITLAB_URL", "https://git.oceanlabs.dev").rstrip("/")
GROUP = os.environ.get("PLANE_TEST_GITLAB_GROUP", "")

if os.environ.get("PLANE_TEST_GITLAB_REQUIRED") == "1" and not TOKEN:
    pytest.fail("PLANE_TEST_GITLAB_REQUIRED=1 but PLANE_TEST_GITLAB_TOKEN is not set", pytrace=False)

pytestmark = [pytest.mark.smoke, pytest.mark.skipif(not TOKEN, reason="PLANE_TEST_GITLAB_TOKEN is not set")]


@pytest.fixture
def client():
    host = BASE_URL.split("://", 1)[1].split("/", 1)[0]
    return GitlabClient(SimpleNamespace(base_url=BASE_URL, host=host, ca_bundle=None), TOKEN)


def test_version_is_supported(client):
    response = client.get("version")

    assert response.status_code == 200
    version = response.json()["version"]
    print(f"GitLab version: {version}")
    assert parse_gitlab_version(version) >= (15, 5)


def test_token_self_reports_scopes_and_state(client):
    response = client.get("personal_access_tokens/self")

    assert response.status_code == 200
    token = response.json()
    assert {"scopes", "active", "revoked", "expires_at", "user_id"} <= set(token)
    print(f"token scopes: {token['scopes']}, active: {token['active']}")


def test_user_has_a_bot_flag(client):
    response = client.get("user")

    assert response.status_code == 200
    print(f"token user is a bot: {response.json()['bot']}")


@pytest.mark.skipif(not GROUP, reason="PLANE_TEST_GITLAB_GROUP is not set")
def test_one_group_projects_page(client):
    group = client.get(f"groups/{quote(GROUP, safe='')}")
    assert group.status_code == 200

    page = client.list_repositories(SimpleNamespace(external_id=str(group.json()["id"])))

    print(f"projects on the first page: {len(page.repositories)}")
    host = urlsplit(BASE_URL).hostname
    assert all(urlsplit(info.clone_url).hostname == host for info in page.repositories)
