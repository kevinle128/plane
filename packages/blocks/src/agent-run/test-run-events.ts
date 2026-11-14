/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgentRunEvent } from "@plane/types";

/** A Run event for tests; `seq` also sets the ID and a time one second per seq after 10:00. */
export const runEvent = <TKind extends TAgentRunEvent["kind"]>(
  seq: number,
  kind: TKind,
  payload: Extract<TAgentRunEvent, { kind: TKind }>["payload"]
): TAgentRunEvent =>
  ({
    id: `event-${seq}`,
    seq,
    kind,
    payload,
    turn_index: 0,
    created_at: new Date(Date.UTC(2026, 10, 14, 10, 0, seq)).toISOString(),
  }) as TAgentRunEvent;
