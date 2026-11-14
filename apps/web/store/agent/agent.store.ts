/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, makeObservable, observable, runInAction } from "mobx";
import { agentsByHarness, withAgent, type TAgentsByHarness } from "@plane/blocks/agent-run";
import type { TAgent, TAgentHarness, TAgentUpdate } from "@plane/types";
import { AgentService } from "@/services/agent/agent.service";

export interface IAgentStore {
  /** Agents keyed by workspace slug, then Harness. `undefined` until fetched. */
  agentsByWorkspace: Record<string, TAgentsByHarness>;
  getAgent: (workspaceSlug: string, harness: TAgentHarness) => TAgent | undefined;
  getAgentById: (workspaceSlug: string, agentId: string) => TAgent | undefined;
  fetchAgents: (workspaceSlug: string) => Promise<TAgent[]>;
  /**
   * Fetches the Agents of a workspace unless they are loaded or a fetch was already made. A failed fetch
   * (for example a guest, who cannot list Agents) is not repeated until the page reloads.
   */
  fetchAgentsOnce: (workspaceSlug: string) => Promise<void>;
  updateAgent: (workspaceSlug: string, harness: TAgentHarness, data: TAgentUpdate) => Promise<TAgent>;
  connect: (workspaceSlug: string, harness: TAgentHarness) => Promise<TAgent>;
  disconnect: (workspaceSlug: string, harness: TAgentHarness) => Promise<TAgent>;
}

export class AgentStore implements IAgentStore {
  agentsByWorkspace: Record<string, TAgentsByHarness> = {};
  service: AgentService;
  private pendingFetches = new Map<string, Promise<void>>();

  constructor() {
    makeObservable(this, {
      agentsByWorkspace: observable,
      fetchAgents: action,
      updateAgent: action,
      connect: action,
      disconnect: action,
    });
    this.service = new AgentService();
  }

  getAgent = (workspaceSlug: string, harness: TAgentHarness) => this.agentsByWorkspace[workspaceSlug]?.[harness];

  getAgentById = (workspaceSlug: string, agentId: string) =>
    Object.values(this.agentsByWorkspace[workspaceSlug] ?? {}).find((agent) => agent?.id === agentId);

  private setAgent(workspaceSlug: string, agent: TAgent) {
    runInAction(() => {
      this.agentsByWorkspace[workspaceSlug] = withAgent(this.agentsByWorkspace[workspaceSlug], agent);
    });
  }

  fetchAgents = async (workspaceSlug: string) => {
    const agents = await this.service.list(workspaceSlug);
    runInAction(() => {
      this.agentsByWorkspace[workspaceSlug] = agentsByHarness(agents);
    });
    return agents;
  };

  fetchAgentsOnce = (workspaceSlug: string) => {
    if (this.agentsByWorkspace[workspaceSlug]) return Promise.resolve();
    const pending = this.pendingFetches.get(workspaceSlug);
    if (pending) return pending;
    const request = (async () => {
      await this.fetchAgents(workspaceSlug);
      this.pendingFetches.delete(workspaceSlug);
    })();
    this.pendingFetches.set(workspaceSlug, request);
    return request;
  };

  updateAgent = async (workspaceSlug: string, harness: TAgentHarness, data: TAgentUpdate) => {
    const agent = await this.service.update(workspaceSlug, harness, data);
    this.setAgent(workspaceSlug, agent);
    return agent;
  };

  connect = async (workspaceSlug: string, harness: TAgentHarness) => {
    const agent = await this.service.connect(workspaceSlug, harness);
    this.setAgent(workspaceSlug, agent);
    return agent;
  };

  disconnect = async (workspaceSlug: string, harness: TAgentHarness) => {
    const agent = await this.service.disconnect(workspaceSlug, harness);
    this.setAgent(workspaceSlug, agent);
    return agent;
  };
}
