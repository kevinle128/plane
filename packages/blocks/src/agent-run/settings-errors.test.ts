/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TAgentSettingsError } from "@plane/types";
import { clearFieldError, getFieldErrorMessage } from "./settings-errors";

const translations: Record<string, string> = {
  "agent_settings.errors.handle_taken": "An agent with this handle already exists.",
};
/** Like the i18n `t`: a missing key gives the key back. */
const t = (key: string) => translations[key] ?? key;

describe("getFieldErrorMessage", () => {
  it("shows the translated message of a known code", () => {
    const error: TAgentSettingsError = { handle: ["handle taken"], codes: { handle: "taken" } };
    expect(getFieldErrorMessage(t, error, "handle")).toBe("An agent with this handle already exists.");
  });

  it("shows the API message for a code without a translation", () => {
    const error: TAgentSettingsError = { handle: ["Handle is odd."], codes: { handle: "odd" } };
    expect(getFieldErrorMessage(t, error, "handle")).toBe("Handle is odd.");
  });

  it("shows the API message when the error has no code for the field", () => {
    expect(getFieldErrorMessage(t, { name: ["Name is bad."] }, "name")).toBe("Name is bad.");
  });

  it("shows nothing when the field has no error", () => {
    expect(getFieldErrorMessage(t, null, "name")).toBeNull();
    expect(getFieldErrorMessage(t, { handle: ["x"], codes: { handle: "taken" } }, "name")).toBeNull();
    expect(getFieldErrorMessage(t, { name: [] }, "name")).toBeNull();
  });
});

describe("clearFieldError", () => {
  it("removes the messages and the code of one field and keeps the others", () => {
    const error: TAgentSettingsError = {
      status: 400,
      name: ["Name is bad."],
      handle: ["handle taken"],
      codes: { name: "invalid", handle: "taken" },
    };
    const next = clearFieldError(error, "handle");
    expect(getFieldErrorMessage(t, next, "handle")).toBeNull();
    expect(next).toEqual({ status: 400, name: ["Name is bad."], codes: { name: "invalid" } });
  });

  it("gives the same value back when the field has no error", () => {
    const error: TAgentSettingsError = { name: ["Name is bad."] };
    expect(clearFieldError(error, "handle")).toBe(error);
    expect(clearFieldError(null, "handle")).toBeNull();
  });
});
