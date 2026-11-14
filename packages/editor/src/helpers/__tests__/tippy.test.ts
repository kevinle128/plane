/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getFirstEnabledIndex, getNextValidIndex } from "../tippy";

const key = (name: string) => ({ key: name }) as KeyboardEvent;
const item = (disabled?: boolean) => ({ disabled });

describe("getNextValidIndex", () => {
  it("moves through items and wraps across sections when no item is disabled", () => {
    const sections = [{ items: [item(), item()] }, { items: [item()] }];
    expect(getNextValidIndex({ event: key("ArrowDown"), sections, selectedIndex: { section: 0, item: 1 } })).toEqual({
      section: 1,
      item: 0,
    });
    expect(getNextValidIndex({ event: key("ArrowDown"), sections, selectedIndex: { section: 1, item: 0 } })).toEqual({
      section: 0,
      item: 0,
    });
    expect(getNextValidIndex({ event: key("ArrowUp"), sections, selectedIndex: { section: 0, item: 0 } })).toEqual({
      section: 1,
      item: 0,
    });
  });

  it("skips disabled items in both directions", () => {
    const sections = [{ items: [item(), item(true)] }, { items: [item(true), item()] }];
    expect(getNextValidIndex({ event: key("ArrowDown"), sections, selectedIndex: { section: 0, item: 0 } })).toEqual({
      section: 1,
      item: 1,
    });
    expect(getNextValidIndex({ event: key("ArrowUp"), sections, selectedIndex: { section: 1, item: 1 } })).toEqual({
      section: 0,
      item: 0,
    });
  });

  it("keeps the selection when every other item is disabled", () => {
    const sections = [{ items: [item(), item(true), item(true)] }];
    expect(getNextValidIndex({ event: key("ArrowDown"), sections, selectedIndex: { section: 0, item: 0 } })).toEqual({
      section: 0,
      item: 0,
    });
  });
});

describe("getFirstEnabledIndex", () => {
  it("returns the first item that is not disabled", () => {
    expect(getFirstEnabledIndex([{ items: [item(true)] }, { items: [item(true), item()] }])).toEqual({
      section: 1,
      item: 1,
    });
  });

  it("returns the first position when every item is disabled or the list is empty", () => {
    expect(getFirstEnabledIndex([{ items: [item(true)] }])).toEqual({ section: 0, item: 0 });
    expect(getFirstEnabledIndex([])).toEqual({ section: 0, item: 0 });
  });
});
