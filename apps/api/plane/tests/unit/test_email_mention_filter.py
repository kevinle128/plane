# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""``process_mention`` renders user mentions as ``@name`` and never looks up an agent ID as a user."""

from uuid import uuid4

import pytest

from plane.bgtasks.email_notification_task import process_mention
from plane.db.models import User


def mention(entity_name, identifier):
    return f'<mention-component entity_name="{entity_name}" entity_identifier="{identifier}"></mention-component>'


@pytest.mark.unit
class TestProcessMention:
    @pytest.mark.django_db
    def test_user_mention_is_rendered_as_display_name(self):
        user = User.objects.create(email="mention@plane.so", username="mention_user", display_name="Ada")

        html = process_mention(f"<p>Hi {mention('user_mention', user.id)}, please look</p>")

        assert html == "<p>Hi @Ada, please look</p>"

    @pytest.mark.django_db
    def test_agent_mention_is_left_in_place_and_not_looked_up(self):
        user = User.objects.create(email="mention2@plane.so", username="mention_user2", display_name="Bob")
        agent_id = uuid4()

        html = process_mention(f"<p>{mention('agent_mention', agent_id)} and {mention('user_mention', user.id)}</p>")

        assert "@Bob" in html
        assert f'entity_identifier="{agent_id}"' in html
        assert 'entity_name="agent_mention"' in html
