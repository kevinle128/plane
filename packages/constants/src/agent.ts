/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgentGitConnectionStatus, TAgentGitPolicy, TAgentGitProvider } from "@plane/types";

export const AGENT_GIT_PROVIDERS: TAgentGitProvider[] = ["github", "gitlab"];

/** Provider names are brand names and are not translated. */
export const AGENT_GIT_PROVIDER_LABELS: Record<TAgentGitProvider, string> = {
  github: "GitHub",
  gitlab: "GitLab",
};

export const AGENT_GIT_CONNECTION_STATUS_I18N: Record<TAgentGitConnectionStatus, string> = {
  connected: "agent_git.status.connected",
  disconnected: "agent_git.status.not_connected",
  reconnect_required: "agent_git.status.reconnect_required",
};

/** Agent branch formats. The labels are Git patterns and are not translated. */
export const AGENT_GIT_BRANCH_FORMATS: { key: TAgentGitPolicy["branch_format"]; label: string }[] = [
  { key: "issue", label: "agent/<issue-identifier>-<run-short-id>" },
  { key: "project_issue", label: "agent/<project-identifier>/<issue-identifier>-<run-short-id>" },
];
