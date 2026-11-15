/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgentRunEvent } from "@plane/types";

export type TTimelineToolResult = {
  /** All parts received so far, joined in part order. */
  text: string;
  isError: boolean;
  /** Every part has arrived. */
  complete: boolean;
};

export type TTimelineThoughtStep = { type: "thought"; id: string; text: string };

export type TTimelineToolStep = {
  type: "tool";
  id: string;
  /** Tool name; empty when only the result is known. */
  name: string;
  /** Main argument of the call (file, command, pattern or URL), shown in the collapsed row. */
  target: string;
  input: unknown;
  result: TTimelineToolResult | undefined;
};

export type TTimelineStep = TTimelineThoughtStep | TTimelineToolStep;

/** Consecutive thoughts and tool work between two other events. */
export type TTimelineWorkEntry = {
  type: "work";
  /** ID of the first event of the group; stable while the group grows. */
  id: string;
  steps: TTimelineStep[];
  stepCount: number;
  /** From the first event of the group to the event after it, else to its last event. */
  durationMs: number;
  /** The group is the end of an active Run, so work continues in it. */
  active: boolean;
};

export type TTimelineEventEntry = { type: "event"; event: TAgentRunEvent };

export type TTimelineEntry = TTimelineEventEntry | TTimelineWorkEntry;

const TARGET_KEYS = ["file_path", "path", "command", "pattern", "url", "query", "description"];

/** The main argument of a tool call, for its one-line summary. */
function getToolTarget(input: unknown): string {
  if (!input || typeof input !== "object") return "";
  const values = input as Record<string, unknown>;
  for (const key of TARGET_KEYS) {
    const value = values[key];
    if (typeof value === "string" && value.trim()) return value.trim().split("\n")[0];
  }
  return "";
}

const text = (value: unknown) => (typeof value === "string" ? value : "");
const time = (event: TAgentRunEvent) => new Date(event.created_at).getTime();

/** Joins the parts of each tool result by call ID. */
function collectToolResults(events: readonly TAgentRunEvent[]): Map<string, TTimelineToolResult> {
  const partsByCall = new Map<string, { parts: Map<number, string>; total: number; isError: boolean }>();
  for (const event of events) {
    if (event.kind !== "tool_result") continue;
    const callId = text(event.payload.call_id);
    const entry = partsByCall.get(callId) ?? { parts: new Map(), total: 1, isError: false };
    entry.parts.set(Number(event.payload.part) || 0, text(event.payload.text));
    entry.total = Math.max(entry.total, Number(event.payload.parts) || 1);
    entry.isError = entry.isError || event.payload.is_error === true;
    partsByCall.set(callId, entry);
  }
  const results = new Map<string, TTimelineToolResult>();
  for (const [callId, entry] of partsByCall) {
    const order = [...entry.parts.keys()].toSorted((a, b) => a - b);
    results.set(callId, {
      text: order.map((part) => entry.parts.get(part)).join(""),
      isError: entry.isError,
      complete: entry.parts.size >= entry.total,
    });
  }
  return results;
}

/**
 * Builds the panel timeline from events in seq order. Thoughts, tool calls and tool results between
 * other events form one Working group; each tool call carries its joined result. Every other event is
 * its own entry.
 */
export function groupRunTimeline(events: readonly TAgentRunEvent[], runActive: boolean): TTimelineEntry[] {
  const results = collectToolResults(events);
  const calledIds = new Set(
    events.flatMap((event) => (event.kind === "tool_call" ? [text(event.payload.call_id)] : []))
  );
  const entries: TTimelineEntry[] = [];
  const shownResults = new Set<string>();
  let group: TTimelineWorkEntry | null = null;
  let groupStart = 0;
  let groupLast = 0;

  for (const event of events) {
    let step: TTimelineStep | null = null;
    if (event.kind === "thought") {
      step = { type: "thought", id: event.id, text: text(event.payload.text) };
    } else if (event.kind === "tool_call") {
      step = {
        type: "tool",
        id: event.id,
        name: text(event.payload.name),
        target: getToolTarget(event.payload.input),
        input: event.payload.input,
        result: results.get(text(event.payload.call_id)),
      };
    } else if (event.kind === "tool_result") {
      const callId = text(event.payload.call_id);
      // A result joins its call; only a result without a call, once per call ID, gets its own step.
      if (!calledIds.has(callId) && !shownResults.has(callId)) {
        shownResults.add(callId);
        step = { type: "tool", id: event.id, name: "", target: "", input: undefined, result: results.get(callId) };
      } else {
        if (group) groupLast = time(event);
        continue;
      }
    }

    if (!step) {
      if (group) group.durationMs = Math.max(0, time(event) - groupStart);
      group = null;
      entries.push({ type: "event", event });
      continue;
    }
    if (!group) {
      group = { type: "work", id: event.id, steps: [], stepCount: 0, durationMs: 0, active: false };
      groupStart = time(event);
      entries.push(group);
    }
    groupLast = time(event);
    group.steps.push(step);
    group.stepCount = group.steps.length;
  }

  if (group) {
    group.durationMs = Math.max(0, groupLast - groupStart);
    group.active = runActive;
  }
  return entries;
}
