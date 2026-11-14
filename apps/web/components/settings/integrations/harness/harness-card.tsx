/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import Link from "next/link";
import { AgentOutline } from "@makeplane/propel/icons";
import { AGENT_HARNESS_COMMANDS, AGENT_HARNESS_LABELS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TAgent, TAgentHarness } from "@plane/types";
import { HarnessStatusTag } from "./connection-row";

/** CLI command with the version of its last verified probe, for example `claude 2.1.289`. */
export const harnessCliLabel = (harness: TAgentHarness, version: string) =>
  version ? `${AGENT_HARNESS_COMMANDS[harness]} ${version}` : AGENT_HARNESS_COMMANDS[harness];

type Props = {
  workspaceSlug: string;
  harness: TAgentHarness;
  /** `undefined` while the Agents load or when they cannot load; the card then shows no state. */
  agent: TAgent | undefined;
};

/** Integrations card of one Harness. The whole card is one link; it holds no other control. */
export function HarnessCard({ workspaceSlug, harness, agent }: Props) {
  const { t } = useTranslation();
  return (
    <Link
      href={`/${workspaceSlug}/settings/integrations/${harness}`}
      className="flex max-w-65 min-w-48 flex-1 basis-52 flex-col gap-2 rounded-lg border border-subtle bg-surface-1 p-3 hover:border-strong focus-visible:outline-2 focus-visible:outline-accent-strong"
    >
      <span className="flex items-center gap-2">
        <span className="flex size-7 items-center justify-center rounded-md border border-subtle bg-layer-2">
          <AgentOutline className="size-4 shrink-0" aria-hidden="true" />
        </span>
        <span className="flex-1 text-body-sm-semibold text-primary">{AGENT_HARNESS_LABELS[harness]}</span>
        {agent && <HarnessStatusTag state={agent.connection.state} />}
      </span>
      <span className="text-caption-sm-regular text-secondary">
        {t(`agent_settings.integrations.blurbs.${harness}`)}
      </span>
      <span className="flex items-center gap-2 text-caption-sm-regular">
        <span className="truncate font-code text-tertiary">
          {harnessCliLabel(harness, agent?.connection.harness_version ?? "")}
        </span>
        <span className="ml-auto text-accent-primary">{t("agent_settings.integrations.configure")}</span>
      </span>
    </Link>
  );
}
