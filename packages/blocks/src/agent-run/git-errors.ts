/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

const RECONNECT_ERROR_CODES = new Set(["github_token_invalid", "gitlab_token_invalid", "provider_reconnect_required"]);

/** True when an API error code means the connection must be connected again, so the page reloads it. */
export function isReconnectErrorCode(code: string | undefined): boolean {
  return !!code && RECONNECT_ERROR_CODES.has(code);
}
