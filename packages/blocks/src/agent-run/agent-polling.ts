/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { AGENT_CONNECTION_POLL_MS } from "@plane/constants";
import type { TAgent } from "@plane/types";
import { isConnectionPending } from "./connection-state";

/**
 * Poll interval of the Agents fetch: the poll period while any probe runs, else 0 (no poll).
 * Give it the Agents from the store, not the last fetch result: Connect writes the connecting Agent
 * to the store only, and the poll must start from that write.
 */
export function getAgentPollInterval(agents: readonly (TAgent | undefined)[]): number {
  return agents.some((agent) => agent && isConnectionPending(agent.connection.state)) ? AGENT_CONNECTION_POLL_MS : 0;
}
