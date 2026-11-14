# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The context envelope (version 1) that a Run starts from.

It holds the work item, its repository, the requester, the Agent and the
earlier comments of the same issue. It never holds other issues or Run
events. The comments have a byte budget: the oldest comments are dropped
first and counted exactly in ``omitted_comment_count``.
"""

# Python imports
import re

# Third party imports
from bs4 import BeautifulSoup

# Django imports
from django.conf import settings

# Module imports
from plane.db.models import AgentRunContextSnapshot, IssueComment

CONTEXT_VERSION = 1
COMMENT_TEXT_BUDGET_BYTES = 60_000
BLOCK_TAGS = ("p", "li", "pre", "blockquote", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr")


def plain_text(html):
    """Readable text of editor HTML: one line per block, no tags."""
    soup = BeautifulSoup(html or "", "html.parser")
    for node in soup.find_all("br"):
        node.replace_with("\n")
    for node in soup.find_all(BLOCK_TAGS):
        node.append("\n")
    text = re.sub(r"[ \t]+\n", "\n", soup.get_text())
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _person(user):
    return {"id": str(user.id), "display_name": user.display_name}


def _comment(comment):
    return {
        "id": str(comment.id),
        "author": _person(comment.actor) if comment.actor else None,
        "created_at": comment.created_at.isoformat(),
        "text": plain_text(comment.comment_html),
    }


def _within_budget(comments):
    """Drop the oldest comments until the text of the rest fits the budget."""
    sizes = [len(comment["text"].encode()) for comment in comments]
    total = sum(sizes)
    dropped = 0
    while total > COMMENT_TEXT_BUDGET_BYTES:
        total -= sizes[dropped]
        dropped += 1
    return comments[dropped:], dropped


def build_payload(run, trigger_comment):
    issue = run.issue
    project = run.project
    workspace = run.workspace
    earlier = (
        IssueComment.objects.filter(issue_id=issue.id, created_at__lt=trigger_comment.created_at)
        .exclude(pk=trigger_comment.pk)
        .select_related("actor")
        .order_by("created_at")
    )
    comments, omitted = _within_budget([_comment(comment) for comment in earlier])
    return {
        "workspace": {"id": str(workspace.id), "slug": workspace.slug, "name": workspace.name},
        "project": {"id": str(project.id), "identifier": project.identifier, "name": project.name},
        "issue": {
            "id": str(issue.id),
            "identifier": f"{project.identifier}-{issue.sequence_id}",
            "sequence_id": issue.sequence_id,
            "url": f"{settings.WEB_URL or ''}/{workspace.slug}/projects/{project.id}/issues/{issue.id}",
            "title": issue.name,
            "description": plain_text(issue.description_html),
            "state": {"name": issue.state.name, "group": issue.state.group} if issue.state else None,
        },
        "repository": {
            "provider": run.provider,
            "host": run.host,
            "full_name": run.full_name,
            "default_branch": run.default_branch,
            "base_ref": run.base_ref,
        },
        "requester": _person(run.requester),
        "agent": {
            "id": str(run.agent_id),
            "name": run.agent_name,
            "handle": run.agent_handle,
            "instructions": run.instructions,
        },
        "trigger_comment": _comment(trigger_comment),
        "comments": comments,
        "omitted_comment_count": omitted,
    }


def create_snapshot(run, trigger_comment):
    payload = build_payload(run, trigger_comment)
    return AgentRunContextSnapshot.objects.create(
        run=run,
        version=CONTEXT_VERSION,
        payload=payload,
        omitted_comment_count=payload["omitted_comment_count"],
    )
