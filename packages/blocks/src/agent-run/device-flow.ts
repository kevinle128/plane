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

/** Time left before a GitHub device code expires, for the "expires in" label. */
export function getDeviceCodeExpiry(expiresAt: string, now: number = Date.now()): TDeviceCodeExpiry {
  const expiresAtMs = Date.parse(expiresAt);
  const remainingMs = Number.isNaN(expiresAtMs) ? 0 : expiresAtMs - now;
  const secondsLeft = remainingMs > 0 ? Math.ceil(remainingMs / 1000) : 0;
  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  return {
    expired: secondsLeft === 0,
    secondsLeft,
    label: `${minutes}:${String(seconds).padStart(2, "0")}`,
  };
}
