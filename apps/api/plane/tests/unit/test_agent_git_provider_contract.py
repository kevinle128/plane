# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""One contract suite for every Git provider client.

GitHub and GitLab must return the same neutral shapes, so later code never
branches on the provider. A further provider would have to pass this suite.
"""

from dataclasses import fields
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from plane.agent.git_providers.base import ProviderError, RepositoryInfo, RepositoryPage
from plane.agent.git_providers.github import GithubClient
from plane.agent.git_providers.gitlab import GitlabClient, parse_gitlab_version
from plane.tests.agent_git_fakes import FakeProviderHttp, json_response, load_fixture
from plane.tests.agent_git_fixtures import github_repositories_page, github_repository


def github_case(fake):
    fake.add(
        "GET",
        "api.github.com/user/installations/111/repositories",
        github_repositories_page(
            github_repository(501, "plane-mini/api"), github_repository(502, "plane-mini/web", private=False)
        ),
    )
    connection = SimpleNamespace(provider="github", host="github.com", base_url="https://github.com", ca_bundle=None)
    account = SimpleNamespace(provider="github", external_id="111", login="plane-mini")
    return GithubClient(connection, "ghu_contract"), account, {"plane-mini/api": True, "plane-mini/web": False}


def gitlab_case(fake):
    fake.add(
        "GET",
        "git.example.com/api/v4/groups/19/projects",
        json_response(200, load_fixture("gitlab", "group_projects_page1.json")),
    )
    connection = SimpleNamespace(
        provider="gitlab", host="git.example.com", base_url="https://git.example.com", ca_bundle=None
    )
    account = SimpleNamespace(provider="gitlab", external_id="19", login="platform")
    return GitlabClient(connection, "glpat-contract"), account, {"platform/api": True, "platform/tools/cli": True}


CASES = {"github": github_case, "gitlab": gitlab_case}


@pytest.fixture(params=sorted(CASES))
def provider_case(request, mocker):
    fake = FakeProviderHttp()
    mocker.patch("plane.agent.git_providers.http.request", side_effect=fake)
    client, account, expected_private = CASES[request.param](fake)
    return SimpleNamespace(provider=request.param, fake=fake, client=client, account=account, private=expected_private)


@pytest.mark.unit
class TestProviderContract:
    def test_list_repositories_returns_neutral_repository_info(self, provider_case):
        page = provider_case.client.list_repositories(provider_case.account)

        assert isinstance(page, RepositoryPage)
        assert page.repositories, "the scripted page has repositories"
        for info in page.repositories:
            assert isinstance(info, RepositoryInfo)
            for field in fields(RepositoryInfo):
                value = getattr(info, field.name)
                assert isinstance(value, bool if field.name == "private" else str), field.name
            assert info.external_id
            assert info.full_name.startswith(f"{info.owner_login}/")
            assert urlsplit(info.clone_url).scheme == "https"
            assert urlsplit(info.clone_url).hostname == provider_case.client.connection.host
            assert info.default_branch

    def test_private_flag_is_neutral(self, provider_case):
        page = provider_case.client.list_repositories(provider_case.account)

        assert {info.full_name: info.private for info in page.repositories} == provider_case.private

    def test_rejected_token_maps_to_a_token_invalid_code(self, provider_case):
        provider_case.fake.routes.clear()
        for path in ("api.github.com/user/installations/111/repositories", "git.example.com/api/v4/groups/19/projects"):
            provider_case.fake.add("GET", path, json_response(401, {"message": "401 Unauthorized"}))

        with pytest.raises(ProviderError) as raised:
            provider_case.client.list_repositories(provider_case.account)

        assert raised.value.code == f"{provider_case.provider}_token_invalid"
        assert raised.value.provider == provider_case.provider

    def test_token_is_sent_only_in_headers(self, provider_case):
        provider_case.client.list_repositories(provider_case.account)

        for call in provider_case.fake.calls:
            assert "contract" not in call["url"]
            assert any("contract" in value for value in (call.get("headers") or {}).values())


@pytest.mark.unit
class TestGitlabVersionParse:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("18.10.3-ee", (18, 10)),
            ("15.5.0", (15, 5)),
            ("15.4.9-ee", (15, 4)),
            ("garbage", None),
            ("", None),
            (None, None),
        ],
    )
    def test_parse(self, raw, expected):
        assert parse_gitlab_version(raw) == expected
