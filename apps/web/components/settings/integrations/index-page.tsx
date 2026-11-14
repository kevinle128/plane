/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { AGENT_HARNESSES } from "@plane/constants";
import type { TAgentGitProvider } from "@plane/types";
import { SettingsHeading } from "@/components/settings/heading";
import { useAgent } from "@/hooks/store/use-agent";
import { useAgentGit } from "@/hooks/store/use-agent-git";
import {
  AgentGitConnectionsError,
  AgentGitProviderIcon,
  AgentGitStatusTag,
  agentGitConnectionsKey,
  agentGitProviderLabel,
} from "./git/provider-meta";
import { HarnessCard } from "./harness/harness-card";
import { AgentsLoadError, useWorkspaceAgents } from "./harness/workspace-agents";

type Props = { workspaceSlug: string };

const ESSENTIAL_PROVIDERS: { provider: TAgentGitProvider; blurbKey: string }[] = [
  { provider: "github", blurbKey: "agent_git.integrations.github_blurb" },
  { provider: "gitlab", blurbKey: "agent_git.integrations.gitlab_blurb" },
];

export const IntegrationsIndexPage = observer(function IntegrationsIndexPage({ workspaceSlug }: Props) {
  const { t } = useTranslation();
  const { fetchConnections, getConnection } = useAgentGit();
  const { data, error, isLoading, mutate } = useSWR(agentGitConnectionsKey(workspaceSlug), () =>
    fetchConnections(workspaceSlug)
  );
  const hasLoadError = !!error && !isLoading;
  // Without loaded connections the status is unknown, so the cards show no status or "Connect" label.
  const isStatusKnown = data !== undefined;
  const { getAgent } = useAgent();
  const agents = useWorkspaceAgents(workspaceSlug);
  const hasAgentsError = !!agents.error && !agents.isLoading;

  return (
    <div className="flex w-full flex-col gap-6">
      <SettingsHeading
        title={t("workspace_settings.settings.integrations.title")}
        description={t("agent_git.integrations.description")}
      />
      <section aria-labelledby="agent-git-essentials" className="flex flex-col gap-3">
        <h4 id="agent-git-essentials" className="tracking-wider text-11 font-semibold text-tertiary uppercase">
          {t("agent_git.integrations.essentials")}
        </h4>
        {hasLoadError && <AgentGitConnectionsError onRetry={() => void mutate()} />}
        <div className="flex flex-wrap gap-3">
          {ESSENTIAL_PROVIDERS.map(({ provider, blurbKey }) => {
            const connection = getConnection(workspaceSlug, provider);
            return (
              <Link
                key={provider}
                href={`/${workspaceSlug}/settings/integrations/${provider}`}
                className="flex max-w-65 min-w-48 flex-1 basis-52 flex-col gap-2 rounded-lg border border-subtle bg-surface-1 p-3 hover:border-strong focus-visible:outline-2 focus-visible:outline-accent-strong"
              >
                <span className="flex items-center gap-2">
                  <span className="flex size-7 items-center justify-center rounded-md border border-subtle bg-layer-2">
                    <AgentGitProviderIcon provider={provider} />
                  </span>
                  <span className="flex-1 text-body-sm-semibold text-primary">{agentGitProviderLabel(provider)}</span>
                  {isStatusKnown && connection && <AgentGitStatusTag connection={connection} t={t} />}
                  {isStatusKnown && !connection && (
                    <span className="text-caption-sm-medium text-accent-primary">
                      {t("agent_git.integrations.connect")}
                    </span>
                  )}
                </span>
                <span className="text-caption-sm-regular text-secondary">{t(blurbKey)}</span>
              </Link>
            );
          })}
        </div>
      </section>
      <section aria-labelledby="agent-harnesses" className="flex flex-col gap-3">
        <h4 id="agent-harnesses" className="tracking-wider text-11 font-semibold text-tertiary uppercase">
          {t("agent_settings.integrations.harnesses")}
        </h4>
        {hasAgentsError && <AgentsLoadError onRetry={() => void agents.mutate()} />}
        <div className="flex flex-wrap gap-3">
          {AGENT_HARNESSES.map((harness) => (
            <HarnessCard
              key={harness}
              workspaceSlug={workspaceSlug}
              harness={harness}
              agent={agents.data ? getAgent(workspaceSlug, harness) : undefined}
            />
          ))}
        </div>
      </section>
    </div>
  );
});
