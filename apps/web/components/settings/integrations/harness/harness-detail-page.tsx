/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
import { Button } from "@makeplane/propel/components/button";
import { AgentOutline, ArrowNarrowLeftOutline } from "@makeplane/propel/icons";
import { isConnectionPending } from "@plane/blocks/agent-run";
import { AGENT_CONNECTION_POLL_MS, AGENT_HARNESSES, AGENT_HARNESS_LABELS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TAgent, TAgentHarness } from "@plane/types";
import { cn } from "@plane/utils";
import { SettingsHeading } from "@/components/settings/heading";
import { useAgent } from "@/hooks/store/use-agent";
import { HarnessConnectionRow, HarnessStatusTag } from "./connection-row";
import { agentsKey, harnessCliLabel } from "./harness-card";

type Props = {
  workspaceSlug: string;
  harness: TAgentHarness;
  canEdit: boolean;
};

/** Poll while any probe runs, so the page and the selector tags follow the live state. */
const pollWhilePending = (agents: TAgent[] | undefined) =>
  agents?.some((agent) => isConnectionPending(agent.connection.state)) ? AGENT_CONNECTION_POLL_MS : 0;

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

function AgentSelector({ workspaceSlug, current }: { workspaceSlug: string; current: TAgentHarness }) {
  const { t } = useTranslation();
  const { getAgent } = useAgent();
  return (
    <nav aria-label={t("agent_settings.detail.selector_label")} className="w-full shrink-0 md:w-56">
      <ul className="flex flex-col gap-1.5">
        {AGENT_HARNESSES.map((harness) => {
          const agent = getAgent(workspaceSlug, harness);
          const isCurrent = harness === current;
          return (
            <li key={harness}>
              <Link
                href={`/${workspaceSlug}/settings/integrations/${harness}`}
                aria-current={isCurrent ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg border px-3 py-2.5 focus-visible:outline-2 focus-visible:outline-accent-strong",
                  isCurrent
                    ? "border-accent-strong bg-layer-1-selected"
                    : "border-subtle bg-surface-1 hover:border-strong"
                )}
              >
                <span className="grid size-8 shrink-0 place-items-center rounded-full bg-accent-subtle text-accent-primary">
                  <AgentOutline className="size-4" aria-hidden="true" />
                </span>
                <span className="flex min-w-0 flex-col">
                  <span className="truncate text-body-sm-semibold text-primary">
                    {agent?.name ?? AGENT_HARNESS_LABELS[harness]}
                  </span>
                  {agent && (
                    <span className="truncate font-code text-caption-sm-regular text-tertiary">@{agent.handle}</span>
                  )}
                </span>
                {agent && <HarnessStatusTag state={agent.connection.state} className="ml-auto shrink-0" />}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/** Harness detail page: Agent selector with live tags, and the settings of the selected Agent. */
export const HarnessDetailPage = observer(function HarnessDetailPage({ workspaceSlug, harness, canEdit }: Props) {
  const { t } = useTranslation();
  const { fetchAgents, getAgent } = useAgent();
  const { error, isLoading, mutate } = useSWR(agentsKey(workspaceSlug), () => fetchAgents(workspaceSlug), {
    refreshInterval: pollWhilePending,
  });
  const agent = getAgent(workspaceSlug, harness);
  const version = agent?.connection.harness_version ?? "";

  return (
    <div className="flex w-full flex-col gap-6">
      <Link
        href={`/${workspaceSlug}/settings/integrations`}
        className="flex w-fit items-center gap-1 text-caption-sm-regular text-tertiary hover:text-secondary"
      >
        <ArrowNarrowLeftOutline className="size-3.5" aria-hidden="true" />
        {t("agent_git.integrations.back")}
      </Link>
      <SettingsHeading title={AGENT_HARNESS_LABELS[harness]} description={t("agent_settings.detail.description")} />
      {!!error && !isLoading && <AgentsLoadError onRetry={() => void mutate()} />}
      {agent && (
        <div className="flex flex-col gap-4 md:flex-row md:items-start">
          <AgentSelector workspaceSlug={workspaceSlug} current={harness} />
          <section
            aria-labelledby="agent-settings-title"
            className="min-w-0 flex-1 rounded-lg border border-subtle bg-surface-1 shadow-raised-100"
          >
            <div className="flex items-center gap-3 border-b border-subtle px-4 py-3">
              <span className="grid size-8 shrink-0 place-items-center rounded-full bg-accent-subtle text-accent-primary">
                <AgentOutline className="size-4" aria-hidden="true" />
              </span>
              <div className="flex min-w-0 flex-col">
                <h4 id="agent-settings-title" className="truncate text-body-md-semibold text-primary">
                  {agent.name}
                </h4>
                <span className="truncate text-caption-sm-regular text-tertiary">
                  {agent.connection.state === "connected"
                    ? t("agent_settings.detail.on_the_mini", { version: harnessCliLabel(harness, version) })
                    : harnessCliLabel(harness, "")}
                </span>
              </div>
            </div>
            {!canEdit && (
              <p className="border-b border-subtle px-4 py-2 text-caption-sm-regular text-tertiary">
                {t("agent_settings.detail.read_only")}
              </p>
            )}
            <ul>
              <HarnessConnectionRow workspaceSlug={workspaceSlug} agent={agent} canEdit={canEdit} />
            </ul>
          </section>
        </div>
      )}
    </div>
  );
});
