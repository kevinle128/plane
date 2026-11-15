/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RunStatusBadge, RunStatusLabel } from "./run-status-badge";

// Translations load asynchronously in jsdom; echo the key and its values so assertions do not race the load.
vi.mock("@plane/i18n", () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => (params ? `${key} ${Object.values(params).join(" ")}` : key),
  }),
}));

describe("RunStatusBadge", () => {
  it("shows the status label as text with an icon", () => {
    const { container } = render(<RunStatusBadge status="failed" />);
    expect(screen.getByText("agent_run.status.failed")).toBeTruthy();
    expect(container.querySelector("svg")).toBeTruthy();
  });
});

describe("RunStatusLabel", () => {
  it("colors the icon and label with the status token and spins only while in progress", () => {
    const { container, rerender } = render(<RunStatusLabel status="in_progress" />);
    const label = screen.getByText("agent_run.status.in_progress");
    expect(label.closest(".text-accent-primary")).toBeTruthy();
    expect(container.querySelector(".animate-spin")).toBeTruthy();

    rerender(<RunStatusLabel status="completed" />);
    expect(screen.getByText("agent_run.status.completed").closest(".text-success-primary")).toBeTruthy();
    expect(container.querySelector(".animate-spin")).toBeNull();
  });
});
