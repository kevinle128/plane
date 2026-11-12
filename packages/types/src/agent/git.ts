/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TAgentGitProvider = "github" | "gitlab";

export type TAgentGitConnectionStatus = "connected" | "disconnected" | "reconnect_required";

export type TAgentGitUserLite = {
  id: string;
  display_name: string;
  first_name: string;
  last_name: string;
  avatar_url?: string | null;
};

/** A workspace Git provider connection. The API never returns tokens. */
export type TAgentGitConnection = {
  id: string;
  provider: TAgentGitProvider;
  base_url: string;
  host: string;
  status: TAgentGitConnectionStatus;
  last_error: string;
  warnings: string[];
  account_external_id: string;
  account_login: string;
  account_is_bot: boolean | null;
  token_name: string;
  token_scopes: string[];
  token_expires_at: string | null;
  server_version: string;
  connected_by: string | null;
  connected_by_detail: TAgentGitUserLite | null;
  connected_at: string | null;
  worker_last_error: string;
  worker_checked_at: string | null;
  has_ca_bundle: boolean;
  /** GitHub App installation URL; empty for GitLab or when the App slug is not configured. */
  install_url: string;
  updated_at: string;
};

export type TAgentGitAccountState = "candidate" | "attached" | "detached";

/** A GitHub installation or a GitLab group. */
export type TAgentGitAccount = {
  id: string;
  provider: TAgentGitProvider;
  external_id: string;
  login: string;
  account_type: string;
  repository_selection: string;
  state: TAgentGitAccountState;
  attached_by: string | null;
  attached_at: string | null;
  removed_at: string | null;
  catalog_refreshed_at: string | null;
  catalog_error: string;
};

/** Result of removing a GitHub installation from Plane. */
export type TAgentGitAccountRemoval = TAgentGitAccount & {
  /** GitHub page where an admin can uninstall the App installation. */
  settings_url: string;
};

/** A repository in the workspace catalog. */
export type TAgentGitRepository = {
  id: string;
  provider: TAgentGitProvider;
  host: string;
  account_id: string;
  account_login: string;
  account_type: string;
  external_id: string;
  full_name: string;
  owner_login: string;
  private: boolean;
  default_branch: string;
  web_url: string;
};

export type TAgentGitRepositoryPage = {
  results: TAgentGitRepository[];
  next_cursor: string | null;
};

export type TAgentGitRepositoryQuery = {
  provider?: TAgentGitProvider;
  search?: string;
  owner?: string;
  cursor?: string;
};

export type TAgentGithubDeviceAuthorizationKind = "user" | "organization";

export type TAgentGithubDeviceAuthorizationStatus = "pending" | "completed" | "cancelled" | "expired" | "denied";

export type TAgentGithubDeviceAuthorization = {
  id: string;
  kind: TAgentGithubDeviceAuthorizationKind;
  status: TAgentGithubDeviceAuthorizationStatus;
  user_code: string;
  verification_uri: string;
  expires_at: string;
  interval: number;
  last_error: string;
};

/** Error body of the agent Git endpoints. `error` is a stable reason code. */
export type TAgentGitError = {
  error: string;
  provider?: TAgentGitProvider | "";
  detail?: string;
};
