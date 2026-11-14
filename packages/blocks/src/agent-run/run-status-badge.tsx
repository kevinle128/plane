/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Badge } from "@makeplane/propel/components/badge";
import { Icon } from "@makeplane/propel/components/icon";
import { useTranslation } from "@plane/i18n";
import type { TAgentRunStatus } from "@plane/types";
import { cn } from "@plane/utils";
import { getAgentRunStatusMeta } from "./status-meta";

type Props = {
  status: TAgentRunStatus;
  className?: string;
};

function StatusIcon({ status }: { status: TAgentRunStatus }) {
  const meta = getAgentRunStatusMeta(status);
  return (
    <span className={cn("inline-flex", meta.spin && "animate-spin motion-reduce:animate-none")}>
      <Icon icon={meta.icon} />
    </span>
  );
}

/** Run status as a Propel badge: icon and label. */
export function RunStatusBadge({ status }: { status: TAgentRunStatus }) {
  const { t } = useTranslation();
  const meta = getAgentRunStatusMeta(status);
  return (
    <Badge size="sm" variant={meta.badgeVariant} label={t(meta.labelKey)} startIcon={<StatusIcon status={status} />} />
  );
}

/** Run status as an icon and a label in the status color, for inline status rows. */
export function RunStatusLabel({ status, className }: Props) {
  const { t } = useTranslation();
  const meta = getAgentRunStatusMeta(status);
  return (
    <span className={cn("inline-flex items-center gap-1 text-caption-sm-medium", meta.textClass, className)}>
      <StatusIcon status={status} />
      <span>{t(meta.labelKey)}</span>
    </span>
  );
}
