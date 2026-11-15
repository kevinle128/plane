/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { Avatar } from "@makeplane/propel/components/avatar";
import { AgentOutline } from "@makeplane/propel/icons";
import { ActivityCommentCard, ActivityCommentHeader, ActivityTimelineTimestamp } from "@plane/blocks/activity";
import { RunStatusLabel } from "@plane/blocks/agent-run";
import { useTranslation } from "@plane/i18n";
import type { TAgentRun } from "@plane/types";
import { calculateTimeAgo, getFileURL, renderFormattedDate, renderFormattedTime } from "@plane/utils";
// components
import { LiteTextEditor } from "@/components/editor/lite-text";
// hooks
import { useAgentRun } from "@/hooks/store/use-agent-run";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useMember } from "@/hooks/store/use-member";
import { useWorkspace } from "@/hooks/store/use-workspace";
// local imports
import { getOpenRunButtonId } from "./panel-root";
import { useRunElapsed } from "./use-run-elapsed";

type Props = {
  run: TAgentRun;
  issueId: string;
  workspaceSlug: string;
  projectId: string;
  /** Draw the activity rail down to the next entry. */
  showConnector: boolean;
};

/**
 * One Run in the work-item activity: who asked which Agent, the request, the live status and, when the Run
 * ends, its conclusion. Thoughts and tool calls stay in the Run panel.
 */
export const AgentRunCard = observer(function AgentRunCard(props: Props) {
  const { run, issueId, workspaceSlug, projectId, showConnector } = props;
  const { t } = useTranslation();
  const { getUserDetails } = useMember();
  const {
    comment: { getCommentById },
  } = useIssueDetail();
  const { getWorkspaceBySlug } = useWorkspace();
  const { openRun, openPanel } = useAgentRun();
  const elapsed = useRunElapsed(run);
  // derived values
  const requester = getUserDetails(run.requester_id);
  const requesterName = requester?.display_name ?? "";
  const request = getCommentById(run.trigger_comment_id)?.comment_stripped?.trim() ?? "";
  const conclusion = run.conclusion_comment_id ? getCommentById(run.conclusion_comment_id) : undefined;
  const workspaceId = getWorkspaceBySlug(workspaceSlug)?.id ?? "";
  const showFailure = run.status === "failed" && !conclusion;

  return (
    <ActivityCommentCard
      id={`agent-run-${run.id}`}
      showConnector={showConnector}
      icon={<AgentOutline />}
      avatar={
        <Avatar
          alt={requesterName}
          fallback={requesterName[0]?.toUpperCase()}
          size="2xs"
          src={getFileURL(requester?.avatar_url ?? "")}
        />
      }
      header={
        <ActivityCommentHeader
          author={requesterName}
          action={t("agent_run.card.mentioned", { agent: `@${run.agent.name}` })}
          timestamp={
            <ActivityTimelineTimestamp
              tooltip={`${renderFormattedDate(run.created_at)} ${renderFormattedTime(run.created_at)}`}
            >
              {calculateTimeAgo(run.created_at)}
            </ActivityTimelineTimestamp>
          }
        />
      }
    >
      <div className="flex flex-col gap-2">
        {request && <p className="line-clamp-3 text-body-sm-regular break-words text-primary">{request}</p>}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <RunStatusLabel status={run.status} />
          <span className="rounded-full border border-subtle bg-layer-1 px-2 py-0.5 text-caption-sm-regular text-secondary">
            {t("agent_run.kind.qa_read_only")}
          </span>
          <span className="font-code text-caption-sm-regular text-tertiary">{elapsed}</span>
          <button
            id={getOpenRunButtonId(run.id)}
            type="button"
            aria-expanded={openRun?.runId === run.id}
            onClick={() => openPanel(issueId, run.id)}
            className="ms-auto rounded-sm text-caption-sm-medium text-link-primary hover:underline focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:outline-none"
          >
            {t("agent_run.card.open_run")} →
          </button>
        </div>
        {showFailure && (
          <p className="text-caption-sm-regular break-words text-danger-primary">
            {run.failure_message || t("agent_run.card.failed_generic")}
          </p>
        )}
        {conclusion && (
          <div className="border-t border-subtle pt-2">
            <LiteTextEditor
              editable={false}
              id={conclusion.id}
              initialValue={conclusion.comment_html ?? ""}
              workspaceId={workspaceId}
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              containerClassName="p-0!"
              displayConfig={{ fontSize: "small-font" }}
              parentClassName="border-none"
            />
          </div>
        )}
      </div>
    </ActivityCommentCard>
  );
});
