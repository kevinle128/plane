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
import { getTokenExpiryWarning } from "@plane/blocks/agent-run";
import { useTranslation } from "@plane/i18n";
import type { TAgentGitConnection, TAgentGitDisconnectResult, TAgentGitProvider } from "@plane/types";
import { getFileURL, renderFormattedDate } from "@plane/utils";
import { SettingsHeading } from "@/components/settings/heading";
import { useAgentGit } from "@/hooks/store/use-agent-git";
import { GitAccountsList } from "./accounts-list";
import { GitChangeRequestPolicy } from "./change-request-policy";
import { GitDisconnectAction } from "./disconnect-action";
import { GithubSetupCard } from "./github/setup-card";
import { GitlabSetupCard } from "./gitlab/setup-card";
import { AgentGitConnectionsError, agentGitConnectionsKey, agentGitProviderLabel } from "./provider-meta";

type Props = {
  workspaceSlug: string;
  provider: TAgentGitProvider;
  canEdit: boolean;
};

const DESCRIPTION_KEYS: Record<TAgentGitProvider, string> = {
  github: "agent_git.github.description",
  gitlab: "agent_git.gitlab.description",
};

const DISCONNECT_CONFIRM_KEYS: Record<TAgentGitProvider, string> = {
  github: "agent_git.connection.github_disconnect_confirm_content",
  gitlab: "agent_git.connection.gitlab_disconnect_confirm_content",
};

const REVOKE_HINTS: Record<TAgentGitProvider, { messageKey: string; linkKey: string }> = {
  github: {
    messageKey: "agent_git.connection.github_revoke_in_provider",
    linkKey: "agent_git.connection.open_github_authorizations",
  },
  gitlab: {
    messageKey: "agent_git.connection.gitlab_revoke_in_provider",
    linkKey: "agent_git.connection.open_gitlab_token_settings",
  },
};

const GITHUB_AUTHORIZATIONS_URL = "https://github.com/settings/apps/authorizations";

function DisconnectResultNotice({ result }: { result: TAgentGitDisconnectResult }) {
  const { t } = useTranslation();
  const hint = REVOKE_HINTS[result.provider];
  const revokeHref = result.provider === "github" ? GITHUB_AUTHORIZATIONS_URL : result.revoke_url;
  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-2 rounded-md border border-subtle bg-layer-1 px-3 py-2 text-caption-sm-regular text-secondary"
    >
      <span className="flex-1">
        {t("agent_git.connection.disconnected", { provider: agentGitProviderLabel(result.provider) })}{" "}
        {result.revoke_in_provider && t(hint.messageKey)}
      </span>
      {result.revoke_in_provider && revokeHref && (
        <AnchorButton variant="secondary" size="sm" href={revokeHref} external label={t(hint.linkKey)} />
      )}
    </div>
  );
}

function MetaItem({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <span className="tracking-wider text-11 font-semibold text-tertiary uppercase">{label}</span>
      <span className="flex min-w-0 items-center gap-2 text-body-sm-regular text-primary">{children}</span>
    </div>
  );
}

function ConnectionMetaStrip({ connection, action }: { connection: TAgentGitConnection; action?: React.ReactNode }) {
  const { t } = useTranslation();
  const connectedBy = connection.connected_by_detail;
  return (
    <div className="flex flex-wrap items-center gap-6 rounded-lg border border-subtle bg-surface-1 px-4 py-3">
      {connectedBy && (
        <MetaItem label={t("agent_git.github.meta.enabled_by")}>
          <Avatar size="sm" src={getFileURL(connectedBy.avatar_url ?? "")} alt={connectedBy.display_name} />
          {connectedBy.display_name}
          {connection.connected_at && (
            <span className="text-caption-sm-regular text-tertiary">
              {renderFormattedDate(connection.connected_at)}
            </span>
          )}
        </MetaItem>
      )}
      {connection.provider === "gitlab" ? (
        <>
          <MetaItem label={t("agent_git.gitlab.meta.base_url")}>
            <span className="truncate font-code">{connection.base_url}</span>
          </MetaItem>
          <MetaItem label={t("agent_git.gitlab.meta.version")}>
            <span className="font-code">{connection.server_version}</span>
          </MetaItem>
          <MetaItem label={t("agent_git.gitlab.meta.token")}>
            <span className="font-code">{connection.token_name}</span>
          </MetaItem>
          <MetaItem label={t("agent_git.gitlab.meta.token_user")}>
            <span className="font-code">{connection.account_login}</span>
          </MetaItem>
          <MetaItem label={t("agent_git.gitlab.meta.expires")}>
            {connection.token_expires_at
              ? renderFormattedDate(connection.token_expires_at)
              : t("agent_git.gitlab.meta.never")}
          </MetaItem>
        </>
      ) : (
        <>
          <MetaItem label={t("agent_git.github.meta.account")}>
            <span className="font-code">{connection.account_login}</span>
          </MetaItem>
          <MetaItem label={t("agent_git.github.meta.scopes")}>
            <span className="font-code text-caption-sm-regular text-secondary">
              {connection.token_scopes.length > 0
                ? connection.token_scopes.join(" · ")
                : t("agent_git.github.meta.no_scopes")}
            </span>
          </MetaItem>
        </>
      )}
      {action && <div className="ml-auto">{action}</div>}
    </div>
  );
}

function ConnectionWarnings({ connection }: { connection: TAgentGitConnection }) {
  const { t } = useTranslation();
  const expiryWarning = getTokenExpiryWarning(connection.provider, connection.token_expires_at);
  const warnings: string[] = [];
  if (connection.warnings.includes("gitlab_token_not_bot")) warnings.push(t("agent_git.gitlab.warnings.not_bot"));
  if (expiryWarning && connection.token_expires_at)
    warnings.push(
      t(`agent_git.gitlab.warnings.${expiryWarning}`, {
        date: renderFormattedDate(connection.token_expires_at) ?? "",
      })
    );
  if (connection.worker_last_error)
    warnings.push(
      t("agent_git.connection.worker_error", { host: connection.host, reason: connection.worker_last_error })
    );
  if (warnings.length === 0) return null;
  return (
    <ul className="flex flex-col gap-2">
      {warnings.map((warning) => (
        <li
          key={warning}
          role="note"
          className="rounded-md bg-warning-subtle px-3 py-2 text-body-sm-regular text-warning-primary"
        >
          {warning}
        </li>
      ))}
    </ul>
  );
}

/** Detail page shared by GitHub and GitLab: setup state, connection facts and settings. */
export const GitProviderDetailPage = observer(function GitProviderDetailPage(props: Props) {
  const { workspaceSlug, provider, canEdit } = props;
  const { t } = useTranslation();
  const { fetchConnections, getConnection } = useAgentGit();
  const [disconnectResult, setDisconnectResult] = useState<TAgentGitDisconnectResult | null>(null);
  const { data, isLoading, error, mutate } = useSWR(agentGitConnectionsKey(workspaceSlug), () =>
    fetchConnections(workspaceSlug)
  );
  // Without loaded connections the page cannot tell connected from not connected, so it shows only the error.
  const isReady = !isLoading && data !== undefined;
  const connection = getConnection(workspaceSlug, provider);
  const isConnected = connection?.status === "connected";
  const needsReconnect = connection?.status === "reconnect_required";
  const reconnectMessage =
    connection?.last_error === "connected_admin_lost"
      ? t("agent_git.github.reconnect.connected_admin_lost")
      : t("agent_git.connection.reconnect_generic", { provider: agentGitProviderLabel(provider) });

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
          <span className="flex-1">{reconnectMessage}</span>
          {canEdit && disconnectAction}
        </div>
      )}
      {!!error && !isLoading && <AgentGitConnectionsError onRetry={() => void mutate()} />}
      {isReady && isConnected && connection && (
        <>
          <ConnectionMetaStrip connection={connection} action={canEdit ? disconnectAction : undefined} />
          <ConnectionWarnings connection={connection} />
          <GitAccountsList workspaceSlug={workspaceSlug} connection={connection} canEdit={canEdit} />
          <GitChangeRequestPolicy workspaceSlug={workspaceSlug} provider={provider} canEdit={canEdit} />
        </>
      )}
      {isReady && !isConnected && provider === "github" && (
        <GithubSetupCard workspaceSlug={workspaceSlug} canEdit={canEdit} />
      )}
      {isReady && !isConnected && provider === "gitlab" && (
        <GitlabSetupCard workspaceSlug={workspaceSlug} canEdit={canEdit} />
      )}
    </div>
  );
});
