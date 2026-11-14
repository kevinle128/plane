/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Ref } from "react";
import { observer } from "mobx-react";
// plane imports
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { AgentOutline, CloseOutline } from "@makeplane/propel/icons";
import { RunStatusBadge } from "@plane/blocks/agent-run";
import { useTranslation } from "@plane/i18n";
import type { TAgentRun } from "@plane/types";
import { renderFormattedDate, renderFormattedTime } from "@plane/utils";
// local imports
import { useRunElapsed } from "./use-run-elapsed";

type Props = {
  run: TAgentRun;
  /** Work item identifier, for example `PROJ-12`. */
  workItemLabel: string;
  activityCount: number;
  closeButtonRef: Ref<HTMLButtonElement>;
  onClose: () => void;
};

/** Run panel header: Agent, work item, Run kind, status, elapsed time, working folder, sandbox and start. */
export const AgentRunPanelHeader = observer(function AgentRunPanelHeader(props: Props) {
  const { run, workItemLabel, activityCount, closeButtonRef, onClose } = props;
  const { t } = useTranslation();
  const elapsed = useRunElapsed(run);
  const startedAt = run.started_at ?? run.created_at;

  return (
    <header className="flex shrink-0 flex-col gap-1.5 border-b border-subtle px-4 py-3">
      <div className="flex items-center gap-2">
        <span
          aria-hidden
          className="grid size-6 shrink-0 place-items-center rounded-md bg-layer-2 text-secondary shadow-raised-100"
        >
          <Icon icon={AgentOutline} />
        </span>
        <h2 className="min-w-0 truncate text-body-sm-semibold text-primary">
          {run.agent.name}
          <span className="ms-1.5 font-code text-caption-sm-regular text-tertiary">
            {workItemLabel ? `${workItemLabel} · ${run.short_id}` : run.short_id}
          </span>
        </h2>
        <span className="shrink-0 rounded-full border border-subtle bg-layer-1 px-2 py-0.5 text-caption-sm-regular text-secondary">
          {t("agent_run.kind.qa_read_only")}
        </span>
        <span className="ms-auto flex shrink-0 items-center gap-2">
          <RunStatusBadge status={run.status} />
          <span className="font-code text-caption-sm-regular text-tertiary">{elapsed}</span>
          <IconButton
            ref={closeButtonRef}
            variant="ghost"
            size="sm"
            aria-label={t("agent_run.panel.close")}
            icon={<Icon icon={CloseOutline} />}
            onClick={onClose}
          />
        </span>
      </div>
      <p className="flex flex-wrap gap-x-3 gap-y-0.5 font-code text-caption-sm-regular text-tertiary">
        <span className="min-w-0 break-all">
          {run.clone_path ? t("agent_run.panel.cwd", { path: run.clone_path }) : t("agent_run.panel.cwd_pending")}
          {" · "}
          {t("agent_run.panel.sandbox_read_only")}
        </span>
        <span>
          {t("agent_run.panel.started", {
            time: `${renderFormattedDate(startedAt)} ${renderFormattedTime(startedAt)}`,
          })}
          {" · "}
          {t("agent_run.panel.activities", { count: activityCount })}
        </span>
      </p>
    </header>
  );
});
