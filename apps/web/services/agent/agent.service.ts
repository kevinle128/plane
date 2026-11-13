/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { TAgent, TAgentHarness, TAgentSettingsError } from "@plane/types";
import { APIService } from "@/services/api.service";

/** API error body with the HTTP status; a body that is not JSON gives an empty error. */
function toAgentSettingsError(error: unknown): TAgentSettingsError {
  const response = (error as { response?: { status?: number; data?: unknown } } | null)?.response;
  const data = response?.data;
  const body = data && typeof data === "object" ? (data as TAgentSettingsError) : {};
  return { ...body, status: response?.status };
}

/** Workspace Agent endpoints (`api/workspaces/<slug>/agents/`). Errors reject with the API error body and status. */
export class AgentService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private base(workspaceSlug: string): string {
    return `/api/workspaces/${workspaceSlug}/agents`;
  }

  async list(workspaceSlug: string): Promise<TAgent[]> {
    return this.get(`${this.base(workspaceSlug)}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentSettingsError(error);
      });
  }

  async retrieve(workspaceSlug: string, harness: TAgentHarness): Promise<TAgent> {
    return this.get(`${this.base(workspaceSlug)}/${harness}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentSettingsError(error);
      });
  }

  async connect(workspaceSlug: string, harness: TAgentHarness): Promise<TAgent> {
    return this.post(`${this.base(workspaceSlug)}/${harness}/connect/`, {})
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentSettingsError(error);
      });
  }

  async disconnect(workspaceSlug: string, harness: TAgentHarness): Promise<TAgent> {
    return this.post(`${this.base(workspaceSlug)}/${harness}/disconnect/`, {})
      .then((response) => response?.data)
      .catch((error) => {
        throw toAgentSettingsError(error);
      });
  }
}
