/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
import { Avatar } from "@makeplane/propel/components/avatar";
import { AnchorButton } from "@makeplane/propel/components/anchor-button";
import { ArrowNarrowLeftOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import type { TAgentGitConnection, TAgentGitDisconnectResult, TAgentGitProvider } from "@plane/types";
import { getFileURL, renderFormattedDate } from "@plane/utils";
import { SettingsHeading } from "@/components/settings/heading";
import { useAgentGit } from "@/hooks/store/use-agent-git";
import { GitAccountsList } from "./accounts-list";
import { GitChangeRequestPolicy } from "./change-request-policy";
import { GitDisconnectAction } from "./disconnect-action";
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

const DISCONNECT_CONFIRM_KEYS: Record<TAgentGitProvider, string> = {
  github: "agent_git.connection.github_disconnect_confirm_content",
  gitlab: "agent_git.connection.github_disconnect_confirm_content",
};

const REVOKE_HINTS: Record<TAgentGitProvider, { messageKey: string; href: string }> = {
  github: {
    messageKey: "agent_git.connection.github_revoke_in_provider",
    href: "https://github.com/settings/apps/authorizations",
  },
  gitlab: {
    messageKey: "agent_git.connection.github_revoke_in_provider",
    href: "https://github.com/settings/apps/authorizations",
  },
};

function DisconnectResultNotice({ result }: { result: TAgentGitDisconnectResult }) {
  const { t } = useTranslation();
  const hint = REVOKE_HINTS[result.provider];
  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-2 rounded-md border border-subtle bg-layer-1 px-3 py-2 text-caption-sm-regular text-secondary"
    >
      <span className="flex-1">
        {t("agent_git.connection.disconnected", { provider: agentGitProviderLabel(result.provider) })}{" "}
        {result.revoke_in_provider && t(hint.messageKey)}
      </span>
      {result.revoke_in_provider && (
        <AnchorButton
          variant="secondary"
          size="sm"
          href={hint.href}
          external
          label={t("agent_git.connection.open_github_authorizations")}
        />
      )}
    </div>
  );
}

function ConnectionMetaStrip({ connection, action }: { connection: TAgentGitConnection; action?: React.ReactNode }) {
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
      {action && <div className="ml-auto">{action}</div>}
    </div>
  );
}

/** Detail page shared by GitHub and GitLab: setup state, connection facts and settings. */
export const GitProviderDetailPage = observer(function GitProviderDetailPage(props: Props) {
  const { workspaceSlug, provider, canEdit } = props;
  const { t } = useTranslation();
  const { fetchConnections, getConnection } = useAgentGit();
  const [disconnectResult, setDisconnectResult] = useState<TAgentGitDisconnectResult | null>(null);
  const { isLoading } = useSWR(`AGENT_GIT_CONNECTIONS_${workspaceSlug}`, () => fetchConnections(workspaceSlug));
  const connection = getConnection(workspaceSlug, provider);
  const isConnected = connection?.status === "connected";
  const needsReconnect = connection?.status === "reconnect_required";
  const reconnectKey =
    connection?.last_error === "connected_admin_lost"
      ? "agent_git.github.reconnect.connected_admin_lost"
      : "agent_git.github.reconnect.generic";

  const disconnectAction = (
    <GitDisconnectAction
      workspaceSlug={workspaceSlug}
      provider={provider}
      confirmContentKey={DISCONNECT_CONFIRM_KEYS[provider]}
      onDisconnected={setDisconnectResult}
    />
  );

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
      {disconnectResult && <DisconnectResultNotice result={disconnectResult} />}
      {needsReconnect && (
        <div
          role="alert"
          className="flex flex-wrap items-center gap-2 rounded-md bg-warning-subtle px-3 py-2 text-body-sm-regular text-warning-primary"
        >
          <span className="flex-1">{t(reconnectKey)}</span>
          {canEdit && disconnectAction}
        </div>
      )}
      {!isLoading && isConnected && connection && (
        <>
          <ConnectionMetaStrip connection={connection} action={canEdit ? disconnectAction : undefined} />
          <GitAccountsList workspaceSlug={workspaceSlug} connection={connection} canEdit={canEdit} />
          <GitChangeRequestPolicy workspaceSlug={workspaceSlug} provider={provider} canEdit={canEdit} />
        </>
      )}
      {!isLoading && !isConnected && provider === "github" && (
        <GithubSetupCard workspaceSlug={workspaceSlug} canEdit={canEdit} />
      )}
    </div>
  );
});
