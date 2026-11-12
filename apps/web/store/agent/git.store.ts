/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, makeObservable, observable, runInAction } from "mobx";
import type {
  TAgentGitConnection,
  TAgentGitProvider,
  TAgentGithubDeviceAuthorization,
  TAgentGithubDeviceAuthorizationKind,
} from "@plane/types";
import { AgentGitService } from "@/services/agent/git.service";

export interface IAgentGitStore {
  /** Connections keyed by workspace slug, then provider. `undefined` until fetched. */
  connectionsByWorkspace: Record<string, Partial<Record<TAgentGitProvider, TAgentGitConnection>>>;
  getConnection: (workspaceSlug: string, provider: TAgentGitProvider) => TAgentGitConnection | undefined;
  isConnected: (workspaceSlug: string, provider: TAgentGitProvider) => boolean;
  fetchConnections: (workspaceSlug: string) => Promise<TAgentGitConnection[]>;
  startGithubDeviceAuthorization: (
    workspaceSlug: string,
    kind: TAgentGithubDeviceAuthorizationKind
  ) => Promise<TAgentGithubDeviceAuthorization>;
  pollGithubDeviceAuthorization: (
    workspaceSlug: string,
    authorizationId: string
  ) => Promise<TAgentGithubDeviceAuthorization>;
  cancelGithubDeviceAuthorization: (
    workspaceSlug: string,
    authorizationId: string
  ) => Promise<TAgentGithubDeviceAuthorization>;
}

export class AgentGitStore implements IAgentGitStore {
  connectionsByWorkspace: Record<string, Partial<Record<TAgentGitProvider, TAgentGitConnection>>> = {};
  service: AgentGitService;

  constructor() {
    makeObservable(this, {
      connectionsByWorkspace: observable,
      fetchConnections: action,
      pollGithubDeviceAuthorization: action,
    });
    this.service = new AgentGitService();
  }

  getConnection = (workspaceSlug: string, provider: TAgentGitProvider) =>
    this.connectionsByWorkspace[workspaceSlug]?.[provider];

  isConnected = (workspaceSlug: string, provider: TAgentGitProvider) =>
    this.getConnection(workspaceSlug, provider)?.status === "connected";

  fetchConnections = async (workspaceSlug: string) => {
    const connections = await this.service.listConnections(workspaceSlug);
    runInAction(() => {
      const byProvider: Partial<Record<TAgentGitProvider, TAgentGitConnection>> = {};
      for (const connection of connections) byProvider[connection.provider] = connection;
      this.connectionsByWorkspace[workspaceSlug] = byProvider;
    });
    return connections;
  };

  startGithubDeviceAuthorization = (workspaceSlug: string, kind: TAgentGithubDeviceAuthorizationKind) =>
    this.service.startGithubDeviceAuthorization(workspaceSlug, kind);

  pollGithubDeviceAuthorization = async (workspaceSlug: string, authorizationId: string) => {
    const authorization = await this.service.pollGithubDeviceAuthorization(workspaceSlug, authorizationId);
    if (authorization.status === "completed") await this.fetchConnections(workspaceSlug);
    return authorization;
  };

  cancelGithubDeviceAuthorization = (workspaceSlug: string, authorizationId: string) =>
    this.service.cancelGithubDeviceAuthorization(workspaceSlug, authorizationId);
}
