/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useMemo } from "react";
// plane imports
import { Icon } from "@makeplane/propel/components/icon";
import { AgentOutline } from "@makeplane/propel/icons";
import type { TMentionSection, TMentionSuggestion } from "@plane/editor";
import { useTranslation } from "@plane/i18n";
// plane types
import type { TSearchEntities, TSearchResponse } from "@plane/types";

export type TUseAdditionalEditorMentionArgs = {
  enableAdvancedMentions: boolean;
  /** List workspace Agents next to people. Only the work-item comment composer starts Runs from a mention. */
  enableAgentMentions?: boolean;
};

export type TAdditionalEditorMentionHandlerArgs = {
  response: TSearchResponse;
};

export type TAdditionalEditorMentionHandlerReturnType = {
  sections: TMentionSection[];
};

export type TAdditionalParseEditorContentArgs = {
  id: string;
  entityType: TSearchEntities;
};

export type TAdditionalParseEditorContentReturnType =
  | {
      redirectionPath: string;
      textContent: string;
    }
  | undefined;

export const useAdditionalEditorMention = (args: TUseAdditionalEditorMentionArgs) => {
  const { enableAgentMentions = false } = args;
  const { t } = useTranslation();

  const updateAdditionalSections = useCallback(
    ({ response }: TAdditionalEditorMentionHandlerArgs): TAdditionalEditorMentionHandlerReturnType => {
      const agents = enableAgentMentions ? (response.agent_mention ?? []) : [];
      if (agents.length === 0) return { sections: [] };
      const items: TMentionSuggestion[] = agents.map((agent) => ({
        icon: (
          <span className="grid size-5 place-items-center rounded-full bg-accent-subtle text-accent-primary">
            <Icon icon={AgentOutline} />
          </span>
        ),
        id: agent.id,
        entity_identifier: agent.id,
        entity_name: "agent_mention",
        title: `${agent.name} @${agent.handle}`,
        disabled: agent.disabled,
        disabledReason: agent.disabled
          ? t(`agent_run.mention.disabled_reason.${agent.disabled_reason || "not_connected"}`)
          : undefined,
      }));
      return { sections: [{ key: "agents", title: t("agent_run.mention.section_title"), items }] };
    },
    [enableAgentMentions, t]
  );

  const parseAdditionalEditorContent = useCallback(
    (_args: TAdditionalParseEditorContentArgs): TAdditionalParseEditorContentReturnType => undefined,
    []
  );

  const editorMentionTypes: TSearchEntities[] = useMemo(
    () => (enableAgentMentions ? ["user_mention", "agent_mention"] : ["user_mention"]),
    [enableAgentMentions]
  );

  return {
    updateAdditionalSections,
    parseAdditionalEditorContent,
    editorMentionTypes,
  };
};
