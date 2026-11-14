/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgent, TAgentHarness } from "@plane/types";

/** The Agents of one workspace, keyed by Harness. */
export type TAgentsByHarness = Partial<Record<TAgentHarness, TAgent>>;

/** The fetched Agents keyed by Harness. Use it to replace all Agents, so a removed Agent goes away. */
export function agentsByHarness(agents: TAgent[]): TAgentsByHarness {
  const byHarness: TAgentsByHarness = {};
  for (const agent of agents) byHarness[agent.harness] = agent;
  return byHarness;
}

/** A copy with the Agent of one Harness replaced; the other Agents stay. */
export function withAgent(current: TAgentsByHarness | undefined, agent: TAgent): TAgentsByHarness {
  return { ...current, [agent.harness]: agent };
}
