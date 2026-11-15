# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import mistune

# Markdown to HTML. Raw HTML in the input is escaped and shown as text, so prose such as
# ``Promise<void>`` keeps its angle brackets. Callers still sanitize the result (for
# example with ``validate_html_content``) before they store it.
markdown = mistune.create_markdown(escape=True, plugins=["strikethrough", "table", "url"])
