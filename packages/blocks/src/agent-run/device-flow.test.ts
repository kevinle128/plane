/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getDeviceCodeExpiry } from "./device-flow";

const NOW = Date.parse("2026-11-12T10:00:00Z");

describe("getDeviceCodeExpiry", () => {
  it("formats the time left as minutes and zero-padded seconds", () => {
    const expiry = getDeviceCodeExpiry("2026-11-12T10:14:22Z", NOW);
    expect(expiry).toEqual({ expired: false, secondsLeft: 862, label: "14:22" });
  });

  it("pads single-digit seconds", () => {
    expect(getDeviceCodeExpiry("2026-11-12T10:01:05Z", NOW).label).toBe("1:05");
  });

  it("rounds partial seconds up so the label never shows 0:00 before expiry", () => {
    expect(getDeviceCodeExpiry("2026-11-12T10:00:00.400Z", NOW)).toEqual({
      expired: false,
      secondsLeft: 1,
      label: "0:01",
    });
  });

  it("reports an expired code at and after the expiry time", () => {
    expect(getDeviceCodeExpiry("2026-11-12T10:00:00Z", NOW)).toEqual({ expired: true, secondsLeft: 0, label: "0:00" });
    expect(getDeviceCodeExpiry("2026-11-12T09:59:00Z", NOW).expired).toBe(true);
  });

  it("treats an unreadable date as expired", () => {
    expect(getDeviceCodeExpiry("not-a-date", NOW)).toEqual({ expired: true, secondsLeft: 0, label: "0:00" });
  });
});
