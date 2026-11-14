/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgent, TAgentUpdate } from "@plane/types";

/** Agent settings that the form edits and sends with one Save. */
export type TAgentSettingsDraft = Pick<TAgent, "name" | "handle" | "instructions" | "selected_model">;

/**
 * Form state. `baseline` has the server values that the draft started from or last took; a field is
 * changed only when its draft value is different from its baseline value.
 */
export type TAgentSettingsForm = { draft: TAgentSettingsDraft; baseline: TAgentSettingsDraft };

const DRAFT_FIELDS = ["name", "handle", "instructions", "selected_model"] as const;

const draftOf = (agent: TAgent): TAgentSettingsDraft => ({
  name: agent.name,
  handle: agent.handle,
  instructions: agent.instructions,
  selected_model: agent.selected_model,
});

/** A form with no user changes, from the server values of the Agent. */
export function agentSettingsFormOf(agent: TAgent): TAgentSettingsForm {
  const values = draftOf(agent);
  return { draft: values, baseline: values };
}

/** The fields that the user changed, so a Save never rewrites a value that another admin changed. */
export function changesOf(form: TAgentSettingsForm): TAgentUpdate {
  const changes: TAgentUpdate = {};
  for (const field of DRAFT_FIELDS) {
    if (form.draft[field] !== form.baseline[field]) changes[field] = form.draft[field];
  }
  return changes;
}

/**
 * Applies new server values to the form. A field that the user did not change takes the server value.
 * A selected model that the Harness does not report now also takes the server value, because the
 * server refuses an unreported model. The baseline always moves to the server values.
 * Gives the same form back when nothing changes.
 */
export function mergeServerAgent(form: TAgentSettingsForm, agent: TAgent): TAgentSettingsForm {
  const server = draftOf(agent);
  const reported = new Set(agent.connection.models.map((model) => model.id));
  const draft = { ...form.draft };
  for (const field of DRAFT_FIELDS) {
    if (form.draft[field] === form.baseline[field]) draft[field] = server[field];
  }
  if (draft.selected_model && !reported.has(draft.selected_model)) draft.selected_model = server.selected_model;

  const isSame = DRAFT_FIELDS.every(
    (field) => draft[field] === form.draft[field] && server[field] === form.baseline[field]
  );
  return isSame ? form : { draft, baseline: server };
}
