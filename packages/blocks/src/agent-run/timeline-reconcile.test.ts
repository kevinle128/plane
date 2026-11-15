/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { runEvent } from "./test-run-events";
import { reconcileRunEvents } from "./timeline-reconcile";

const thought = (seq: number) => runEvent(seq, "thought", { text: `t${seq}` });
const seqs = (events: { seq: number }[]) => events.map((event) => event.seq);

describe("reconcileRunEvents", () => {
  it("appends a page in seq order", () => {
    expect(seqs(reconcileRunEvents([thought(1), thought(2)], [thought(3), thought(4)]))).toEqual([1, 2, 3, 4]);
  });

  it("drops events it already has when pages overlap", () => {
    const current = [thought(1), thought(2), thought(3)];
    const merged = reconcileRunEvents(current, [thought(2), thought(3), thought(4)]);
    expect(seqs(merged)).toEqual([1, 2, 3, 4]);
    expect(merged[1]).toBe(current[1]);
  });

  it("fills a gap when the missing page arrives later", () => {
    const withGap = reconcileRunEvents([thought(1), thought(2)], [thought(5), thought(6)]);
    expect(seqs(withGap)).toEqual([1, 2, 5, 6]);
    expect(seqs(reconcileRunEvents(withGap, [thought(3), thought(4)]))).toEqual([1, 2, 3, 4, 5, 6]);
  });

  it("orders out-of-order pages and events by seq", () => {
    const merged = reconcileRunEvents([], [thought(7), thought(5)]);
    expect(seqs(reconcileRunEvents(merged, [thought(6), thought(4), thought(5)]))).toEqual([4, 5, 6, 7]);
  });

  it("keeps the same list when a page adds nothing", () => {
    const current = [thought(1)];
    expect(reconcileRunEvents(current, [])).toBe(current);
    expect(reconcileRunEvents(current, [thought(1)])).toBe(current);
  });

  it("stays exact over a long history delivered in overlapping pages", () => {
    const all = Array.from({ length: 1000 }, (_, index) => thought(index + 1));
    let events: ReturnType<typeof thought>[] = [];
    for (let start = 0; start < all.length; start += 90)
      events = reconcileRunEvents(events, all.slice(start, start + 100));
    expect(seqs(events)).toEqual(all.map((event) => event.seq));
  });
});
