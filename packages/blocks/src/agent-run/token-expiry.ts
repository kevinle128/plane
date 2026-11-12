/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgentGitProvider } from "@plane/types";

export const TOKEN_EXPIRY_WARNING_DAYS = 14;
const DAY_MS = 24 * 60 * 60 * 1000;

export type TTokenExpiryState = {
  expired: boolean;
  expiresSoon: boolean;
};

export type TTokenExpiryWarning = "expired" | "expires_soon";

/** Expiry state of a provider token, computed on read: a warning shows within 14 days of expiry. */
export function getTokenExpiryState(
  expiresAt: string | null,
  now: number = Date.now(),
  warningDays: number = TOKEN_EXPIRY_WARNING_DAYS
): TTokenExpiryState {
  const expiresAtMs = expiresAt ? Date.parse(expiresAt) : Number.NaN;
  if (Number.isNaN(expiresAtMs)) return { expired: false, expiresSoon: false };
  if (expiresAtMs <= now) return { expired: true, expiresSoon: false };
  return { expired: false, expiresSoon: expiresAtMs - now <= warningDays * DAY_MS };
}

/**
 * Token expiry warning of a connection. Only a GitLab token needs action from the admin: the GitHub
 * token expires after some hours and Plane refreshes it, so GitHub never shows this warning.
 */
export function getTokenExpiryWarning(
  provider: TAgentGitProvider,
  expiresAt: string | null,
  now: number = Date.now()
): TTokenExpiryWarning | null {
  if (provider !== "gitlab") return null;
  const state = getTokenExpiryState(expiresAt, now);
  if (state.expired) return "expired";
  return state.expiresSoon ? "expires_soon" : null;
}
