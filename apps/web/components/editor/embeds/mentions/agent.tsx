/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
// hooks
import { useAgent } from "@/hooks/store/use-agent";
import { useAgentRun } from "@/hooks/store/use-agent-run";

type Props = {
  id: string;
};

/** An Agent mention in a comment. The name comes from the workspace Agents, else from a Run snapshot of that Agent. */
export const EditorAgentMention = observer(function EditorAgentMention(props: Props) {
  const { id } = props;
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();
  const { getAgentById, fetchAgentsOnce } = useAgent();
  const { runMap } = useAgentRun();
  const slug = workspaceSlug?.toString() ?? "";

  useEffect(() => {
    if (!slug) return;
    fetchAgentsOnce(slug).catch(() => {
      // Members without the Agents list (guests) still see names from Run snapshots or the fallback label.
    });
  }, [slug, fetchAgentsOnce]);

  const name =
    getAgentById(slug, id)?.name ??
    Object.values(runMap).find((run) => run.agent.id === id)?.agent.name ??
    t("agent_run.mention.unknown_agent");

  return (
    <span className="not-prose inline rounded-sm bg-accent-subtle-active px-1 py-0.5 text-accent-primary no-underline">
      @{name}
    </span>
  );
});
