/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TDeviceCodeExpiry = {
  expired: boolean;
  secondsLeft: number;
  /** `m:ss`, for example `14:22`. */
  label: string;
};

/** What to do after a poll request fails. */
export type TDevicePollErrorAction = "retry" | "stop";

/**
 * Local deadline (ms) of a device code. The server lifetime of the code (`expires_at - created_at`) is added
 * to the local time the response arrived, so a wrong browser clock does not change the countdown. Without a
 * readable `created_at`, the absolute `expires_at` is used. The countdown is for display only: the poll
 * status from the server decides when the code is expired.
 */
export function getDeviceCodeDeadline(
  authorization: { expires_at: string; created_at?: string },
  receivedAt: number
): number {
  const expiresAtMs = Date.parse(authorization.expires_at);
  const createdAtMs = authorization.created_at ? Date.parse(authorization.created_at) : Number.NaN;
  if (Number.isNaN(expiresAtMs) || Number.isNaN(createdAtMs)) return expiresAtMs;
  return receivedAt + (expiresAtMs - createdAtMs);
}

/** Time left before a GitHub device code expires, for the "expires in" label. */
export function getDeviceCodeExpiry(deadline: number, now: number = Date.now()): TDeviceCodeExpiry {
  const remainingMs = Number.isNaN(deadline) ? 0 : deadline - now;
  const secondsLeft = remainingMs > 0 ? Math.ceil(remainingMs / 1000) : 0;
  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  return {
    expired: secondsLeft === 0,
    secondsLeft,
    label: `${minutes}:${String(seconds).padStart(2, "0")}`,
  };
}

const RETRY_STATUSES = new Set([408, 429]);

/**
 * A failed poll is polled again when the failure can be temporary: no HTTP status (network error),
 * a server error, a timeout or a rate limit. Other client errors (for example 403 or 404) stop the flow.
 */
export function getDevicePollErrorAction(status: number | undefined): TDevicePollErrorAction {
  if (!status || status >= 500 || RETRY_STATUSES.has(status)) return "retry";
  return "stop";
}

/**
 * Error code of a denied authorization that the user did not refuse, for example wrong App credentials.
 * Returns `null` when the user refused (`access_denied`) or no code is known.
 */
export function getDeniedReasonCode(lastError: string): string | null {
  if (!lastError || lastError === "access_denied") return null;
  return lastError;
}
