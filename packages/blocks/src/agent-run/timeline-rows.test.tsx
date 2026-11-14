/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { runEvent } from "./test-run-events";
import { groupRunTimeline } from "./timeline-group";
import { RunTimelineRows } from "./timeline-rows";

// Translations load asynchronously in jsdom; echo the key and its values so assertions do not race the load.
vi.mock("@plane/i18n", () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => (params ? `${key} ${Object.values(params).join(" ")}` : key),
  }),
}));

const events = [
  runEvent(1, "message", { role: "user", text: "Why does login fail?" }),
  runEvent(2, "thought", { text: "Look at the auth module first." }),
  runEvent(3, "tool_call", { call_id: "c1", name: "Read", input: { file_path: "src/auth.ts" } }),
  runEvent(4, "tool_result", { call_id: "c1", part: 0, parts: 1, text: "export const ttl = 0;", is_error: false }),
  runEvent(5, "message", { role: "assistant", text: "The token lifetime is zero." }),
];

const renderRows = (active = false) =>
  // An active Run is still working, so its answer has not arrived yet.
  render(<RunTimelineRows entries={groupRunTimeline(active ? events.slice(0, 4) : events, active)} />);

describe("RunTimelineRows", () => {
  it("shows the request and the agent answer expanded", () => {
    renderRows();
    expect(screen.getByText("Why does login fail?")).toBeTruthy();
    expect(screen.getByText("The token lifetime is zero.")).toBeTruthy();
  });

  it("collapses a finished Working group and opens it from the keyboard", async () => {
    const user = userEvent.setup();
    renderRows();
    const group = screen.getByRole("button", { name: "agent_run.timeline.worked_for 3s" });
    expect(group.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("Read")).toBeNull();

    group.focus();
    await user.keyboard("{Enter}");
    expect(group.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("Read")).toBeTruthy();
  });

  it("shows thoughts and tool calls collapsed to one line until opened", async () => {
    const user = userEvent.setup();
    renderRows(true);
    // Active Runs keep the last group open with its step count.
    const group = screen.getByRole("button", { name: "agent_run.timeline.working 2" });
    expect(group.getAttribute("aria-expanded")).toBe("true");

    const thought = screen.getByRole("button", { name: /Look at the auth module first\./ });
    expect(thought.getAttribute("aria-expanded")).toBe("false");
    const tool = screen.getByRole("button", { name: /Read/ });
    expect(tool.getAttribute("aria-expanded")).toBe("false");
    expect(screen.getByText("src/auth.ts")).toBeTruthy();
    expect(screen.queryByText("export const ttl = 0;")).toBeNull();

    await user.click(tool);
    expect(tool.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("export const ttl = 0;")).toBeTruthy();
  });

  it("renders markdown through the given renderer", () => {
    render(
      <RunTimelineRows
        entries={groupRunTimeline(events, false)}
        renderMarkdown={(text) => <em data-testid="markdown">{text}</em>}
      />
    );
    expect(screen.getAllByTestId("markdown").map((node) => node.textContent)).toEqual(["The token lifetime is zero."]);
  });
});
