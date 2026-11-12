/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgentGitProvider } from "@plane/types";

export type TChangeRequestTerm = "pull_request" | "merge_request";

/** Policy labels that name the change request ("pull request" or "merge request"). */
export const POLICY_LABEL_FIELDS = [
  "title",
  "description",
  "open_as_draft",
  "open_as_draft_hint",
  "mirror_conclusions",
  "mirror_conclusions_hint",
] as const;

export type TPolicyLabelField = (typeof POLICY_LABEL_FIELDS)[number];

const CHANGE_REQUEST_TERMS: Record<TAgentGitProvider, TChangeRequestTerm> = {
  github: "pull_request",
  gitlab: "merge_request",
};

/** GitHub says "pull request"; GitLab says "merge request". */
export function getChangeRequestTerm(provider: TAgentGitProvider): TChangeRequestTerm {
  return CHANGE_REQUEST_TERMS[provider];
}

/** i18n key of a policy label in the terms of the provider. */
export function getPolicyLabelKey(field: TPolicyLabelField, provider: TAgentGitProvider): string {
  return `agent_git.policy.${field}.${getChangeRequestTerm(provider)}`;
}
