/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { BadgeVariant } from "@makeplane/propel/components/badge";
import type { IconGlyph } from "@makeplane/propel/components/icon";
import {
  AlertCircleOutline,
  CircleDashedOutline,
  ClockOutline,
  HourglassOutline,
  PauseOutline,
  StopCircleOutline,
  TickCircleOutline,
} from "@makeplane/propel/icons";
import type { TAgentRunStatus } from "@plane/types";

export type TAgentRunStatusMeta = {
  icon: IconGlyph;
  /** Translation key of the status label. The label is always shown, so color is never the only signal. */
  labelKey: string;
  /** Semantic text token class for the icon and label. */
  textClass: string;
  badgeVariant: BadgeVariant;
  /** The icon turns while the Run works. */
  spin: boolean;
};

const STATUS_META: Record<TAgentRunStatus, TAgentRunStatusMeta> = {
  created: {
    icon: HourglassOutline,
    labelKey: "agent_run.status.created",
    textClass: "text-tertiary",
    badgeVariant: "neutral",
    spin: false,
  },
  in_progress: {
    icon: CircleDashedOutline,
    labelKey: "agent_run.status.in_progress",
    textClass: "text-accent-primary",
    badgeVariant: "brand",
    spin: true,
  },
  awaiting: {
    icon: PauseOutline,
    labelKey: "agent_run.status.awaiting",
    textClass: "text-warning-primary",
    badgeVariant: "warning",
    spin: false,
  },
  completed: {
    icon: TickCircleOutline,
    labelKey: "agent_run.status.completed",
    textClass: "text-success-primary",
    badgeVariant: "success",
    spin: false,
  },
  failed: {
    icon: AlertCircleOutline,
    labelKey: "agent_run.status.failed",
    textClass: "text-danger-primary",
    badgeVariant: "danger",
    spin: false,
  },
  stale: {
    icon: ClockOutline,
    labelKey: "agent_run.status.stale",
    textClass: "text-warning-primary",
    badgeVariant: "warning",
    spin: false,
  },
  stopped: {
    icon: StopCircleOutline,
    labelKey: "agent_run.status.stopped",
    textClass: "text-secondary",
    badgeVariant: "neutral",
    spin: false,
  },
};

const ACTIVE_STATUSES: ReadonlySet<TAgentRunStatus> = new Set(["created", "in_progress", "awaiting"]);

/** Icon, label key, semantic color and badge variant of a Run status. */
export function getAgentRunStatusMeta(status: TAgentRunStatus): TAgentRunStatusMeta {
  return STATUS_META[status];
}

/** A Run that can still change without a member action: waiting for pickup, working, or waiting for the member. */
export function isAgentRunActive(status: TAgentRunStatus): boolean {
  return ACTIVE_STATUSES.has(status);
}
