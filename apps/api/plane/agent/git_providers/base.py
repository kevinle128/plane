# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Provider-neutral shapes shared by the GitHub and GitLab clients."""

from dataclasses import dataclass, field
from typing import Optional, Protocol


class ProviderError(Exception):
    """A Git provider failure with a stable, user-facing reason code.

    ``code`` is fixed (for example ``gitlab_tls_failed`` or
    ``provider_disconnected``). ``detail`` is safe to show to an admin and
    never contains a token.
    """

    def __init__(self, code, provider, detail="", http_status=400):
        super().__init__(code)
        self.code = code
        self.provider = provider
        self.detail = detail
        self.http_status = http_status

    def as_response_body(self):
        body = {"error": self.code, "provider": self.provider}
        if self.detail:
            body["detail"] = self.detail
        return body


@dataclass(frozen=True)
class RepositoryInfo:
    external_id: str
    full_name: str
    owner_login: str
    private: bool
    default_branch: str
    clone_url: str
    web_url: str


@dataclass(frozen=True)
class RepositoryPage:
    repositories: list = field(default_factory=list)
    next_cursor: Optional[str] = None


class GitProviderClient(Protocol):
    """The operations later code may call on any provider."""

    def list_repositories(self, account, cursor: Optional[str] = None) -> RepositoryPage: ...
