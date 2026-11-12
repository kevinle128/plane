/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { Button } from "@makeplane/propel/components/button";
import { TickOutline } from "@makeplane/propel/icons";
import { getDeniedReasonCode } from "@plane/blocks/agent-run";
import { useTranslation } from "@plane/i18n";
import type { TAgentGithubDeviceAuthorization } from "@plane/types";
import { useAgentGit } from "@/hooks/store/use-agent-git";
import { AgentGitProviderIcon, agentGitErrorMessage } from "../provider-meta";
import type { TDeviceFlowOutcome } from "./device-flow";
import { GithubDeviceFlowCard } from "./device-flow";

type Props = { workspaceSlug: string; canEdit: boolean };

const CHECKLIST = [
  "agent_git.github.setup.check_repositories",
  "agent_git.github.setup.check_bind",
  "agent_git.github.setup.check_pull_requests",
];

const OUTCOME_MESSAGES: Partial<Record<TDeviceFlowOutcome, string>> = {
  expired: "agent_git.github.result.expired",
  denied: "agent_git.github.result.denied",
  cancelled: "agent_git.github.result.cancelled",
};

/** Disconnected GitHub state: explains the integration and starts the device flow. */
export const GithubSetupCard = observer(function GithubSetupCard({ workspaceSlug, canEdit }: Props) {
  const { t } = useTranslation();
  const { startGithubDeviceAuthorization } = useAgentGit();
  const [flow, setFlow] = useState<{ authorization: TAgentGithubDeviceAuthorization; receivedAt: number } | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);

  const handleStart = async () => {
    setIsStarting(true);
    setMessage(null);
    try {
      const authorization = await startGithubDeviceAuthorization(workspaceSlug, "user");
      setFlow({ authorization, receivedAt: Date.now() });
    } catch (error) {
      setMessage(agentGitErrorMessage(t, error));
    } finally {
      setIsStarting(false);
    }
  };

  const handleSettled = useCallback(
    (outcome: TDeviceFlowOutcome, last: TAgentGithubDeviceAuthorization, errorMessage?: string) => {
      setFlow(null);
      if (outcome === "failed") {
        setMessage(errorMessage ?? t("agent_git.errors.generic"));
        return;
      }
      // A denied authorization that the user did not refuse shows the reason, for example wrong App credentials.
      const deniedReason = outcome === "denied" ? getDeniedReasonCode(last.last_error) : null;
      if (deniedReason) {
        setMessage(agentGitErrorMessage(t, { error: deniedReason }));
        return;
      }
      const key = OUTCOME_MESSAGES[outcome];
      setMessage(key ? t(key) : null);
    },
    [t]
  );

  if (flow) {
    return (
      <GithubDeviceFlowCard
        workspaceSlug={workspaceSlug}
        authorization={flow.authorization}
        receivedAt={flow.receivedAt}
        onSettled={handleSettled}
      />
    );
  }

  return (
    <section className="flex flex-col items-center gap-4 rounded-lg border border-subtle bg-surface-1 px-6 py-8 text-center">
      <span className="flex size-8 items-center justify-center rounded-full bg-layer-1">
        <AgentGitProviderIcon provider="github" className="size-5" />
      </span>
      <div className="flex flex-col gap-1">
        <h4 className="text-body-md-semibold text-primary">{t("agent_git.github.setup.title")}</h4>
        <p className="max-w-[620px] text-body-xs-regular text-tertiary">{t("agent_git.github.setup.description")}</p>
      </div>
      <ul className="flex w-full max-w-md flex-col gap-2 rounded-md border border-subtle bg-surface-2 p-3 text-left">
        {CHECKLIST.map((key) => (
          <li key={key} className="flex items-center gap-2 text-caption-sm-regular text-secondary">
            <TickOutline className="size-3.5 shrink-0 text-success-primary" aria-hidden="true" />
            {t(key)}
          </li>
        ))}
      </ul>
      {message && (
        <p role="alert" className="text-caption-sm-regular text-danger-primary">
          {message}
        </p>
      )}
      {canEdit ? (
        <div className="flex flex-col items-center gap-2">
          <Button
            variant="primary"
            size="lg"
            stretch="auto"
            label={t("agent_git.github.setup.authenticate")}
            loading={isStarting}
            onClick={() => void handleStart()}
          />
          <Link
            href={`/${workspaceSlug}/settings/integrations`}
            className="text-caption-sm-regular text-tertiary hover:text-secondary"
          >
            {t("agent_git.github.setup.later")}
          </Link>
        </div>
      ) : (
        <p className="text-caption-sm-regular text-tertiary">{t("agent_git.integrations.read_only")}</p>
      )}
    </section>
  );
});
