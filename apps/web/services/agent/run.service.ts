/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { TAgentRun, TAgentRunEventsPage } from "@plane/types";
import { APIService } from "@/services/api.service";

/** Largest events page the API returns. */
const EVENTS_PAGE_LIMIT = 200;

/** Run endpoints of a work item (`.../issues/<id>/agent-runs/`). Errors reject with the API error body. */
export class AgentRunService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private base(workspaceSlug: string, projectId: string, issueId: string): string {
    return `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/agent-runs`;
  }

  async list(workspaceSlug: string, projectId: string, issueId: string): Promise<TAgentRun[]> {
    return this.get(`${this.base(workspaceSlug, projectId, issueId)}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async retrieve(workspaceSlug: string, projectId: string, issueId: string, runId: string): Promise<TAgentRun> {
    return this.get(`${this.base(workspaceSlug, projectId, issueId)}/${runId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** Events with `seq` greater than `after`, in seq order. */
  async listEvents(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    runId: string,
    after: number
  ): Promise<TAgentRunEventsPage> {
    return this.get(`${this.base(workspaceSlug, projectId, issueId)}/${runId}/events/`, {
      after,
      limit: EVENTS_PAGE_LIMIT,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
