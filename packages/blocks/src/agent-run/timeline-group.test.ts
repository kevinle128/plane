/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { runEvent } from "./test-run-events";
import { groupRunTimeline, type TTimelineWorkEntry } from "./timeline-group";

const user = runEvent(1, "message", { role: "user", text: "Why does login fail?" });
const thought = (seq: number) => runEvent(seq, "thought", { text: `thinking ${seq}` });
const call = (seq: number, callId: string) =>
  runEvent(seq, "tool_call", { call_id: callId, name: "Read", input: { file_path: "src/auth.ts" } });
const result = (seq: number, callId: string, part: number, parts: number, text: string) =>
  runEvent(seq, "tool_result", { call_id: callId, part, parts, text, is_error: false });
const answer = (seq: number) => runEvent(seq, "message", { role: "assistant", text: "The token expires." });

const works = (entries: ReturnType<typeof groupRunTimeline>) =>
  entries.filter((entry): entry is TTimelineWorkEntry => entry.type === "work");

describe("groupRunTimeline", () => {
  it("puts thoughts, tool calls and their results between messages into one Working group", () => {
    const events = [user, thought(2), call(3, "c1"), result(4, "c1", 0, 1, "file"), thought(5), answer(6)];
    const entries = groupRunTimeline(events, false);
    expect(entries.map((entry) => entry.type)).toEqual(["event", "work", "event"]);
    const [work] = works(entries);
    expect(work.steps.map((step) => step.type)).toEqual(["thought", "tool", "thought"]);
    expect(work.stepCount).toBe(3);
  });

  it("counts steps while active and measures the duration to the next event when done", () => {
    const active = works(groupRunTimeline([user, thought(2), call(3, "c1")], true))[0];
    expect(active).toMatchObject({ active: true, stepCount: 2 });

    const done = works(groupRunTimeline([user, thought(2), call(3, "c1"), answer(9)], false))[0];
    expect(done.active).toBe(false);
    expect(done.durationMs).toBe(7000);
  });

  it("is not active when more events follow the group, even if the Run is active", () => {
    const [work] = works(groupRunTimeline([user, thought(2), answer(3)], true));
    expect(work.active).toBe(false);
  });

  it("joins tool result parts by call ID and part index, in any order", () => {
    const events = [
      call(2, "c1"),
      call(3, "c2"),
      result(4, "c2", 0, 1, "only"),
      result(5, "c1", 1, 2, "world"),
      result(6, "c1", 0, 2, "hello "),
    ];
    const [work] = works(groupRunTimeline(events, false));
    expect(work.steps).toHaveLength(2);
    expect(work.steps[0]).toMatchObject({ type: "tool", name: "Read", target: "src/auth.ts" });
    expect(work.steps[0].type === "tool" && work.steps[0].result).toEqual({
      text: "hello world",
      isError: false,
      complete: true,
    });
    expect(work.steps[1].type === "tool" && work.steps[1].result?.text).toBe("only");
  });

  it("marks a result incomplete until every part arrived", () => {
    const [work] = works(groupRunTimeline([call(2, "c1"), result(3, "c1", 0, 3, "a")], true));
    expect(work.steps[0].type === "tool" && work.steps[0].result?.complete).toBe(false);
  });

  it("keeps a result whose call is missing as one step for all its parts", () => {
    const entries = groupRunTimeline(
      [result(2, "lost", 0, 2, "out"), answer(3), result(4, "lost", 1, 2, "put")],
      false
    );
    expect(entries.map((entry) => entry.type)).toEqual(["work", "event"]);
    const [work] = works(entries);
    expect(work.steps).toHaveLength(1);
    expect(work.steps[0]).toMatchObject({ type: "tool", name: "", result: { text: "output", complete: true } });
  });

  it("keeps messages, status, errors and the conclusion as their own entries in order", () => {
    const events = [
      runEvent(1, "status", { code: "cloning", text: "Cloning" }),
      user,
      runEvent(3, "error", { code: "gateway", message: "No answer" }),
      runEvent(4, "conclusion", { text: "Done", comment_id: "c", status: "completed" }),
    ];
    expect(
      groupRunTimeline(events, false).map((entry) => (entry.type === "event" ? entry.event.kind : "work"))
    ).toEqual(["status", "message", "error", "conclusion"]);
  });
});
