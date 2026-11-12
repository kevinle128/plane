# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""GitHub client for the provider-neutral interface."""

# Python imports
from urllib.parse import urlsplit

# Module imports
from plane.agent.git_providers import http
from plane.agent.git_providers.base import ProviderError, RepositoryInfo, RepositoryPage

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


def _on_github(url):
    parts = urlsplit(url or "")
    return parts.scheme == "https" and parts.hostname == GITHUB_HOST


class GithubClient:
    def __init__(self, connection, token):
        self.connection = connection
        self._token = token

    def list_repositories(self, account, cursor=None):
        page = int(cursor or 1)
        response = http.request(
            "GET",
            f"{GITHUB_API_URL}/user/installations/{account.external_id}/repositories",
            provider=PROVIDER,
            headers=api_headers(self._token),
            params={"per_page": PAGE_SIZE, "page": page},
        )
        raise_for_status(response)
        body = response.json() or {}
        repositories = []
        for item in body.get("repositories") or []:
            # Only GitHub-hosted clone URLs reach the catalog, so the Worker is
            # never pointed at another host through an API response.
            if not _on_github(item.get("clone_url")):
                continue
            repositories.append(
                RepositoryInfo(
                    external_id=str(item["id"]),
                    full_name=str(item["full_name"]),
                    owner_login=str((item.get("owner") or {}).get("login") or item["full_name"].split("/")[0]),
                    private=bool(item.get("private", True)),
                    default_branch=str(item.get("default_branch") or ""),
                    clone_url=str(item["clone_url"]),
                    web_url=str(item.get("html_url") or ""),
                )
            )
        return RepositoryPage(repositories=repositories, next_cursor=str(page + 1) if has_next_page(response) else None)
