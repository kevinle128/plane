/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** The four local CLI Harnesses. Each workspace has one Agent per Harness. */
export type TAgentHarness = "claude_code" | "codex" | "omp";

/** Connection state as Plane shows it. A probe without a report after 120 s reads as `failed`. */
export type TAgentConnectionState = "not_connected" | "connecting" | "connected" | "failed";

/**
 * Where a model entry comes from: the Harness reported it, or the Worker used its static list of CLI
 * aliases because the model list request failed at Connect.
 */
export type TAgentModelSource = "reported" | "fallback";

/** A model of the connected Harness. Only models in the connection report can be selected. */
export type TAgentModel = {
  id: string;
  label: string;
  description: string;
  source: TAgentModelSource;
};

export type TAgentConnectionCheck = {
  name: string;
  passed: boolean;
  detail: string;
};

export type TAgentConnection = {
  state: TAgentConnectionState;
  probe_generation: number;
  probe_requested_at: string | null;
  harness_version: string;
  location: string;
  models: TAgentModel[];
  capabilities: Partial<Record<"midturn_input" | "native_resume" | "permission_prompt", boolean>>;
  checks: TAgentConnectionCheck[];
  /** Code of the action that makes the connection work, for example `authentication`. Empty when connected. */
  missing_action: string;
  /** Detail from the Harness, for example its exit message. Shown as is, in a code box. */
  failure_hint: string;
  verified_at: string | null;
};

/** A workspace Agent: the mentionable identity of one Harness. */
export type TAgent = {
  id: string;
  harness: TAgentHarness;
  name: string;
  handle: string;
  instructions: string;
  mentionable: boolean;
  selected_model: string;
  /** True when a new Run can start from a mention: the Agent is mentionable and its Harness is connected. */
  available_for_mentions: boolean;
  connection: TAgentConnection;
};

/** Settings an admin can change on an Agent. */
export type TAgentSettingsField = "name" | "handle" | "instructions" | "mentionable" | "selected_model";

export type TAgentUpdate = Partial<Pick<TAgent, TAgentSettingsField>>;

/**
 * API error body of the Agent settings endpoints. Field errors are lists of messages; `codes` has the
 * first error code of each field, so the web app can show a translated message.
 */
export type TAgentSettingsError = {
  error?: string;
  status?: number;
  codes?: Partial<Record<TAgentSettingsField, string>>;
} & Partial<Record<TAgentSettingsField, string[]>>;
