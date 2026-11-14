/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TActivityRow<TEntry, TRun> = { type: "entry"; entry: TEntry } | { type: "run"; run: TRun };

const timeOf = (value: string | undefined) => (value ? new Date(value).getTime() : 0);

/**
 * Inserts Run cards into an activity list that is already in `order`, by Run creation time. The entries
 * keep their given order. A Run comes after an entry of the same time in ascending order and before it in
 * descending order, so a card always reads after the comment that started it.
 */
export function insertRunsByTime<TEntry extends { created_at?: string }, TRun extends { created_at: string }>(
  entries: readonly TEntry[],
  runs: readonly TRun[],
  order: "asc" | "desc"
): TActivityRow<TEntry, TRun>[] {
  const ascending = order === "asc";
  const pending = runs.toSorted((a, b) =>
    ascending ? timeOf(a.created_at) - timeOf(b.created_at) : timeOf(b.created_at) - timeOf(a.created_at)
  );
  const rows: TActivityRow<TEntry, TRun>[] = [];
  let next = 0;
  for (const entry of entries) {
    const entryTime = timeOf(entry.created_at);
    while (next < pending.length) {
      const runTime = timeOf(pending[next].created_at);
      if (ascending ? runTime >= entryTime : runTime < entryTime) break;
      rows.push({ type: "run", run: pending[next++] });
    }
    rows.push({ type: "entry", entry });
  }
  while (next < pending.length) rows.push({ type: "run", run: pending[next++] });
  return rows;
}
