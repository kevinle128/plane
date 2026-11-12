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
  TAgentGitProvider,
  TAgentGitRepositoryPage,
  TAgentGitRepositoryQuery,
  TAgentGithubDeviceAuthorization,
  TAgentGithubDeviceAuthorizationKind,
} from "@plane/types";
import { APIService } from "@/services/api.service";

/** Workspace Git provider endpoints (`api/workspaces/<slug>/agent-git/`). Errors reject with the API error body. */
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
        throw error?.response?.data;
      });
  }

  async startGithubDeviceAuthorization(
    workspaceSlug: string,
    kind: TAgentGithubDeviceAuthorizationKind
  ): Promise<TAgentGithubDeviceAuthorization> {
    return this.post(`${this.base(workspaceSlug)}/github/device-authorizations/`, { kind })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async pollGithubDeviceAuthorization(
    workspaceSlug: string,
    authorizationId: string
  ): Promise<TAgentGithubDeviceAuthorization> {
    return this.post(`${this.base(workspaceSlug)}/github/device-authorizations/${authorizationId}/poll/`, {})
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async cancelGithubDeviceAuthorization(
    workspaceSlug: string,
    authorizationId: string
  ): Promise<TAgentGithubDeviceAuthorization> {
    return this.post(`${this.base(workspaceSlug)}/github/device-authorizations/${authorizationId}/cancel/`, {})
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async listAccounts(workspaceSlug: string, provider: TAgentGitProvider): Promise<TAgentGitAccount[]> {
    return this.get(`${this.base(workspaceSlug)}/${provider}/accounts/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async syncGithubAccounts(workspaceSlug: string): Promise<TAgentGitAccount[]> {
    return this.post(`${this.base(workspaceSlug)}/github/accounts/sync/`, {})
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
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
        throw error?.response?.data;
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
        throw error?.response?.data;
      });
  }

  async listRepositories(
    workspaceSlug: string,
    query: TAgentGitRepositoryQuery = {}
  ): Promise<TAgentGitRepositoryPage> {
    return this.get(`${this.base(workspaceSlug)}/repositories/`, { params: query })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
