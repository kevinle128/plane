# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Self-hosted GitLab client for the provider-neutral interface."""

# Python imports
import logging
import re
from urllib.parse import urlsplit

# Module imports
from plane.agent.git_providers import http
from plane.agent.git_providers.base import ProviderError, RepositoryInfo, RepositoryPage

logger = logging.getLogger("plane.agent.git_providers.gitlab")

PROVIDER = "gitlab"
PAGE_SIZE = 100
_VERSION = re.compile(r"^(\d+)\.(\d+)")


def parse_gitlab_version(raw):
    """Return ``(major, minor)`` of a GitLab version such as ``18.10.3-ee``, or ``None``."""
    match = _VERSION.match(str(raw or ""))
    return (int(match.group(1)), int(match.group(2))) if match else None


def token_headers(token):
    return {"PRIVATE-TOKEN": token, "Accept": "application/json"}


def raise_for_status(response):
    """A 401 means the token is no longer valid; a 403 refuses one resource only."""
    if response.status_code == 401:
        raise ProviderError("gitlab_token_invalid", PROVIDER, http_status=409)
    if response.status_code != 200:
        raise ProviderError("gitlab_unexpected_response", PROVIDER, f"HTTP {response.status_code}", http_status=502)


class GitlabClient:
    def __init__(self, connection, token):
        self.connection = connection
        self._token = token

    def get(self, path, params=None, deadline=None):
        return http.request(
            "GET",
            f"{self.connection.base_url}/api/v4/{path}",
            provider=PROVIDER,
            headers=token_headers(self._token),
            params=params,
            ca_bundle=self.connection.ca_bundle,
            deadline=deadline,
        )

    def list_repositories(self, account, cursor=None):
        response = self.get(
            f"groups/{account.external_id}/projects",
            params={
                "include_subgroups": "true",
                "with_shared": "false",
                "archived": "false",
                "per_page": PAGE_SIZE,
                "page": int(cursor or 1),
            },
        )
        raise_for_status(response)
        expected = urlsplit(self.connection.base_url)
        repositories = []
        for item in response.json() or []:
            clone = urlsplit(str(item.get("http_url_to_repo") or ""))
            # A project whose clone URL points at another host or scheme is skipped,
            # so the Worker is never sent to a third host through an API response.
            if clone.scheme != expected.scheme or clone.hostname != expected.hostname or clone.port != expected.port:
                logger.warning("gitlab project %s skipped: clone URL is not on the connection host", item.get("id"))
                continue
            path = str(item["path_with_namespace"])
            repositories.append(
                RepositoryInfo(
                    external_id=str(item["id"]),
                    full_name=path,
                    owner_login=str((item.get("namespace") or {}).get("full_path") or path.rsplit("/", 1)[0]),
                    private=item.get("visibility") != "public",
                    default_branch=str(item.get("default_branch") or ""),
                    clone_url=str(item["http_url_to_repo"]),
                    web_url=str(item.get("web_url") or ""),
                )
            )
        # GitLab sends an empty X-Next-Page on the last page.
        next_page = (response.header("X-Next-Page") or "").strip()
        return RepositoryPage(repositories=repositories, next_cursor=next_page or None)
