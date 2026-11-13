/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { SVGProps } from "react";
import { Button } from "@makeplane/propel/components/button";
import { Github, Gitlab } from "@makeplane/propel/icons";
import { AGENT_GIT_CONNECTION_STATUS_I18N, AGENT_GIT_PROVIDER_LABELS } from "@plane/constants";
import type { TAgentGitConnection, TAgentGitError, TAgentGitProvider } from "@plane/types";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";

const PROVIDER_ICONS: Record<TAgentGitProvider, (props: SVGProps<SVGSVGElement>) => React.JSX.Element> = {
  github: Github,
  gitlab: Gitlab,
};

export function AgentGitProviderIcon({ provider, className }: { provider: TAgentGitProvider; className?: string }) {
  const Icon = PROVIDER_ICONS[provider];
  return <Icon className={cn("size-4 shrink-0", className)} aria-hidden="true" />;
}

export const agentGitProviderLabel = (provider: TAgentGitProvider) => AGENT_GIT_PROVIDER_LABELS[provider];

/** SWR key of the Git connections of a workspace. */
export const agentGitConnectionsKey = (workspaceSlug: string) => `AGENT_GIT_CONNECTIONS_${workspaceSlug}`;

/** SWR key of the repository catalog of a workspace. */
export const agentGitRepositoriesKey = (workspaceSlug: string) => `AGENT_GIT_REPOSITORIES_${workspaceSlug}`;

/** Shown when the connections cannot load, so a failed request does not look like "not connected". */
export function AgentGitConnectionsError({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-2 rounded-md bg-danger-subtle px-3 py-2 text-body-sm-regular text-danger-primary"
    >
      <span className="flex-1">{t("agent_git.connection.load_error")}</span>
      <Button variant="secondary" size="sm" stretch="auto" label={t("common.retry")} onClick={onRetry} />
    </div>
  );
}

type TTranslate = (key: string, params?: Record<string, unknown>) => string;

/** Translated message for an agent Git API error body. Unknown codes fall back to a generic message. */
export function agentGitErrorMessage(t: TTranslate, error: unknown): string {
  const body = error as TAgentGitError | undefined;
  const code = body?.error;
  if (code) {
    const key = `agent_git.errors.${code}`;
    const message = t(key, { detail: body?.detail ?? "" });
    if (message && message !== key) return message;
  }
  return t("agent_git.errors.generic");
}

/** Status text with a semantic color; never relies on color alone. */
export function AgentGitStatusTag({
  connection,
  t,
  className,
}: {
  connection: TAgentGitConnection | undefined;
  t: TTranslate;
  className?: string;
}) {
  const status = connection?.status ?? "disconnected";
  return (
    <span
      className={cn(
        "text-caption-sm-medium",
        {
          "text-success-primary": status === "connected",
          "text-tertiary": status === "disconnected",
          "text-warning-primary": status === "reconnect_required",
        },
        className
      )}
    >
      {t(AGENT_GIT_CONNECTION_STATUS_I18N[status])}
    </span>
  );
}
