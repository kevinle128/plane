/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useMemo, useRef } from "react";
import { observer } from "mobx-react";
// plane imports
import { Avatar } from "@makeplane/propel/components/avatar";
import { groupRunTimeline, isAgentRunActive, RunTimelineRows } from "@plane/blocks/agent-run";
import { Spinner } from "@plane/blocks/spinner";
import { useTranslation } from "@plane/i18n";
import type { TAgentRun } from "@plane/types";
import { getFileURL } from "@plane/utils";
// components
import { MarkdownRenderer } from "@/components/ui/markdown-to-component";
// hooks
import { useAgentRun } from "@/hooks/store/use-agent-run";
import { useMember } from "@/hooks/store/use-member";

/** Distance from the bottom, in px, within which new events keep the view scrolled to the end. */
const STICK_TO_BOTTOM_PX = 48;

type Props = {
  run: TAgentRun;
  loadError: boolean;
};

const renderMarkdown = (text: string) => (
  <div className="flex flex-col gap-2 break-words">
    <MarkdownRenderer markdown={text} />
  </div>
);

/** The scrolling Run timeline. It follows new events while the member reads the end. */
export const AgentRunTimeline = observer(function AgentRunTimeline({ run, loadError }: Props) {
  const { t } = useTranslation();
  const { eventsByRun } = useAgentRun();
  const { getUserDetails } = useMember();
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const events = eventsByRun[run.id];
  const active = isAgentRunActive(run.status);
  const entries = useMemo(() => groupRunTimeline(events ?? [], active), [events, active]);
  const requester = getUserDetails(run.requester_id);

  useEffect(() => {
    const element = scrollRef.current;
    if (element && stickToBottom.current) element.scrollTop = element.scrollHeight;
  }, [entries]);

  return (
    <div
      ref={scrollRef}
      role="region"
      aria-label={t("agent_run.timeline.region_label")}
      tabIndex={0}
      onScroll={(event) => {
        const element = event.currentTarget;
        stickToBottom.current = element.scrollHeight - element.scrollTop - element.clientHeight < STICK_TO_BOTTOM_PX;
      }}
      className="min-h-0 flex-1 overflow-y-auto px-4 py-4 focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:outline-none focus-visible:ring-inset"
    >
      {loadError && !events?.length ? (
        <p role="alert" className="text-body-sm-regular text-danger-primary">
          {t("agent_run.timeline.load_error")}
        </p>
      ) : (
        <>
          <RunTimelineRows
            entries={entries}
            renderMarkdown={renderMarkdown}
            requesterGlyph={
              <Avatar
                alt={requester?.display_name ?? ""}
                fallback={requester?.display_name?.[0]?.toUpperCase()}
                size="2xs"
                src={getFileURL(requester?.avatar_url ?? "")}
              />
            }
          />
          {active && (
            <div className="mt-4 flex items-center gap-2 text-body-sm-regular text-tertiary italic" aria-live="polite">
              <Spinner height="14px" width="14px" />
              {t("agent_run.timeline.working_tail")}
            </div>
          )}
        </>
      )}
    </div>
  );
});
