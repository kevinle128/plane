/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { AGENT_CONNECTION_POLL_MS } from "@plane/constants";
import { agentsByHarness, withAgent } from "./agent-collection";
import { getAgentPollInterval } from "./agent-polling";
import { makeAgent } from "./test-agent";

describe("getAgentPollInterval", () => {
  it("does not poll before the Agents load or when no probe runs", () => {
    expect(getAgentPollInterval([])).toBe(0);
    expect(getAgentPollInterval([undefined, undefined])).toBe(0);
    for (const state of ["not_connected", "connected", "failed"] as const)
      expect(getAgentPollInterval([makeAgent({}, { state })])).toBe(0);
  });

  it("polls while any Agent has a running probe", () => {
    const agents = [makeAgent({}, { state: "connected" }), makeAgent({ harness: "codex" }, { state: "connecting" })];
    expect(getAgentPollInterval(agents)).toBe(AGENT_CONNECTION_POLL_MS);
  });

  it("starts polling when the store gets the connecting Agent from Connect, with no new fetch", () => {
    const fetched = agentsByHarness([makeAgent(), makeAgent({ harness: "codex", name: "Codex" })]);
    expect(getAgentPollInterval(Object.values(fetched))).toBe(0);

    const afterConnect = withAgent(fetched, makeAgent({}, { state: "connecting", probe_generation: 1 }));
    expect(getAgentPollInterval(Object.values(afterConnect))).toBe(AGENT_CONNECTION_POLL_MS);

    const afterReport = withAgent(afterConnect, makeAgent({}, { state: "connected", probe_generation: 1 }));
    expect(getAgentPollInterval(Object.values(afterReport))).toBe(0);
  });
});
