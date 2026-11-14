/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// components
import { AgentRunCard } from "@/components/agent-run/run-card";
// hooks
import { useAgentRun } from "@/hooks/store/use-agent-run";

type Props = {
  runId: string;
  issueId: string;
  workspaceSlug: string;
  projectId: string;
  ends: "top" | "bottom" | undefined;
};

/** The Run card at its place in the activity list. */
export const AgentRunCardRow = observer(function AgentRunCardRow(props: Props) {
  const { runId, issueId, workspaceSlug, projectId, ends } = props;
  const { getRunById } = useAgentRun();
  const run = getRunById(runId);
  if (!run) return null;
  return (
    <AgentRunCard
      run={run}
      issueId={issueId}
      workspaceSlug={workspaceSlug}
      projectId={projectId}
      showConnector={ends !== "bottom"}
    />
  );
});
