/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Button } from "@makeplane/propel/components/button";
import {
  getHarnessConnectionAction,
  getHarnessConnectionTag,
  getMissingActionKey,
  type THarnessConnectionTone,
} from "@plane/blocks/agent-run";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { Spinner } from "@plane/blocks/spinner";
import { setToast } from "@plane/blocks/toast";
import { AGENT_PROBE_HARNESSES } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TAgent, TAgentConnectionState } from "@plane/types";
import { cn } from "@plane/utils";
import { useAgent } from "@/hooks/store/use-agent";

const TONE_CLASSES: Record<THarnessConnectionTone, string> = {
  success: "text-success-primary",
  tertiary: "text-tertiary",
  danger: "text-danger-primary",
  accent: "text-accent-primary",
};

const HINT_KEYS: Record<TAgentConnectionState, string> = {
  not_connected: "agent_settings.connection.hint_not_connected",
  connecting: "agent_settings.connection.hint_connecting",
  connected: "agent_settings.connection.hint_connected",
  failed: "agent_settings.connection.hint_failed",
};

/** Connection state as text with a semantic color; never relies on color alone. */
export function HarnessStatusTag({ state, className }: { state: TAgentConnectionState; className?: string }) {
  const { t } = useTranslation();
  const tag = getHarnessConnectionTag(state);
  return <span className={cn("text-caption-sm-medium", TONE_CLASSES[tag.tone], className)}>{t(tag.labelKey)}</span>;
}

type Props = {
  workspaceSlug: string;
  agent: TAgent;
  canEdit: boolean;
};

/** Connection row: state, hint, the missing action of a failed probe, and the one available action. */
export const HarnessConnectionRow = observer(function HarnessConnectionRow({ workspaceSlug, agent, canEdit }: Props) {
  const { t } = useTranslation();
  const { connect, disconnect } = useAgent();
  const [isStarting, setIsStarting] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const { state, missing_action: missingAction, failure_hint: failureHint } = agent.connection;
  const probeAvailable = AGENT_PROBE_HARNESSES.includes(agent.harness);
  const action = canEdit && probeAvailable ? getHarnessConnectionAction(state) : null;
  const missingActionKey = state === "failed" ? getMissingActionKey(missingAction) : null;
  const hintKey =
    probeAvailable || state !== "not_connected" ? HINT_KEYS[state] : "agent_settings.connection.hint_unavailable";

  const startProbe = async () => {
    setIsStarting(true);
    try {
      await connect(workspaceSlug, agent.harness);
    } catch {
      setToast({ type: "error", title: t("agent_settings.connection.connect_failed") });
    } finally {
      setIsStarting(false);
    }
  };

  const confirmDisconnect = async () => {
    setIsDisconnecting(true);
    try {
      await disconnect(workspaceSlug, agent.harness);
      setIsConfirmOpen(false);
    } catch {
      setToast({ type: "error", title: t("agent_settings.connection.disconnect_failed") });
    } finally {
      setIsDisconnecting(false);
    }
  };

  return (
    <li
      className={cn("flex flex-wrap items-start gap-2 border-b border-subtle px-4 py-3", {
        "bg-danger-subtle": state === "failed",
      })}
    >
      <div className="flex min-w-0 flex-1 basis-56 flex-col gap-1">
        <span className="flex items-center gap-2">
          <span className="text-body-sm-medium text-primary">{t("agent_settings.connection.label")}</span>
          <HarnessStatusTag state={state} />
        </span>
        <span className="text-caption-sm-regular text-pretty text-tertiary">{t(hintKey)}</span>
        {missingActionKey && (
          <span role="alert" className="text-caption-sm-medium text-danger-primary">
            {t(missingActionKey)}
          </span>
        )}
        {state === "failed" && failureHint && (
          <span
            aria-label={t("agent_settings.connection.failure_detail_label")}
            className="w-fit max-w-full rounded-md border border-subtle bg-surface-2 px-2 py-1 font-code text-caption-sm-regular break-words text-danger-primary"
          >
            {failureHint}
          </span>
        )}
      </div>
      <span className="ml-auto flex shrink-0 items-center gap-2">
        {state === "connecting" && <Spinner height="14px" width="14px" />}
        {action === "connect" && (
          <Button
            variant="primary"
            size="sm"
            stretch="auto"
            label={t("agent_settings.connection.connect")}
            loading={isStarting}
            onClick={() => void startProbe()}
          />
        )}
        {action === "retry" && (
          <Button
            variant="secondary"
            size="sm"
            stretch="auto"
            label={t("agent_settings.connection.retry")}
            loading={isStarting}
            onClick={() => void startProbe()}
          />
        )}
        {action === "disconnect" && (
          <Button
            variant="tertiary"
            size="sm"
            stretch="auto"
            label={t("agent_settings.connection.disconnect")}
            onClick={() => setIsConfirmOpen(true)}
          />
        )}
      </span>
      <ConfirmDialog
        isOpen={isConfirmOpen}
        variant="danger"
        title={t("agent_settings.connection.disconnect_confirm_title", { name: agent.name })}
        content={t("agent_settings.connection.disconnect_confirm_content")}
        handleClose={() => setIsConfirmOpen(false)}
        handleSubmit={confirmDisconnect}
        isSubmitting={isDisconnecting}
        primaryButtonText={{
          default: t("agent_settings.connection.disconnect"),
          loading: t("agent_settings.connection.disconnecting"),
        }}
      />
    </li>
  );
});
