/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { agentsByHarness, withAgent } from "./agent-collection";
import { makeAgent } from "./test-agent";

describe("agentsByHarness", () => {
  it("keys the fetched Agents by Harness", () => {
    const claude = makeAgent();
    const codex = makeAgent({ harness: "codex", name: "Codex" });
    expect(agentsByHarness([claude, codex])).toEqual({ claude_code: claude, codex });
  });

  it("gives a full replacement, so an Agent that the server no longer returns goes away", () => {
    const before = agentsByHarness([makeAgent(), makeAgent({ harness: "codex" })]);
    const after = agentsByHarness([makeAgent({ name: "Renamed" })]);
    expect(before.codex).toBeDefined();
    expect(after).toEqual({ claude_code: makeAgent({ name: "Renamed" }) });
  });
});

describe("withAgent", () => {
  it("replaces the Agent of one Harness and keeps the others", () => {
    const codex = makeAgent({ harness: "codex" });
    const current = agentsByHarness([makeAgent(), codex]);
    const updated = makeAgent({ name: "Renamed" }, { state: "connecting" });
    const next = withAgent(current, updated);
    expect(next).toEqual({ claude_code: updated, codex });
    expect(current.claude_code?.name).toBe("Claude");
  });

  it("adds an Agent when the workspace has no Agents yet", () => {
    const agent = makeAgent();
    expect(withAgent(undefined, agent)).toEqual({ claude_code: agent });
  });
});
