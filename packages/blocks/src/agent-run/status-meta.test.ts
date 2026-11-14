/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TAgentRunStatus } from "@plane/types";
import { getAgentRunStatusMeta, isAgentRunActive } from "./status-meta";

const STATUSES: TAgentRunStatus[] = ["created", "in_progress", "awaiting", "completed", "failed", "stale", "stopped"];

describe("getAgentRunStatusMeta", () => {
  it("gives each of the seven states an icon, a label key and a semantic text token", () => {
    for (const status of STATUSES) {
      const meta = getAgentRunStatusMeta(status);
      expect(meta.icon).toBeTruthy();
      expect(meta.labelKey).toBe(`agent_run.status.${status}`);
      expect(meta.textClass).toMatch(
        /^text-(tertiary|secondary|accent-primary|warning-primary|success-primary|danger-primary)$/
      );
    }
  });

  it("never tells two states apart by color alone", () => {
    const icons = new Set(STATUSES.map((status) => getAgentRunStatusMeta(status).icon));
    const labels = new Set(STATUSES.map((status) => getAgentRunStatusMeta(status).labelKey));
    expect(icons.size).toBe(STATUSES.length);
    expect(labels.size).toBe(STATUSES.length);
  });

  it("maps states to the design colors and badge variants", () => {
    expect(getAgentRunStatusMeta("created")).toMatchObject({ textClass: "text-tertiary", badgeVariant: "neutral" });
    expect(getAgentRunStatusMeta("in_progress")).toMatchObject({
      textClass: "text-accent-primary",
      badgeVariant: "brand",
      spin: true,
    });
    expect(getAgentRunStatusMeta("awaiting")).toMatchObject({
      textClass: "text-warning-primary",
      badgeVariant: "warning",
    });
    expect(getAgentRunStatusMeta("completed")).toMatchObject({
      textClass: "text-success-primary",
      badgeVariant: "success",
    });
    expect(getAgentRunStatusMeta("failed")).toMatchObject({ textClass: "text-danger-primary", badgeVariant: "danger" });
    expect(getAgentRunStatusMeta("stale")).toMatchObject({
      textClass: "text-warning-primary",
      badgeVariant: "warning",
    });
    expect(getAgentRunStatusMeta("stopped")).toMatchObject({ textClass: "text-secondary", badgeVariant: "neutral" });
  });

  it("does not know an approval state", () => {
    expect(getAgentRunStatusMeta("approval" as TAgentRunStatus)).toBeUndefined();
  });
});

describe("isAgentRunActive", () => {
  it("is true while the Run can still change by itself", () => {
    expect(STATUSES.filter(isAgentRunActive)).toEqual(["created", "in_progress", "awaiting"]);
  });
});
