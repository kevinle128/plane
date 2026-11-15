/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
import { reconcileRunEvents } from "@plane/blocks/agent-run";
import type { TAgentRun, TAgentRunEvent } from "@plane/types";
import { AgentRunService } from "@/services/agent/run.service";

/** Upper bound of event pages read in one fetch, so a server that always reports more cannot loop forever. */
const MAX_EVENT_PAGES_PER_FETCH = 50;

export type TOpenAgentRun = { issueId: string; runId: string };

export interface IAgentRunStore {
  /** Run IDs of each work item in `created_at` order. `undefined` until fetched. */
  runIdsByIssue: Record<string, string[]>;
  runMap: Record<string, TAgentRun>;
  /** Loaded timeline events of each Run, in seq order. Kept after the panel closes, so a reopen shows them at once. */
  eventsByRun: Record<string, TAgentRunEvent[]>;
  /** The Run shown in the Run panel, or `null` when the panel is closed. */
  openRun: TOpenAgentRun | null;
  getRunsByIssueId: (issueId: string) => TAgentRun[] | undefined;
  getRunById: (runId: string) => TAgentRun | undefined;
  fetchRuns: (workspaceSlug: string, projectId: string, issueId: string) => Promise<TAgentRun[]>;
  fetchRun: (workspaceSlug: string, projectId: string, issueId: string, runId: string) => Promise<TAgentRun>;
  /** Reads every event after the last loaded one, page by page, and merges them by event ID. */
  fetchRunEvents: (workspaceSlug: string, projectId: string, issueId: string, runId: string) => Promise<void>;
  openPanel: (issueId: string, runId: string) => void;
  closePanel: () => void;
}

export class AgentRunStore implements IAgentRunStore {
  runIdsByIssue: Record<string, string[]> = {};
  runMap: Record<string, TAgentRun> = {};
  eventsByRun: Record<string, TAgentRunEvent[]> = {};
  openRun: TOpenAgentRun | null = null;
  /** Seq after which the next events page starts, per Run. */
  private cursorByRun: Record<string, number> = {};
  service: AgentRunService;

  constructor() {
    makeObservable<AgentRunStore>(this, {
      runIdsByIssue: observable,
      runMap: observable,
      eventsByRun: observable.shallow,
      openRun: observable.ref,
      fetchRuns: action,
      fetchRun: action,
      fetchRunEvents: action,
      openPanel: action,
      closePanel: action,
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

  fetchRun = async (workspaceSlug: string, projectId: string, issueId: string, runId: string) => {
    const run = await this.service.retrieve(workspaceSlug, projectId, issueId, runId);
    runInAction(() => {
      this.runMap[run.id] = run;
    });
    return run;
  };

  fetchRunEvents = async (workspaceSlug: string, projectId: string, issueId: string, runId: string) => {
    for (let page = 0; page < MAX_EVENT_PAGES_PER_FETCH; page++) {
      const after = this.cursorByRun[runId] ?? 0;
      // Pages are read one by one: each page starts after the last event of the previous one.
      // oxlint-disable-next-line no-await-in-loop
      const response = await this.service.listEvents(workspaceSlug, projectId, issueId, runId, after);
      runInAction(() => {
        const current = this.eventsByRun[runId] ?? [];
        const merged = reconcileRunEvents(current, response.events);
        if (merged !== current || !this.eventsByRun[runId]) this.eventsByRun[runId] = merged;
        this.cursorByRun[runId] = Math.max(after, response.next_after);
      });
      // Stop at the end, and when the cursor does not move, so a bad page cannot repeat forever.
      if (!response.has_more || response.next_after <= after) return;
    }
  };

  openPanel = (issueId: string, runId: string) => {
    this.openRun = { issueId, runId };
  };

  closePanel = () => {
    this.openRun = null;
  };
}
