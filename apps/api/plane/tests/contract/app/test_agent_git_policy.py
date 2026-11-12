# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.agent.services.git_connection import change_request_policy
from plane.db.models import AgentGitPolicy


def policy_url(slug, provider="github"):
    return f"/api/workspaces/{slug}/agent-git/{provider}/policy/"


@pytest.mark.contract
class TestDraftPullRequestDefault:
    @pytest.mark.django_db
    def test_open_as_draft_is_on_by_default(self, session_client, workspace):
        response = session_client.get(policy_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["provider"] == "github"
        assert response.data["open_as_draft"] is True
        assert not AgentGitPolicy.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    def test_admin_change_persists_and_the_delivery_policy_reads_it(self, session_client, workspace):
        patched = session_client.patch(policy_url(workspace.slug), {"open_as_draft": False}, format="json")
        reloaded = session_client.get(policy_url(workspace.slug))

        assert patched.status_code == status.HTTP_200_OK
        assert patched.data["open_as_draft"] is False
        assert reloaded.data["open_as_draft"] is False
        assert change_request_policy(workspace.id, "github")["open_as_draft"] is False
        assert AgentGitPolicy.objects.filter(workspace=workspace, provider="github").count() == 1

    @pytest.mark.django_db
    def test_member_reads_but_cannot_change(self, session_client, member_client, workspace):
        assert member_client.get(policy_url(workspace.slug)).data["open_as_draft"] is True

        response = member_client.patch(policy_url(workspace.slug), {"open_as_draft": False}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert session_client.get(policy_url(workspace.slug)).data["open_as_draft"] is True

    @pytest.mark.django_db
    def test_guest_cannot_read(self, guest_client, workspace):
        assert guest_client.get(policy_url(workspace.slug)).status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_invalid_value_returns_400(self, session_client, workspace):
        response = session_client.patch(policy_url(workspace.slug), {"open_as_draft": "sometimes"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not AgentGitPolicy.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    def test_unknown_provider_returns_404(self, session_client, workspace):
        assert session_client.get(policy_url(workspace.slug, provider="gitea")).status_code == 404
