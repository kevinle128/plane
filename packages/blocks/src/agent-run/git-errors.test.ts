/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { isReconnectErrorCode } from "./git-errors";

describe("isReconnectErrorCode", () => {
  it("is true for a token the provider no longer accepts", () => {
    expect(isReconnectErrorCode("github_token_invalid")).toBe(true);
    expect(isReconnectErrorCode("gitlab_token_invalid")).toBe(true);
    expect(isReconnectErrorCode("provider_reconnect_required")).toBe(true);
  });

  it("is false for other errors and for no error", () => {
    expect(isReconnectErrorCode("github_unexpected_response")).toBe(false);
    expect(isReconnectErrorCode("provider_disconnected")).toBe(false);
    expect(isReconnectErrorCode("")).toBe(false);
    expect(isReconnectErrorCode(undefined)).toBe(false);
  });
});
