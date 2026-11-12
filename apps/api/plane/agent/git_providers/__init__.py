# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Provider clients. ``client_for`` is the only place that branches on the provider."""


def client_for(connection):
    """Return the provider client for a usable connection.

    Raises ``ProviderError`` when the connection has no usable token
    (disconnected, reconnect required, or the token cannot be decrypted).
    """
    if connection.provider == "github":
        from plane.agent.git_providers.github import GithubClient
        from plane.agent.services import github_connection

        return GithubClient(connection, github_connection.usable_token(connection.id))
    raise ValueError(f"Unsupported Git provider: {connection.provider}")
