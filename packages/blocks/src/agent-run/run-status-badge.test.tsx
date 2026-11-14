/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RunStatusBadge, RunStatusLabel } from "./run-status-badge";

describe("RunStatusBadge", () => {
  it("shows the status label as text with an icon", () => {
    const { container } = render(<RunStatusBadge status="failed" />);
    expect(screen.getByText("Failed")).toBeTruthy();
    expect(container.querySelector("svg")).toBeTruthy();
  });
});

describe("RunStatusLabel", () => {
  it("colors the icon and label with the status token and spins only while in progress", () => {
    const { container, rerender } = render(<RunStatusLabel status="in_progress" />);
    const label = screen.getByText("In progress");
    expect(label.closest(".text-accent-primary")).toBeTruthy();
    expect(container.querySelector(".animate-spin")).toBeTruthy();

    rerender(<RunStatusLabel status="completed" />);
    expect(screen.getByText("Completed").closest(".text-success-primary")).toBeTruthy();
    expect(container.querySelector(".animate-spin")).toBeNull();
  });
});
