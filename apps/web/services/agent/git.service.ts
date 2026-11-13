/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type {
  TAgentGitAccount,
  TAgentGitAccountRemoval,
  TAgentGitConnection,
  TAgentGitDisconnectResult,
  TAgentGitError,
  TAgentGitPolicy,
  TAgentGitProvider,
  TAgentGitRepositoryPage,
  TAgentGitlabConnectInput,
  TAgentGitRepositoryQuery,
  TAgentGithubDeviceAuthorization,
  TAgentGithubDeviceAuthorizationKind,
} from "@plane/types";
import { APIService } from "@/services/api.service";

/**
 * API error body with the HTTP status. A body that is not JSON (for example an HTML 502 page) gives an
 * empty error code, so the caller shows the generic message.
 */
function toAgentGitError(error: unknown): TAgentGitError {
  const response = (error as { response?: { status?: number; data?: unknown } } | null)?.response;
  const data = response?.data;
  const body = data && typeof data === "object" ? (data as Partial<TAgentGitError>) : {};
  return { ...body, error: typeof body.error === "string" ? body.error : "", status: response?.status };
}

/** Workspace Git provider endpoints (`api/workspaces/<slug>/agent-git/`). Errors reject with the API error body and the HTTP status. */
export class AgentGitService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private base(workspaceSlug: string): string {
    return `/api/workspaces/${workspaceSlug}/agent-git`;
  }

  async listConnections(workspaceSlug: string): Promise<TAgentGitConnection[]> {
    return this.get(`${this.base(workspaceSlug)}/connections/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }

  async startGithubDeviceAuthorization(
    workspaceSlug: string,
    kind: TAgentGithubDeviceAuthorizationKind
  ): Promise<TAgentGithubDeviceAuthorization> {
    return this.post(`${this.base(workspaceSlug)}/github/device-authorizations/`, { kind })
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }

  async pollGithubDeviceAuthorization(
    workspaceSlug: string,
    authorizationId: string
  ): Promise<TAgentGithubDeviceAuthorization> {
    return this.post(`${this.base(workspaceSlug)}/github/device-authorizations/${authorizationId}/poll/`, {})
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }

  async cancelGithubDeviceAuthorization(
    workspaceSlug: string,
    authorizationId: string
  ): Promise<TAgentGithubDeviceAuthorization> {
    return this.post(`${this.base(workspaceSlug)}/github/device-authorizations/${authorizationId}/cancel/`, {})
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }

  async connectGitlab(workspaceSlug: string, data: TAgentGitlabConnectInput): Promise<TAgentGitConnection> {
    return this.post(`${this.base(workspaceSlug)}/gitlab/connection/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }

  async disconnect(workspaceSlug: string, provider: TAgentGitProvider): Promise<TAgentGitDisconnectResult> {
    return this.delete(`${this.base(workspaceSlug)}/${provider}/connection/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }

  async listAccounts(workspaceSlug: string, provider: TAgentGitProvider): Promise<TAgentGitAccount[]> {
    return this.get(`${this.base(workspaceSlug)}/${provider}/accounts/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }

  async syncGithubAccounts(workspaceSlug: string): Promise<TAgentGitAccount[]> {
    return this.post(`${this.base(workspaceSlug)}/github/accounts/sync/`, {})
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }

  async attachAccount(
    workspaceSlug: string,
    provider: TAgentGitProvider,
    accountId: string
  ): Promise<TAgentGitAccount> {
    return this.post(`${this.base(workspaceSlug)}/${provider}/accounts/${accountId}/attach/`, {})
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }

  async removeAccount(
    workspaceSlug: string,
    provider: TAgentGitProvider,
    accountId: string
  ): Promise<TAgentGitAccountRemoval> {
    return this.delete(`${this.base(workspaceSlug)}/${provider}/accounts/${accountId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }

  async listRepositories(
    workspaceSlug: string,
    query: TAgentGitRepositoryQuery = {}
  ): Promise<TAgentGitRepositoryPage> {
    return this.get(`${this.base(workspaceSlug)}/repositories/`, { params: query })
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }

  async getPolicy(workspaceSlug: string, provider: TAgentGitProvider): Promise<TAgentGitPolicy> {
    return this.get(`${this.base(workspaceSlug)}/${provider}/policy/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }

  async updatePolicy(
    workspaceSlug: string,
    provider: TAgentGitProvider,
    data: Partial<Omit<TAgentGitPolicy, "provider">>
  ): Promise<TAgentGitPolicy> {
    return this.patch(`${this.base(workspaceSlug)}/${provider}/policy/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentGitError(error);
      });
  }
}
