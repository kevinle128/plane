# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.agent.services.branch_name import agent_branch_name, is_valid_ref_name


@pytest.mark.unit
class TestAgentBranchName:
    def test_issue_format(self):
        name = agent_branch_name("issue", project_identifier="PLAN", issue_identifier="PLAN-214", run_short_id="a1b2c3")

        assert name == "agent/PLAN-214-a1b2c3"

    def test_project_issue_format(self):
        name = agent_branch_name(
            "project_issue", project_identifier="PLAN", issue_identifier="PLAN-214", run_short_id="a1b2c3"
        )

        assert name == "agent/PLAN/PLAN-214-a1b2c3"

    @pytest.mark.parametrize("branch_format", ["issue", "project_issue"])
    def test_two_runs_on_one_issue_get_distinct_names(self, branch_format):
        first = agent_branch_name(
            branch_format, project_identifier="PLAN", issue_identifier="PLAN-7", run_short_id="r1"
        )
        second = agent_branch_name(
            branch_format, project_identifier="PLAN", issue_identifier="PLAN-7", run_short_id="r2"
        )

        assert first != second

    @pytest.mark.parametrize(
        "project_identifier, issue_identifier, expected",
        [
            ("PL AN", "PL AN-1", "agent/PL-AN/PL-AN-1-abc"),
            ("..", "../../etc", "agent/project/etc-abc"),
            ("-rm", "-rm-1", "agent/rm/rm-1-abc"),
            ("X.lock", "X.lock", "agent/X-lock/X-lock-abc"),
            ("ÜBER", "ÜBER~1^2:3", "agent/BER/BER-1-2-3-abc"),
            ("@{", "@{-1}", "agent/project/1-abc"),
        ],
    )
    def test_unsafe_identifiers_are_sanitized_into_a_valid_ref(self, project_identifier, issue_identifier, expected):
        name = agent_branch_name(
            "project_issue",
            project_identifier=project_identifier,
            issue_identifier=issue_identifier,
            run_short_id="ABC",
        )

        assert name == expected
        assert is_valid_ref_name(name)

    def test_unknown_format_is_rejected(self):
        with pytest.raises(ValueError):
            agent_branch_name("random", project_identifier="P", issue_identifier="P-1", run_short_id="r1")

    @pytest.mark.parametrize("run_short_id", ["", "  ", "///"])
    def test_a_run_suffix_is_required(self, run_short_id):
        with pytest.raises(ValueError):
            agent_branch_name("issue", project_identifier="P", issue_identifier="P-1", run_short_id=run_short_id)


@pytest.mark.unit
class TestRefNameValidation:
    @pytest.mark.parametrize("ref", ["main", "release/2.0", "feature/PLAN-1_fix", "v1.2.3"])
    def test_valid_refs(self, ref):
        assert is_valid_ref_name(ref)

    @pytest.mark.parametrize(
        "ref",
        [
            "",
            "-x",
            "/x",
            "x/",
            "x.",
            "a..b",
            "a@{1}",
            "@",
            "a b",
            "a\tb",
            "a~1",
            "a^",
            "a:b",
            "a?",
            "a*",
            "a[",
            "a\\b",
            "a//b",
            ".hidden",
            "a/.b",
            "x.lock",
            "a/b.lock/c",
            "x" * 256,
            None,
            12,
        ],
    )
    def test_invalid_refs(self, ref):
        assert not is_valid_ref_name(ref)
