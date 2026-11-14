/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TAgentModel } from "@plane/types";
import { agentSettingsFormOf, changesOf, mergeServerAgent } from "./settings-draft";
import { makeAgent } from "./test-agent";

const models = (...ids: string[]): TAgentModel[] =>
  ids.map((id) => ({ id, label: id, description: "", source: "reported" }));

describe("changesOf", () => {
  it("has no changes for an untouched form", () => {
    const form = agentSettingsFormOf(makeAgent());
    expect(changesOf(form)).toEqual({});
  });

  it("has only the fields that differ from the baseline", () => {
    const form = agentSettingsFormOf(makeAgent());
    expect(changesOf({ ...form, draft: { ...form.draft, instructions: "Be brief." } })).toEqual({
      instructions: "Be brief.",
    });
  });
});

describe("mergeServerAgent", () => {
  it("takes a rename from another tab and does not send the old name back on Save", () => {
    const form = agentSettingsFormOf(makeAgent({ name: "Claude" }));
    const edited = { ...form, draft: { ...form.draft, instructions: "Be brief." } };

    const merged = mergeServerAgent(edited, makeAgent({ name: "Claude B" }));

    expect(merged.draft.name).toBe("Claude B");
    expect(merged.draft.instructions).toBe("Be brief.");
    expect(changesOf(merged)).toEqual({ instructions: "Be brief." });
  });

  it("keeps a field the user changed when the server value of that field changes too", () => {
    const form = agentSettingsFormOf(makeAgent({ handle: "claude" }));
    const edited = { ...form, draft: { ...form.draft, handle: "mine" } };

    const merged = mergeServerAgent(edited, makeAgent({ handle: "theirs" }));

    expect(merged.draft.handle).toBe("mine");
    expect(changesOf(merged)).toEqual({ handle: "mine" });
  });

  it("does not enable Save when the server cleared the selected model after a new probe", () => {
    const connected = makeAgent({ selected_model: "opus" }, { state: "connected", models: models("opus", "sonnet") });
    const form = agentSettingsFormOf(connected);

    const merged = mergeServerAgent(
      form,
      makeAgent({ selected_model: "" }, { state: "connected", models: models("sonnet") })
    );

    expect(merged.draft.selected_model).toBe("");
    expect(changesOf(merged)).toEqual({});
  });

  it("never sends a model that the Harness no longer reports, also when the user picked it", () => {
    const connected = makeAgent({ selected_model: "" }, { state: "connected", models: models("opus", "sonnet") });
    const form = agentSettingsFormOf(connected);
    const edited = { ...form, draft: { ...form.draft, name: "Mine", selected_model: "opus" } };

    const merged = mergeServerAgent(
      edited,
      makeAgent({ selected_model: "" }, { state: "connected", models: models("sonnet") })
    );

    expect(merged.draft.selected_model).toBe("");
    expect(changesOf(merged)).toEqual({ name: "Mine" });
  });

  it("keeps a picked model that the Harness still reports", () => {
    const agent = makeAgent({ selected_model: "" }, { state: "connected", models: models("opus", "sonnet") });
    const form = agentSettingsFormOf(agent);
    const edited = { ...form, draft: { ...form.draft, selected_model: "opus" } };

    const merged = mergeServerAgent(edited, makeAgent({ mentionable: false }, agent.connection));

    expect(changesOf(merged)).toEqual({ selected_model: "opus" });
  });

  it("gives the same form back when the server values did not change", () => {
    const agent = makeAgent({ name: "Claude" });
    const form = agentSettingsFormOf(agent);
    const edited = { ...form, draft: { ...form.draft, instructions: "Be brief." } };
    expect(mergeServerAgent(edited, makeAgent({ name: "Claude" }))).toBe(edited);
  });
});
