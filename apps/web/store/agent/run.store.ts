/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
import type { TAgentRun } from "@plane/types";
import { AgentRunService } from "@/services/agent/run.service";

export interface IAgentRunStore {
  /** Run IDs of each work item in `created_at` order. `undefined` until fetched. */
  runIdsByIssue: Record<string, string[]>;
  runMap: Record<string, TAgentRun>;
  getRunsByIssueId: (issueId: string) => TAgentRun[] | undefined;
  getRunById: (runId: string) => TAgentRun | undefined;
  fetchRuns: (workspaceSlug: string, projectId: string, issueId: string) => Promise<TAgentRun[]>;
}

export class AgentRunStore implements IAgentRunStore {
  runIdsByIssue: Record<string, string[]> = {};
  runMap: Record<string, TAgentRun> = {};
  service: AgentRunService;

  constructor() {
    makeObservable(this, {
      runIdsByIssue: observable,
      runMap: observable,
      fetchRuns: action,
    });
    this.service = new AgentRunService();
  }

  getRunsByIssueId = computedFn((issueId: string) => {
    const ids = this.runIdsByIssue[issueId];
    if (!ids) return undefined;
    return ids.map((id) => this.runMap[id]).filter((run): run is TAgentRun => !!run);
  });

  getRunById = (runId: string) => this.runMap[runId];

  fetchRuns = async (workspaceSlug: string, projectId: string, issueId: string) => {
    const runs = await this.service.list(workspaceSlug, projectId, issueId);
    runInAction(() => {
      for (const run of runs) this.runMap[run.id] = run;
      this.runIdsByIssue[issueId] = runs.map((run) => run.id);
    });
    return runs;
  };
}
