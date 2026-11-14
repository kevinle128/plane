/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { observer } from "mobx-react";
// plane imports
import { isAgentRunActive } from "@plane/blocks/agent-run";
import { AGENT_RUN_POLL_MS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
// hooks
import { useAgentRun } from "@/hooks/store/use-agent-run";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProject } from "@/hooks/store/use-project";
// local imports
import { AgentRunComposerShell } from "./composer-shell";
import { AgentRunPanelHeader } from "./panel-header";
import { AgentRunTimeline } from "./timeline";

/** ID of the Open run button of a Run card; focus returns there when the panel closes. */
export const getOpenRunButtonId = (runId: string) => `agent-run-open-${runId}`;

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
};

/**
 * The Run panel of a work item: one drawer on the right, mounted in a portal so that the full page and the
 * peek view share it. It polls the Run and its events while the Run is active. Focus moves into the panel
 * when it opens, so Escape closes it before the peek; focus returns to the Open run button.
 */
export const AgentRunPanelRoot = observer(function AgentRunPanelRoot(props: Props) {
  const { workspaceSlug, projectId, issueId } = props;
  const { t } = useTranslation();
  const runStore = useAgentRun();
  const { openRun, getRunById, eventsByRun, fetchRun, fetchRunEvents, closePanel } = runStore;
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const { getProjectById } = useProject();
  const [loadError, setLoadError] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  // derived values
  const runId = openRun?.issueId === issueId ? openRun.runId : null;
  const run = runId ? getRunById(runId) : undefined;
  const issue = getIssueById(issueId);
  const projectIdentifier = getProjectById(projectId)?.identifier;
  const workItemLabel = projectIdentifier && issue ? `${projectIdentifier}-${issue.sequence_id}` : "";

  const handleClose = useCallback(() => {
    if (!runId) return;
    closePanel();
    // The card can re-render while the panel unmounts; focus the button after this update.
    setTimeout(() => document.getElementById(getOpenRunButtonId(runId))?.focus(), 0);
  }, [runId, closePanel]);

  // The panel belongs to this work item; it closes when the work item view goes away.
  useEffect(
    () => () => {
      if (runStore.openRun?.issueId === issueId) runStore.closePanel();
    },
    [runStore, issueId]
  );

  // Load the Run and its events on open, then poll every few seconds while the Run is active.
  useEffect(() => {
    if (!runId) return;
    setLoadError(false);
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      let active = false;
      try {
        // Read the status first, so the events read after it include everything up to that status.
        const latest = await fetchRun(workspaceSlug, projectId, issueId, runId);
        active = isAgentRunActive(latest.status);
        await fetchRunEvents(workspaceSlug, projectId, issueId, runId);
        if (!cancelled) setLoadError(false);
      } catch (error) {
        console.error("Failed to load the Run timeline:", error);
        if (cancelled) return;
        setLoadError(true);
        const known = getRunById(runId);
        active = !!known && isAgentRunActive(known.status);
      }
      if (!cancelled && active) timer = setTimeout(poll, AGENT_RUN_POLL_MS);
    };
    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [workspaceSlug, projectId, issueId, runId, fetchRun, fetchRunEvents, getRunById]);

  // Focus the close button when the panel opens, so keyboard users start inside it.
  useEffect(() => {
    if (runId) closeButtonRef.current?.focus();
  }, [runId]);

  if (!run || typeof document === "undefined") return null;

  const activityCount = Math.max(run.event_count, eventsByRun[run.id]?.length ?? 0);

  return createPortal(
    <aside
      aria-label={t("agent_run.panel.label", { id: run.short_id })}
      data-prevent-outside-click
      // Escape inside the panel closes the panel only. React handles the event at its root container,
      // below the document listener of the peek, so stopping it here leaves the peek open. Popups and
      // editors outside the panel keep their own Escape.
      onKeyDown={(event) => {
        if (event.key !== "Escape" || event.defaultPrevented) return;
        event.stopPropagation();
        handleClose();
      }}
      className="fixed inset-y-0 right-0 z-30 flex w-[540px] max-w-full flex-col border-l border-subtle bg-surface-1 shadow-overlay-200"
    >
      <AgentRunPanelHeader
        run={run}
        workItemLabel={workItemLabel}
        activityCount={activityCount}
        closeButtonRef={closeButtonRef}
        onClose={handleClose}
      />
      <AgentRunTimeline run={run} loadError={loadError} />
      <AgentRunComposerShell agentName={run.agent.name} />
    </aside>,
    document.body
  );
});
