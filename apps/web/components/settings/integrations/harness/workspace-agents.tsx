/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
import { Button } from "@makeplane/propel/components/button";
import { getAgentPollInterval } from "@plane/blocks/agent-run";
import { AGENT_CONNECTION_POLL_MS, AGENT_HARNESSES } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { useAgent } from "@/hooks/store/use-agent";

/** SWR key of the Agents of a workspace. */
export const agentsKey = (workspaceSlug: string) => `AGENTS_${workspaceSlug}`;

/**
 * Fetches the Agents of a workspace into the store, and polls while a probe runs. Call it only in an
 * observer component: the poll interval comes from the store, so Connect starts the poll at once.
 * SWR starts or stops its poll timer only when the interval number changes.
 */
export function useWorkspaceAgents(workspaceSlug: string) {
  const { fetchAgents, getAgent } = useAgent();
  const refreshInterval = getAgentPollInterval(AGENT_HARNESSES.map((harness) => getAgent(workspaceSlug, harness)));
  return useSWR(agentsKey(workspaceSlug), () => fetchAgents(workspaceSlug), {
    refreshInterval,
    // Shorter than the poll period, so SWR does not skip a poll as a duplicate request.
    dedupingInterval: AGENT_CONNECTION_POLL_MS / 2,
  });
}

export function AgentsLoadError({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-2 rounded-md bg-danger-subtle px-3 py-2 text-body-sm-regular text-danger-primary"
    >
      <span className="flex-1">{t("agent_settings.integrations.load_error")}</span>
      <Button variant="secondary" size="sm" stretch="auto" label={t("common.retry")} onClick={onRetry} />
    </div>
  );
}
