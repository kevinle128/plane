/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgentGitConnectionStatus, TAgentGitPolicy, TAgentGitProvider, TAgentHarness } from "@plane/types";

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

/** Harness order on the Integrations page and in the Agent selector. */
export const AGENT_HARNESSES: TAgentHarness[] = ["claude_code", "codex", "grok", "omp"];

/** Harness names are product names and are not translated. */
export const AGENT_HARNESS_LABELS: Record<TAgentHarness, string> = {
  claude_code: "Claude Code",
  codex: "Codex CLI",
  grok: "Grok CLI",
  omp: "Omp",
};

/** The CLI command of each Harness, shown when no version is known yet. */
export const AGENT_HARNESS_COMMANDS: Record<TAgentHarness, string> = {
  claude_code: "claude",
  codex: "codex",
  grok: "grok",
  omp: "omp",
};

/** Harnesses whose connection probe the Worker can run. The others can be configured but not connected yet. */
export const AGENT_PROBE_HARNESSES: TAgentHarness[] = ["claude_code"];

/** Poll interval of the Harness detail page while a probe runs. */
export const AGENT_CONNECTION_POLL_MS = 2000;
