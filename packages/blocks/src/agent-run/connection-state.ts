/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgentConnection, TAgentConnectionState, TAgentModel } from "@plane/types";

export type THarnessConnectionTone = "success" | "tertiary" | "danger" | "accent";

export type THarnessConnectionAction = "connect" | "retry" | "disconnect";

const TAGS: Record<TAgentConnectionState, { labelKey: string; tone: THarnessConnectionTone }> = {
  not_connected: { labelKey: "agent_settings.status.not_connected", tone: "tertiary" },
  connecting: { labelKey: "agent_settings.status.connecting", tone: "accent" },
  connected: { labelKey: "agent_settings.status.connected", tone: "success" },
  failed: { labelKey: "agent_settings.status.failed", tone: "danger" },
};

const ACTIONS: Record<TAgentConnectionState, THarnessConnectionAction | null> = {
  not_connected: "connect",
  connecting: null,
  connected: "disconnect",
  failed: "retry",
};

/** Missing-action codes with their own message. Other codes show the generic message. */
const KNOWN_MISSING_ACTIONS = new Set([
  "worker_did_not_answer",
  "harness_not_found",
  "unsupported_version",
  "authentication",
  "model_report",
  "follow_up",
  "progress",
  "interruption",
  "permission",
  "recovery",
]);

/** Tag label key and semantic tone of a connection state; the tag is derived from live state, never stored copy. */
export function getHarnessConnectionTag(state: TAgentConnectionState) {
  return TAGS[state];
}

/** The one connection action an admin can take in this state. */
export function getHarnessConnectionAction(state: TAgentConnectionState): THarnessConnectionAction | null {
  return ACTIONS[state];
}

/** A running probe; the page polls until the state changes (Plane fails it after 120 s without a report). */
export function isConnectionPending(state: TAgentConnectionState): boolean {
  return state === "connecting";
}

/** The model selector shows only for a connected Harness that reported models; no model is shown as verified otherwise. */
export function canSelectModel(connection: TAgentConnection | undefined): boolean {
  return connection?.state === "connected" && connection.models.length > 0;
}

/** Translation key of the note on a model that the Harness did not report (the static fallback list), or `null`. */
export function getModelSourceNoteKey(model: TAgentModel): string | null {
  return model.source === "fallback" ? "agent_settings.model.not_reported" : null;
}

/** Translation key of the action that fixes a failed connection, or `null` when nothing is missing. */
export function getMissingActionKey(code: string): string | null {
  if (!code) return null;
  return `agent_settings.missing_action.${KNOWN_MISSING_ACTIONS.has(code) ? code : "generic"}`;
}
