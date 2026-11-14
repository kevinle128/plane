/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgent, TAgentConnection, TAgentHarness } from "@plane/types";

/** Test Agent with a connection; give only the values a test needs. */
export function makeAgent(
  overrides: Partial<Omit<TAgent, "connection">> = {},
  connection: Partial<TAgentConnection> = {}
): TAgent {
  const harness: TAgentHarness = overrides.harness ?? "claude_code";
  return {
    id: `agent-${harness}`,
    harness,
    name: "Claude",
    handle: "claude",
    instructions: "",
    mentionable: true,
    selected_model: "",
    available_for_mentions: false,
    ...overrides,
    connection: {
      state: "not_connected",
      probe_generation: 0,
      probe_requested_at: null,
      harness_version: "",
      location: "",
      models: [],
      capabilities: {},
      checks: [],
      missing_action: "",
      failure_hint: "",
      verified_at: null,
      ...connection,
    },
  };
}
