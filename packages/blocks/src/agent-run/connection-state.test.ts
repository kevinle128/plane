/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TAgentConnection } from "@plane/types";
import {
  canSelectModel,
  getHarnessConnectionAction,
  getHarnessConnectionTag,
  getMissingActionKey,
  getModelSourceNoteKey,
  isConnectionPending,
} from "./connection-state";

const connection = (overrides: Partial<TAgentConnection> = {}): TAgentConnection => ({
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
  ...overrides,
});

describe("getHarnessConnectionTag", () => {
  it("maps each of the four connection states to a label and a semantic tone", () => {
    expect(getHarnessConnectionTag("not_connected")).toEqual({
      labelKey: "agent_settings.status.not_connected",
      tone: "tertiary",
    });
    expect(getHarnessConnectionTag("connecting")).toEqual({
      labelKey: "agent_settings.status.connecting",
      tone: "accent",
    });
    expect(getHarnessConnectionTag("connected")).toEqual({
      labelKey: "agent_settings.status.connected",
      tone: "success",
    });
    expect(getHarnessConnectionTag("failed")).toEqual({ labelKey: "agent_settings.status.failed", tone: "danger" });
  });
});

describe("getHarnessConnectionAction", () => {
  it("offers Connect, Retry or Disconnect by state, and nothing while connecting", () => {
    expect(getHarnessConnectionAction("not_connected")).toBe("connect");
    expect(getHarnessConnectionAction("failed")).toBe("retry");
    expect(getHarnessConnectionAction("connected")).toBe("disconnect");
    expect(getHarnessConnectionAction("connecting")).toBeNull();
  });
});

describe("isConnectionPending", () => {
  it("polls only while a probe is running", () => {
    expect(isConnectionPending("connecting")).toBe(true);
    for (const state of ["not_connected", "connected", "failed"] as const)
      expect(isConnectionPending(state)).toBe(false);
  });
});

describe("canSelectModel", () => {
  const models = [{ id: "sonnet", label: "Sonnet", description: "", source: "reported" as const }];

  it("allows a model choice only for a connected Harness with reported models", () => {
    expect(canSelectModel(connection({ state: "connected", models }))).toBe(true);
    expect(canSelectModel(connection({ state: "connected", models: [] }))).toBe(false);
    expect(canSelectModel(connection({ state: "failed", models }))).toBe(false);
    expect(canSelectModel(connection({ state: "not_connected", models }))).toBe(false);
    expect(canSelectModel(undefined)).toBe(false);
  });
});

describe("getModelSourceNoteKey", () => {
  it("marks a fallback model as not reported by the Harness and leaves reported models plain", () => {
    expect(getModelSourceNoteKey({ id: "opus", label: "Opus", description: "", source: "fallback" })).toBe(
      "agent_settings.model.not_reported"
    );
    expect(getModelSourceNoteKey({ id: "opus", label: "Opus", description: "", source: "reported" })).toBeNull();
  });
});

describe("getMissingActionKey", () => {
  it("names the missing action for known codes and falls back for unknown ones", () => {
    expect(getMissingActionKey("worker_did_not_answer")).toBe("agent_settings.missing_action.worker_did_not_answer");
    expect(getMissingActionKey("permission")).toBe("agent_settings.missing_action.permission");
    expect(getMissingActionKey("sandbox_not_signed_in")).toBe("agent_settings.missing_action.sandbox_not_signed_in");
    expect(getMissingActionKey("harness_version_unverified")).toBe(
      "agent_settings.missing_action.harness_version_unverified"
    );
    expect(getMissingActionKey("teleport")).toBe("agent_settings.missing_action.generic");
    expect(getMissingActionKey("")).toBeNull();
  });
});
