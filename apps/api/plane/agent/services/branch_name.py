# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Git ref names: validation of user-supplied refs and Agent branch names."""

# Python imports
import re

MAX_REF_BYTES = 255
MAX_COMPONENT_LENGTH = 100
BRANCH_FORMATS = {
    "issue": "agent/{issue}-{run}",
    "project_issue": "agent/{project}/{issue}-{run}",
}
_UNSAFE_CHARACTERS = re.compile(r"[^A-Za-z0-9._-]")
_DOT_RUNS = re.compile(r"\.{2,}")
_DASH_RUNS = re.compile(r"-{2,}")
_FORBIDDEN_CHARACTERS = set(" ~^:?*[\\")


def is_valid_ref_name(ref):
    """Return True when ``ref`` is a safe Git branch or tag name.

    Follows ``git check-ref-format`` and also refuses a leading ``-``,
    because the value is later passed to git commands as an argument.
    """
    if not isinstance(ref, str) or not ref:
        return False
    if len(ref.encode("utf-8")) > MAX_REF_BYTES:
        return False
    if ref == "@" or ref.startswith(("-", "/")) or ref.endswith(("/", ".")):
        return False
    if ".." in ref or "@{" in ref or "//" in ref:
        return False
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in ref):
        return False
    if any(character in _FORBIDDEN_CHARACTERS for character in ref):
        return False
    return all(not part.startswith(".") and not part.endswith(".lock") for part in ref.split("/"))


def _sanitize_component(value):
    """Reduce an identifier to one safe ref component (letters, digits, ``.``, ``_``, ``-``)."""
    text = _UNSAFE_CHARACTERS.sub("-", str(value or ""))
    text = _DOT_RUNS.sub("-", text)
    text = _DASH_RUNS.sub("-", text).strip("-.")[:MAX_COMPONENT_LENGTH].strip("-.")
    if text.endswith(".lock"):
        text = f"{text[: -len('.lock')]}-lock"
    return text


def agent_branch_name(branch_format, *, project_identifier, issue_identifier, run_short_id):
    """Return the Agent branch name for one Run.

    The Run short ID keeps names unique when two Runs work on the same issue.
    A Run keeps the name it was given; callers store it and never recompute
    it after the workspace format changes.
    """
    template = BRANCH_FORMATS.get(branch_format)
    if template is None:
        raise ValueError(f"Unknown branch format: {branch_format}")
    run = _sanitize_component(run_short_id).lower()
    if not run:
        raise ValueError("A Run short ID is required for an Agent branch name")
    name = template.format(
        project=_sanitize_component(project_identifier) or "project",
        issue=_sanitize_component(issue_identifier) or "issue",
        run=run,
    )
    if not is_valid_ref_name(name):
        raise ValueError("Agent branch name is not a valid Git ref")
    return name
