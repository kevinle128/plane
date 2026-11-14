/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { insertRunsByTime, type TActivityRow } from "./activity-merge";

type TEntry = { id: string; created_at?: string };
type TRun = { id: string; created_at: string };
const at = (minute: number) => `2026-11-14T10:${String(minute).padStart(2, "0")}:00Z`;
const entry = (id: string, minute?: number): TEntry => ({
  id,
  created_at: minute === undefined ? undefined : at(minute),
});
const run = (id: string, minute: number): TRun => ({ id, created_at: at(minute) });
const ids = (rows: TActivityRow<TEntry, TRun>[]) =>
  rows.map((row) => (row.type === "entry" ? row.entry.id : `run:${row.run.id}`));

describe("insertRunsByTime", () => {
  it("places each Run by creation time after its trigger comment in ascending order", () => {
    const entries = [entry("a", 1), entry("trigger", 2), entry("b", 5)];
    expect(ids(insertRunsByTime(entries, [run("r1", 2), run("r0", 0)], "asc"))).toEqual([
      "run:r0",
      "a",
      "trigger",
      "run:r1",
      "b",
    ]);
  });

  it("places each Run before its trigger comment in descending order", () => {
    const entries = [entry("b", 5), entry("trigger", 2), entry("a", 1)];
    expect(ids(insertRunsByTime(entries, [run("r1", 2), run("r9", 9)], "desc"))).toEqual([
      "run:r9",
      "b",
      "run:r1",
      "trigger",
      "a",
    ]);
  });

  it("keeps the given entry order, even when entries share a time or are out of order", () => {
    const entries = [entry("x", 3), entry("y", 3), entry("late", 8), entry("early", 1), entry("no-time")];
    const rows = ids(insertRunsByTime(entries, [run("r", 4)], "asc"));
    expect(rows.filter((id) => !id.startsWith("run:"))).toEqual(["x", "y", "late", "early", "no-time"]);
    expect(rows).toEqual(["x", "y", "run:r", "late", "early", "no-time"]);
  });

  it("appends Runs newer than every entry and returns entries alone without Runs", () => {
    expect(ids(insertRunsByTime([entry("a", 1)], [run("r", 9)], "asc"))).toEqual(["a", "run:r"]);
    expect(ids(insertRunsByTime([entry("a", 1)], [], "asc"))).toEqual(["a"]);
  });
});
