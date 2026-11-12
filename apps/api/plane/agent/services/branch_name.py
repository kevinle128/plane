# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Git ref names: validation of user-supplied refs and Agent branch names."""

MAX_REF_BYTES = 255
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
