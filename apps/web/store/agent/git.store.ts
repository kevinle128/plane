/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, makeObservable, observable, runInAction } from "mobx";
import type {
  TAgentGitAccount,
  TAgentGitAccountRemoval,
  TAgentGitConnection,
  TAgentGitDisconnectResult,
  TAgentGitProvider,
  TAgentGithubDeviceAuthorization,
  TAgentGithubDeviceAuthorizationKind,
} from "@plane/types";
import { AgentGitService } from "@/services/agent/git.service";

export interface IAgentGitStore {
  /** Connections keyed by workspace slug, then provider. `undefined` until fetched. */
  connectionsByWorkspace: Record<string, Partial<Record<TAgentGitProvider, TAgentGitConnection>>>;
  /** Accounts keyed by workspace slug, then provider. */
  accountsByWorkspace: Record<string, Partial<Record<TAgentGitProvider, TAgentGitAccount[]>>>;
  getAccounts: (workspaceSlug: string, provider: TAgentGitProvider) => TAgentGitAccount[] | undefined;
  fetchAccounts: (workspaceSlug: string, provider: TAgentGitProvider) => Promise<TAgentGitAccount[]>;
  syncGithubAccounts: (workspaceSlug: string) => Promise<TAgentGitAccount[]>;
  attachAccount: (workspaceSlug: string, provider: TAgentGitProvider, accountId: string) => Promise<TAgentGitAccount>;
  removeAccount: (
    workspaceSlug: string,
    provider: TAgentGitProvider,
    accountId: string
  ) => Promise<TAgentGitAccountRemoval>;
  disconnect: (workspaceSlug: string, provider: TAgentGitProvider) => Promise<TAgentGitDisconnectResult>;
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
  accountsByWorkspace: Record<string, Partial<Record<TAgentGitProvider, TAgentGitAccount[]>>> = {};
  service: AgentGitService;

  constructor() {
    makeObservable(this, {
      connectionsByWorkspace: observable,
      accountsByWorkspace: observable,
      fetchConnections: action,
      disconnect: action,
      fetchAccounts: action,
      syncGithubAccounts: action,
      attachAccount: action,
      removeAccount: action,
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

  disconnect = async (workspaceSlug: string, provider: TAgentGitProvider) => {
    const result = await this.service.disconnect(workspaceSlug, provider);
    runInAction(() => {
      const { revoke_in_provider: _revoke, ...connection } = result;
      this.connectionsByWorkspace[workspaceSlug] = {
        ...this.connectionsByWorkspace[workspaceSlug],
        [provider]: connection,
      };
    });
    return result;
  };

  getAccounts = (workspaceSlug: string, provider: TAgentGitProvider) =>
    this.accountsByWorkspace[workspaceSlug]?.[provider];

  private setAccounts(workspaceSlug: string, provider: TAgentGitProvider, accounts: TAgentGitAccount[]) {
    runInAction(() => {
      this.accountsByWorkspace[workspaceSlug] = { ...this.accountsByWorkspace[workspaceSlug], [provider]: accounts };
    });
  }

  fetchAccounts = async (workspaceSlug: string, provider: TAgentGitProvider) => {
    const accounts = await this.service.listAccounts(workspaceSlug, provider);
    this.setAccounts(workspaceSlug, provider, accounts);
    return accounts;
  };

  syncGithubAccounts = async (workspaceSlug: string) => {
    const accounts = await this.service.syncGithubAccounts(workspaceSlug);
    this.setAccounts(workspaceSlug, "github", accounts);
    return accounts;
  };

  private replaceAccount(workspaceSlug: string, provider: TAgentGitProvider, account: TAgentGitAccount) {
    const current = this.getAccounts(workspaceSlug, provider) ?? [];
    this.setAccounts(
      workspaceSlug,
      provider,
      current.map((item) => (item.id === account.id ? account : item))
    );
  }

  attachAccount = async (workspaceSlug: string, provider: TAgentGitProvider, accountId: string) => {
    const account = await this.service.attachAccount(workspaceSlug, provider, accountId);
    this.replaceAccount(workspaceSlug, provider, account);
    return account;
  };

  removeAccount = async (workspaceSlug: string, provider: TAgentGitProvider, accountId: string) => {
    const removal = await this.service.removeAccount(workspaceSlug, provider, accountId);
    this.replaceAccount(workspaceSlug, provider, removal);
    return removal;
  };
}
