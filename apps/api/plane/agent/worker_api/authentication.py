# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Worker token authentication.

The token travels in ``Authorization: Bearer <token>``. It must never use
``X-Api-Key``: ``APITokenLogMiddleware`` stores the request and response bodies
of every ``X-Api-Key`` request, and some Worker responses carry provider tokens.
Only the SHA-256 hash of the token is stored.
"""

# Python imports
import hashlib

# Third party imports
from rest_framework import authentication, permissions
from rest_framework.exceptions import AuthenticationFailed

# Module imports
from plane.db.models import AgentWorker

AUTH_SCHEME = "Bearer"
MAX_TOKEN_LENGTH = 256


def hash_worker_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


class WorkerPrincipal:
    """The authenticated Worker. It is not a ``User`` and has no workspace role."""

    is_authenticated = True
    is_anonymous = False
    # The request logger reads ``request.user.id``; a Worker has no user ID.
    id = None
    pk = None

    def __init__(self, worker):
        self.worker = worker

    def __str__(self):
        return f"agent worker {self.worker.name}"


class WorkerTokenAuthentication(authentication.BaseAuthentication):
    def authenticate_header(self, request):
        # Makes DRF answer 401 (not 403) for a missing or invalid token.
        return f'{AUTH_SCHEME} realm="agent-worker"'

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme != AUTH_SCHEME or not token:
            return None
        token = token.strip()
        if not token or len(token) > MAX_TOKEN_LENGTH:
            raise AuthenticationFailed("Invalid worker token.")
        worker = AgentWorker.objects.filter(token_hash=hash_worker_token(token), revoked_at__isnull=True).first()
        if worker is None:
            raise AuthenticationFailed("Invalid worker token.")
        return WorkerPrincipal(worker), None


class IsAgentWorker(permissions.BasePermission):
    """Only a Worker principal passes, even if another mechanism authenticated a user."""

    def has_permission(self, request, view):
        return isinstance(request.user, WorkerPrincipal)
