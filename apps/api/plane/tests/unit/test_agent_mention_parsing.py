# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.agent.services.context_snapshot import plain_text
from plane.agent.services.run_creation import parse_agent_mentions

FIRST = "6f1c1d5e-0c43-4a43-9a51-0a1f6a4f0001"
SECOND = "6f1c1d5e-0c43-4a43-9a51-0a1f6a4f0002"


def mention(entity_name, identifier):
    return f'<mention-component entity_name="{entity_name}" entity_identifier="{identifier}"></mention-component>'


@pytest.mark.unit
class TestParseAgentMentions:
    def test_distinct_agents_in_order_of_first_mention(self):
        html = (
            f"<p>{mention('agent_mention', SECOND)} and {mention('agent_mention', FIRST)}</p>"
            f"<p>{mention('agent_mention', SECOND)} again</p>"
        )

        assert parse_agent_mentions(html) == [SECOND, FIRST]

    def test_user_mentions_and_other_tags_are_ignored(self):
        html = f"<p>{mention('user_mention', FIRST)} <span entity_identifier='{SECOND}'>x</span></p>"

        assert parse_agent_mentions(html) == []

    def test_mention_without_identifier_is_ignored(self):
        html = '<p><mention-component entity_name="agent_mention"></mention-component></p>'

        assert parse_agent_mentions(html) == []

    @pytest.mark.parametrize("html", ["", None, "<p></p>", "plain text"])
    def test_empty_or_plain_content_has_no_mentions(self, html):
        assert parse_agent_mentions(html) == []


@pytest.mark.unit
class TestPlainText:
    def test_blocks_become_lines_and_tags_are_removed(self):
        html = f"<p>{mention('agent_mention', FIRST)} Why <strong>fails</strong>?</p><ul><li>one</li><li>two</li></ul>"

        assert plain_text(html) == "Why fails?\none\ntwo"

    def test_line_breaks_are_kept(self):
        assert plain_text("<p>a<br>b</p>") == "a\nb"
