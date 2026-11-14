/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type CommandListInstance = {
  onKeyDown: (props: { event: KeyboardEvent }) => boolean;
};

type TSections = {
  items: readonly object[];
}[];

/** An item can opt out of selection with `disabled: true`; items without the field are enabled. */
const isDisabled = (item: object | undefined) => !!item && "disabled" in item && item.disabled === true;

type TIndex = {
  section: number;
  item: number;
};

type TArgs = {
  event: KeyboardEvent;
  sections: TSections;
  selectedIndex: TIndex;
};

export const DROPDOWN_NAVIGATION_KEYS = ["ArrowUp", "ArrowDown", "Enter"];

const isItemEnabled = (sections: TSections, index: TIndex) => !isDisabled(sections[index.section]?.items?.[index.item]);

/** One step up or down, wrapping across sections. */
const step = (sections: TSections, index: TIndex, direction: "up" | "down"): TIndex => {
  let nextSection = index.section;
  let nextItem = index.item;

  if (direction === "up") {
    nextItem--;
    if (nextItem < 0) {
      // Move to previous section
      nextSection--;
      if (nextSection < 0) {
        // Wrap to last section
        nextSection = sections.length - 1;
      }
      nextItem = sections[nextSection]?.items?.length - 1;
    }
  } else {
    nextItem++;
    if (nextItem >= sections[nextSection]?.items?.length) {
      // Move to next section
      nextSection++;
      if (nextSection >= sections.length) {
        // Wrap to first section
        nextSection = 0;
      }
      nextItem = 0;
    }
  }

  return { section: nextSection, item: nextItem };
};

/** The next selectable item in the key direction. Disabled items are skipped; with no other enabled item the selection stays. */
export const getNextValidIndex = (args: TArgs): TIndex | undefined => {
  const { event, sections, selectedIndex } = args;
  const direction = event.key === "ArrowUp" ? "up" : "down";
  if (!sections.length) return { section: 0, item: 0 };
  const total = sections.reduce((count, section) => count + (section.items?.length ?? 0), 0);

  let next = step(sections, selectedIndex, direction);
  for (let tries = 1; tries < total && !isItemEnabled(sections, next); tries++) {
    next = step(sections, next, direction);
  }
  return isItemEnabled(sections, next) ? next : selectedIndex;
};

/** The first item that is not disabled, else the first position. */
export const getFirstEnabledIndex = (sections: TSections): TIndex => {
  for (let section = 0; section < sections.length; section++) {
    const item = sections[section].items?.findIndex((entry) => !isDisabled(entry)) ?? -1;
    if (item >= 0) return { section, item };
  }
  return { section: 0, item: 0 };
};
