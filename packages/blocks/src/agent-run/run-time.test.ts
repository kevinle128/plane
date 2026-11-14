/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { formatRunDuration, getRunElapsedMs } from "./run-time";

describe("formatRunDuration", () => {
  it("shows seconds, minutes with seconds, and hours with minutes", () => {
    expect(formatRunDuration(0)).toBe("0s");
    expect(formatRunDuration(45_900)).toBe("45s");
    expect(formatRunDuration(184_000)).toBe("3m 4s");
    expect(formatRunDuration(3_720_000)).toBe("1h 2m");
  });

  it("treats a negative or unknown span as zero", () => {
    expect(formatRunDuration(-5)).toBe("0s");
    expect(formatRunDuration(Number.NaN)).toBe("0s");
  });
});

describe("getRunElapsedMs", () => {
  const now = new Date("2026-11-14T10:10:00Z");

  it("counts from the start to the end of a finished Run", () => {
    expect(
      getRunElapsedMs(
        { created_at: "2026-11-14T10:00:00Z", started_at: "2026-11-14T10:01:00Z", ended_at: "2026-11-14T10:03:30Z" },
        now
      )
    ).toBe(150_000);
  });

  it("counts to now while the Run works, and from creation before pickup", () => {
    expect(
      getRunElapsedMs({ created_at: "2026-11-14T10:00:00Z", started_at: "2026-11-14T10:09:00Z", ended_at: null }, now)
    ).toBe(60_000);
    expect(getRunElapsedMs({ created_at: "2026-11-14T10:09:30Z", started_at: null, ended_at: null }, now)).toBe(30_000);
  });
});
