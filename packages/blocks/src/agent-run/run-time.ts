/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgentRun } from "@plane/types";

/** Compact elapsed time: `45s`, `3m 4s`, `1h 2m`. The units are the same in every locale. */
export function formatRunDuration(ms: number): string {
  const totalSeconds = Number.isFinite(ms) && ms > 0 ? Math.floor(ms / 1000) : 0;
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

/** Time from the start of the Run (its creation before pickup) to its end, or to `now` while it runs. */
export function getRunElapsedMs(run: Pick<TAgentRun, "created_at" | "started_at" | "ended_at">, now: Date): number {
  const start = new Date(run.started_at ?? run.created_at).getTime();
  const end = run.ended_at ? new Date(run.ended_at).getTime() : now.getTime();
  return Math.max(0, end - start);
}
