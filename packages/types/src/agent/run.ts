/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgentHarness } from "./agent";

/**
 * Run status as the API returns it. `stale` is derived by the API: the Run is `in_progress` or `awaiting`
 * and its Worker lease has expired.
 */
export type TAgentRunStatus = "created" | "in_progress" | "awaiting" | "completed" | "failed" | "stopped" | "stale";

/** One Run: one invocation of an Agent, started by a mention in a work-item comment. */
export type TAgentRun = {
  id: string;
  /** Human Run label, for example `R-7KQ2MX`. */
  short_id: string;
  status: TAgentRunStatus;
  /** Snapshot of the Agent when the Run was created. */
  agent: { id: string; name: string; handle: string; harness: TAgentHarness };
  requester_id: string;
  trigger_comment_id: string;
  conclusion_comment_id: string | null;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  last_progress_at: string | null;
  failure_code: string;
  failure_message: string;
  provider: string;
  repository_full_name: string;
  /** Working folder of the Run on the Worker machine; empty until the clone is done. */
  clone_path: string;
  /** Model snapshot; empty means the Harness default. */
  model: string;
  event_count: number;
  sandbox: "read_only";
};

export type TAgentRunEventKind =
  | "message"
  | "thought"
  | "tool_call"
  | "tool_result"
  | "plan"
  | "question"
  | "error"
  | "status"
  | "conclusion";

type TAgentRunEventBase = {
  id: string;
  /** Order of the event in its Run, assigned by Plane from 1. */
  seq: number;
  turn_index: number | null;
  created_at: string;
};

/** A Run timeline event. Payloads come from the Worker; read every field defensively. */
export type TAgentRunEvent = TAgentRunEventBase &
  (
    | {
        kind: "message";
        payload: { role: "user" | "assistant"; text: string; comment_id?: string; author_id?: string };
      }
    | { kind: "thought"; payload: { text: string } }
    | { kind: "tool_call"; payload: { call_id: string; name: string; input: unknown } }
    | {
        kind: "tool_result";
        /** Long output arrives in `parts` events; `part` is 0-based. */
        payload: { call_id: string; part: number; parts: number; text: string; is_error: boolean };
      }
    | { kind: "status"; payload: { code: string; text: string } }
    | { kind: "error"; payload: { code: string; message: string } }
    | { kind: "conclusion"; payload: { text: string; comment_id: string | null; status: string } }
    | { kind: "plan" | "question"; payload: Record<string, unknown> }
  );

/** One page of `GET .../agent-runs/<id>/events/?after=<seq>`. */
export type TAgentRunEventsPage = {
  events: TAgentRunEvent[];
  /** Seq of the last event in the page, or the requested `after` when the page is empty. */
  next_after: number;
  has_more: boolean;
};

/** Why an Agent cannot be mentioned now. Empty when it can. */
export type TAgentMentionDisabledReason = "" | "not_connected" | "not_mentionable" | "no_repository";

/** An Agent in the `agent_mention` entity search. Unavailable Agents are listed with `disabled: true`. */
export type TAgentMentionSearchResponse = {
  id: string;
  name: string;
  handle: string;
  harness: TAgentHarness;
  disabled: boolean;
  disabled_reason: TAgentMentionDisabledReason;
};

/** 400 body of a comment create that mentions an Agent that cannot start a Run. Nothing was saved. */
export type TAgentUnavailableError = {
  error: "agent_unavailable";
  agent: string;
  reason: "not_connected" | "not_mentionable" | "not_found";
};
