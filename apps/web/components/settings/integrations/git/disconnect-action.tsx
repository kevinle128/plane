/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Button } from "@makeplane/propel/components/button";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TAgentGitDisconnectResult, TAgentGitProvider } from "@plane/types";
import { useAgentGit } from "@/hooks/store/use-agent-git";
import { agentGitErrorMessage, agentGitProviderLabel } from "./provider-meta";

type Props = {
  workspaceSlug: string;
  provider: TAgentGitProvider;
  confirmContentKey: string;
  onDisconnected: (result: TAgentGitDisconnectResult) => void;
};

/** Disconnect button with a confirmation. On failure the connection stays and an actionable error shows. */
export const GitDisconnectAction = observer(function GitDisconnectAction(props: Props) {
  const { workspaceSlug, provider, confirmContentKey, onDisconnected } = props;
  const { t } = useTranslation();
  const { disconnect } = useAgentGit();
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const providerName = agentGitProviderLabel(provider);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const result = await disconnect(workspaceSlug, provider);
      setIsOpen(false);
      onDisconnected(result);
    } catch (error) {
      setToast({ type: "error", title: agentGitErrorMessage(t, error) });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Button
        variant="tertiary"
        size="sm"
        stretch="auto"
        label={t("agent_git.connection.disconnect")}
        onClick={() => setIsOpen(true)}
      />
      <ConfirmDialog
        isOpen={isOpen}
        variant="danger"
        title={t("agent_git.connection.disconnect_confirm_title", { provider: providerName })}
        content={t(confirmContentKey)}
        handleClose={() => setIsOpen(false)}
        handleSubmit={handleSubmit}
        isSubmitting={isSubmitting}
        primaryButtonText={{
          default: t("agent_git.connection.disconnect"),
          loading: t("agent_git.connection.disconnecting"),
        }}
      />
    </>
  );
});
