/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { formatRunDuration, getRunElapsedMs, isAgentRunActive } from "@plane/blocks/agent-run";
import type { TAgentRun } from "@plane/types";

/** Elapsed time of a Run as text; it updates every second while the Run is active. */
export function useRunElapsed(run: TAgentRun): string {
  const [now, setNow] = useState(() => new Date());
  const active = isAgentRunActive(run.status);

  useEffect(() => {
    if (!active) return;
    setNow(new Date());
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, [active]);

  return formatRunDuration(getRunElapsedMs(run, now));
}
