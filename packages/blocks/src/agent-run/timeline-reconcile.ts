/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgentRunEvent } from "@plane/types";

/**
 * Merges a page of Run events into the loaded events: one entry per event ID, in seq order. Pages may
 * overlap, leave gaps that a later page fills, or arrive out of order. Returns `current` itself when the
 * page adds nothing, so observers do not re-render.
 */
export function reconcileRunEvents(
  current: readonly TAgentRunEvent[],
  incoming: readonly TAgentRunEvent[]
): TAgentRunEvent[] {
  const known = new Set(current.map((event) => event.id));
  const added = new Map<string, TAgentRunEvent>();
  for (const event of incoming) if (!known.has(event.id)) added.set(event.id, event);
  if (added.size === 0) return current as TAgentRunEvent[];
  return [...current, ...added.values()].toSorted((a, b) => a.seq - b.seq);
}
