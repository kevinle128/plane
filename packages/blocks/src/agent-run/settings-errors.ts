/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgentSettingsError, TAgentSettingsField } from "@plane/types";

type TTranslate = (key: string) => string;

/**
 * Translated message of a field error, or `null` when the field has no error. A code without a
 * translation shows the API message (`t` gives the key back for a missing key).
 */
export function getFieldErrorMessage(
  t: TTranslate,
  error: TAgentSettingsError | null,
  field: TAgentSettingsField
): string | null {
  const messages = error?.[field];
  if (!messages?.length) return null;
  const code = error?.codes?.[field];
  if (code) {
    const key = `agent_settings.errors.${field}_${code}`;
    const message = t(key);
    if (message && message !== key) return message;
  }
  return messages[0];
}

/** The error without the messages and the code of one field; the same value when that field has no error. */
export function clearFieldError(
  error: TAgentSettingsError | null,
  field: TAgentSettingsField
): TAgentSettingsError | null {
  if (!error || (error[field] === undefined && error.codes?.[field] === undefined)) return error;
  const { [field]: _messages, codes, ...rest } = error;
  const { [field]: _code, ...otherCodes } = codes ?? {};
  return codes ? { ...rest, codes: otherCodes } : rest;
}
