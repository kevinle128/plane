/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  getDeniedReasonCode,
  getDeviceCodeDeadline,
  getDeviceCodeExpiry,
  getDevicePollErrorAction,
} from "./device-flow";

const NOW = Date.parse("2026-11-12T10:00:00Z");

describe("getDeviceCodeExpiry", () => {
  it("formats the time left as minutes and zero-padded seconds", () => {
    const expiry = getDeviceCodeExpiry(NOW + 862_000, NOW);
    expect(expiry).toEqual({ expired: false, secondsLeft: 862, label: "14:22" });
  });

  it("pads single-digit seconds", () => {
    expect(getDeviceCodeExpiry(NOW + 65_000, NOW).label).toBe("1:05");
  });

  it("rounds partial seconds up so the label never shows 0:00 before expiry", () => {
    expect(getDeviceCodeExpiry(NOW + 400, NOW)).toEqual({ expired: false, secondsLeft: 1, label: "0:01" });
  });

  it("reports an expired code at and after the deadline", () => {
    expect(getDeviceCodeExpiry(NOW, NOW)).toEqual({ expired: true, secondsLeft: 0, label: "0:00" });
    expect(getDeviceCodeExpiry(NOW - 60_000, NOW).expired).toBe(true);
  });

  it("treats an unreadable deadline as expired", () => {
    expect(getDeviceCodeExpiry(Number.NaN, NOW)).toEqual({ expired: true, secondsLeft: 0, label: "0:00" });
  });
});

describe("getDeviceCodeDeadline", () => {
  it("adds the server lifetime of the code to the local time the response arrived", () => {
    // The browser clock is 20 minutes fast: the absolute server expiry is already in the local past.
    const receivedAt = Date.parse("2026-11-12T10:20:00Z");
    const deadline = getDeviceCodeDeadline(
      { created_at: "2026-11-12T10:00:00Z", expires_at: "2026-11-12T10:15:00Z" },
      receivedAt
    );
    expect(deadline).toBe(receivedAt + 15 * 60 * 1000);
    expect(getDeviceCodeExpiry(deadline, receivedAt).label).toBe("15:00");
  });

  it("uses the absolute expiry when the server creation time is missing or unreadable", () => {
    const expiresAt = "2026-11-12T10:15:00Z";
    expect(getDeviceCodeDeadline({ expires_at: expiresAt }, NOW)).toBe(Date.parse(expiresAt));
    expect(getDeviceCodeDeadline({ expires_at: expiresAt, created_at: "soon" }, NOW)).toBe(Date.parse(expiresAt));
  });

  it("gives an expired deadline when the server expiry is unreadable", () => {
    const deadline = getDeviceCodeDeadline({ expires_at: "never", created_at: "2026-11-12T10:00:00Z" }, NOW);
    expect(getDeviceCodeExpiry(deadline, NOW).expired).toBe(true);
  });
});

describe("getDevicePollErrorAction", () => {
  it("polls again after a network error, a server error, a timeout or a rate limit", () => {
    for (const status of [undefined, 0, 500, 502, 503, 504, 408, 429]) {
      expect(getDevicePollErrorAction(status)).toBe("retry");
    }
  });

  it("stops after an error that another poll cannot fix", () => {
    for (const status of [400, 403, 404, 409]) {
      expect(getDevicePollErrorAction(status)).toBe("stop");
    }
  });
});

describe("getDeniedReasonCode", () => {
  it("gives no reason when the user refused, so the refusal text shows", () => {
    expect(getDeniedReasonCode("access_denied")).toBeNull();
    expect(getDeniedReasonCode("")).toBeNull();
  });

  it("gives the error code when GitHub or Plane failed for another reason", () => {
    expect(getDeniedReasonCode("incorrect_client_credentials")).toBe("incorrect_client_credentials");
    expect(getDeniedReasonCode("github_identity_failed")).toBe("github_identity_failed");
  });
});
