/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { SendOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";

type Props = {
  agentName: string;
};

/** The place of the Run composer. Messages to a Run are not available yet, so the input is disabled. */
export function AgentRunComposerShell({ agentName }: Props) {
  const { t } = useTranslation();
  const placeholder = t("agent_run.composer.placeholder", { agent: agentName });
  return (
    <div className="shrink-0 border-t border-subtle px-4 py-3">
      <div className="flex items-center gap-2 rounded-lg border border-subtle bg-surface-2 px-3 py-2">
        <input
          type="text"
          disabled
          aria-label={placeholder}
          placeholder={placeholder}
          className="min-w-0 flex-1 bg-transparent text-body-sm-regular text-primary placeholder:text-placeholder disabled:cursor-not-allowed"
        />
        <IconButton
          variant="ghost"
          size="sm"
          disabled
          aria-label={t("agent_run.composer.send")}
          icon={<Icon icon={SendOutline} />}
        />
      </div>
    </div>
  );
}
