/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getTokenExpiryState } from "./token-expiry";

const NOW = Date.parse("2026-11-12T10:00:00Z");

describe("getTokenExpiryState", () => {
  it("reports no warning for a token that never expires", () => {
    expect(getTokenExpiryState(null, NOW)).toEqual({ expired: false, expiresSoon: false });
  });

  it("warns within 14 days of expiry", () => {
    expect(getTokenExpiryState("2026-11-26T00:00:00Z", NOW)).toEqual({ expired: false, expiresSoon: true });
  });

  it("does not warn when expiry is further than 14 days away", () => {
    expect(getTokenExpiryState("2026-11-27T00:00:00Z", NOW)).toEqual({ expired: false, expiresSoon: false });
  });

  it("reports an expired token", () => {
    expect(getTokenExpiryState("2026-11-12T00:00:00Z", NOW)).toEqual({ expired: true, expiresSoon: false });
  });

  it("ignores an unreadable date", () => {
    expect(getTokenExpiryState("soon", NOW)).toEqual({ expired: false, expiresSoon: false });
  });
});
