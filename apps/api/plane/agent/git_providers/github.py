# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""GitHub client for the provider-neutral interface."""

# Python imports
import logging
from urllib.parse import urlsplit

# Module imports
from plane.agent.git_providers import http
from plane.agent.git_providers.base import ProviderError, RepositoryInfo, RepositoryPage, fits_catalog

logger = logging.getLogger("plane.agent.git_providers.github")

PROVIDER = "github"
GITHUB_HOST = "github.com"
GITHUB_API_URL = "https://api.github.com"
PAGE_SIZE = 100


def api_headers(token):
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def has_next_page(response):
    return 'rel="next"' in (response.header("Link") or "")


def raise_for_status(response):
    """Map a GitHub error status to a reason code. A 401 means the token is no longer valid."""
    if response.status_code == 401:
        raise ProviderError("github_token_invalid", PROVIDER, http_status=409)
    if response.status_code != 200:
        raise ProviderError("github_unexpected_response", PROVIDER, f"HTTP {response.status_code}", http_status=502)


def unexpected_body(detail):
    """A GitHub answer whose JSON does not have the documented shape."""
    return ProviderError("github_unexpected_response", PROVIDER, detail, http_status=502)


def _on_github(url):
    parts = urlsplit(url or "")
    return parts.scheme == "https" and parts.hostname == GITHUB_HOST


class GithubClient:
    def __init__(self, connection, token):
        self.connection = connection
        self._token = token

    def list_repositories(self, account, cursor=None, deadline=None):
        page = int(cursor or 1)
        response = http.request(
            "GET",
            f"{GITHUB_API_URL}/user/installations/{account.external_id}/repositories",
            provider=PROVIDER,
            headers=api_headers(self._token),
            params={"per_page": PAGE_SIZE, "page": page},
            deadline=deadline,
        )
        raise_for_status(response)
        items = response.json_object().get("repositories")
        if not isinstance(items, list):
            raise unexpected_body("repositories")
        repositories = []
        for item in items:
            if not isinstance(item, dict) or item.get("id") is None or not item.get("full_name"):
                raise unexpected_body("repository")
            # Only GitHub-hosted clone URLs reach the catalog, so the Worker is
            # never pointed at another host through an API response.
            if not _on_github(item.get("clone_url")):
                continue
            full_name = str(item["full_name"])
            owner = item.get("owner")
            info = RepositoryInfo(
                external_id=str(item["id"]),
                full_name=full_name,
                owner_login=str((owner.get("login") if isinstance(owner, dict) else None) or full_name.split("/")[0]),
                private=bool(item.get("private", True)),
                default_branch=str(item.get("default_branch") or ""),
                clone_url=str(item["clone_url"]),
                web_url=str(item.get("html_url") or ""),
            )
            if fits_catalog(info):
                repositories.append(info)
            else:
                logger.warning(
                    "github repository %s skipped: a value is too long for the catalog", info.external_id[:64]
                )
        return RepositoryPage(repositories=repositories, next_cursor=str(page + 1) if has_next_page(response) else None)
