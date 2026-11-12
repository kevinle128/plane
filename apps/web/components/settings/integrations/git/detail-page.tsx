/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
import { Avatar } from "@makeplane/propel/components/avatar";
import { ArrowNarrowLeftOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import type { TAgentGitConnection, TAgentGitProvider } from "@plane/types";
import { getFileURL, renderFormattedDate } from "@plane/utils";
import { SettingsHeading } from "@/components/settings/heading";
import { useAgentGit } from "@/hooks/store/use-agent-git";
import { GitAccountsList } from "./accounts-list";
import { GithubSetupCard } from "./github/setup-card";
import { agentGitProviderLabel } from "./provider-meta";

type Props = {
  workspaceSlug: string;
  provider: TAgentGitProvider;
  canEdit: boolean;
};

const DESCRIPTION_KEYS: Record<TAgentGitProvider, string> = {
  github: "agent_git.github.description",
  gitlab: "agent_git.github.description",
};

function ConnectionMetaStrip({ connection }: { connection: TAgentGitConnection }) {
  const { t } = useTranslation();
  const connectedBy = connection.connected_by_detail;
  return (
    <div className="flex flex-wrap items-center gap-6 rounded-lg border border-subtle bg-surface-1 px-4 py-3">
      {connectedBy && (
        <div className="flex flex-col gap-1">
          <span className="tracking-wider text-11 font-semibold text-tertiary uppercase">
            {t("agent_git.github.meta.enabled_by")}
          </span>
          <span className="flex items-center gap-2 text-body-sm-regular text-primary">
            <Avatar size="sm" src={getFileURL(connectedBy.avatar_url ?? "")} alt={connectedBy.display_name} />
            {connectedBy.display_name}
            {connection.connected_at && (
              <span className="text-caption-sm-regular text-tertiary">
                {renderFormattedDate(connection.connected_at)}
              </span>
            )}
          </span>
        </div>
      )}
      <div className="flex flex-col gap-1">
        <span className="tracking-wider text-11 font-semibold text-tertiary uppercase">
          {t("agent_git.github.meta.account")}
        </span>
        <span className="font-code text-body-sm-regular text-primary">{connection.account_login}</span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="tracking-wider text-11 font-semibold text-tertiary uppercase">
          {t("agent_git.github.meta.scopes")}
        </span>
        <span className="font-code text-caption-sm-regular text-secondary">
          {connection.token_scopes.length > 0
            ? connection.token_scopes.join(" · ")
            : t("agent_git.github.meta.no_scopes")}
        </span>
      </div>
    </div>
  );
}

/** Detail page shared by GitHub and GitLab: setup state, connection facts and settings. */
export const GitProviderDetailPage = observer(function GitProviderDetailPage(props: Props) {
  const { workspaceSlug, provider, canEdit } = props;
  const { t } = useTranslation();
  const { fetchConnections, getConnection } = useAgentGit();
  const { isLoading } = useSWR(`AGENT_GIT_CONNECTIONS_${workspaceSlug}`, () => fetchConnections(workspaceSlug));
  const connection = getConnection(workspaceSlug, provider);
  const isConnected = connection?.status === "connected";
  const needsReconnect = connection?.status === "reconnect_required";
  const reconnectKey =
    connection?.last_error === "connected_admin_lost"
      ? "agent_git.github.reconnect.connected_admin_lost"
      : "agent_git.github.reconnect.generic";

  return (
    <div className="flex w-full flex-col gap-6">
      <Link
        href={`/${workspaceSlug}/settings/integrations`}
        className="flex w-fit items-center gap-1 text-caption-sm-regular text-tertiary hover:text-secondary"
      >
        <ArrowNarrowLeftOutline className="size-3.5" aria-hidden="true" />
        {t("agent_git.integrations.back")}
      </Link>
      <SettingsHeading title={agentGitProviderLabel(provider)} description={t(DESCRIPTION_KEYS[provider])} />
      {needsReconnect && (
        <p role="alert" className="rounded-md bg-warning-subtle px-3 py-2 text-body-sm-regular text-warning-primary">
          {t(reconnectKey)}
        </p>
      )}
      {!isLoading && isConnected && connection && (
        <>
          <ConnectionMetaStrip connection={connection} />
          <GitAccountsList workspaceSlug={workspaceSlug} connection={connection} canEdit={canEdit} />
        </>
      )}
      {!isLoading && !isConnected && provider === "github" && (
        <GithubSetupCard workspaceSlug={workspaceSlug} canEdit={canEdit} />
      )}
    </div>
  );
});
