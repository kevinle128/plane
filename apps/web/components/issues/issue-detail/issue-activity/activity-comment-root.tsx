/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { insertRunsByTime } from "@plane/blocks/agent-run";
import { EmptyStateCompact } from "@plane/blocks/empty-state";
import type { E_SORT_ORDER, TActivityFilters } from "@plane/constants";
import { BASE_ACTIVITY_FILTER_TYPES, EActivityFilterType, filterActivityOnSelectedFilters } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TCommentsOperations } from "@plane/types";
// components
import { CommentCard } from "@/components/comments/card/root";
// hooks
import { useAgentRun } from "@/hooks/store/use-agent-run";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// local imports
import { IssueActivityItem } from "./activity/activity-list";
import { AgentRunCardRow } from "./agent-run-card-row";
import { IssueActivityLoader } from "./loader";

type TIssueActivityCommentRoot = {
  workspaceSlug: string;
  projectId: string;
  isIntakeIssue: boolean;
  issueId: string;
  selectedFilters: TActivityFilters[];
  activityOperations: TCommentsOperations;
  showAccessSpecifier?: boolean;
  disabled?: boolean;
  sortOrder: E_SORT_ORDER;
};

export const IssueActivityCommentRoot = observer(function IssueActivityCommentRoot(props: TIssueActivityCommentRoot) {
  const {
    workspaceSlug,
    isIntakeIssue,
    issueId,
    selectedFilters,
    activityOperations,
    showAccessSpecifier,
    projectId,
    disabled,
    sortOrder,
  } = props;
  // translation
  const { t } = useTranslation();
  // store hooks
  const {
    activity: { getActivityAndCommentsByIssueId },
    comment: { getCommentById },
  } = useIssueDetail();
  const { getRunsByIssueId } = useAgentRun();
  // derived values
  const activityAndComments = getActivityAndCommentsByIssueId(issueId, sortOrder);

  if (!activityAndComments) return <IssueActivityLoader />;

  // Run cards go with comments. A Run's conclusion comment is shown inside its card, not a second time.
  const runs = selectedFilters.includes(EActivityFilterType.COMMENT) ? (getRunsByIssueId(issueId) ?? []) : [];
  const conclusionCommentIds = new Set(runs.map((run) => run.conclusion_comment_id).filter(Boolean));
  const filteredActivityAndComments = insertRunsByTime(
    filterActivityOnSelectedFilters(activityAndComments, selectedFilters).filter(
      (activityComment) =>
        !(activityComment.activity_type === "COMMENT" && conclusionCommentIds.has(activityComment.id))
    ),
    runs,
    sortOrder
  );

  if (filteredActivityAndComments.length <= 0) {
    const isCommentsOnly = selectedFilters.every((filter) => filter === EActivityFilterType.COMMENT);
    return (
      <div className="py-6">
        <EmptyStateCompact
          assetKey={isCommentsOnly ? "comment" : "activity"}
          title={t(isCommentsOnly ? "activity_empty_state.no_comments" : "activity_empty_state.no_activity")}
        />
      </div>
    );
  }

  // the last entry ends the timeline rail
  const getEnds = (index: number) =>
    index === filteredActivityAndComments.length - 1 ? "bottom" : index === 0 ? "top" : undefined;

  return (
    <div>
      {filteredActivityAndComments.map((row, index) => {
        if (row.type === "run")
          return (
            <AgentRunCardRow
              key={`agent-run-${row.run.id}`}
              runId={row.run.id}
              issueId={issueId}
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              ends={getEnds(index)}
            />
          );
        const activityComment = row.entry;
        const comment = getCommentById(activityComment.id);
        return activityComment.activity_type === "COMMENT" ? (
          <CommentCard
            key={activityComment.id}
            workspaceSlug={workspaceSlug}
            entityId={issueId}
            comment={comment}
            activityOperations={activityOperations}
            ends={getEnds(index)}
            showAccessSpecifier={!!showAccessSpecifier}
            showCopyLinkOption={!isIntakeIssue}
            disabled={disabled}
            projectId={projectId}
            enableReplies
          />
        ) : BASE_ACTIVITY_FILTER_TYPES.includes(activityComment.activity_type as EActivityFilterType) ? (
          <IssueActivityItem key={activityComment.id} activityId={activityComment.id} ends={getEnds(index)} />
        ) : null;
      })}
    </div>
  );
});
