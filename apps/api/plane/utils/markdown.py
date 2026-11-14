# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import mistune

# Markdown to HTML. Raw HTML passes through unchanged, so callers must sanitize the
# result (for example with ``validate_html_content``) before they store it.
markdown = mistune.create_markdown(escape=False, plugins=["strikethrough", "table", "url"])
