/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TAgentGitProvider } from "@plane/types";
import { getAccountTypeLabelKey, getChangeRequestTerm, getPolicyLabelKey, POLICY_LABEL_FIELDS } from "./provider-terms";

const PROVIDERS: TAgentGitProvider[] = ["github", "gitlab"];
// A non-literal specifier keeps the locale file out of the type-checked project; Vitest loads it.
const EN_AGENT_LOCALE = new URL("../../../i18n/src/locales/en/agent.json", import.meta.url).href;

async function loadEnglishKeys(): Promise<Set<string>> {
  const module = (await import(/* @vite-ignore */ EN_AGENT_LOCALE)) as { default: Record<string, unknown> };
  const keys = new Set<string>();
  const walk = (node: unknown, path: string[]) => {
    if (node && typeof node === "object") {
      for (const [key, value] of Object.entries(node)) walk(value, [...path, key]);
    } else {
      keys.add(path.join("."));
    }
  };
  walk(module.default, []);
  return keys;
}

describe("getChangeRequestTerm", () => {
  it("uses pull request for GitHub and merge request for GitLab", () => {
    expect(getChangeRequestTerm("github")).toBe("pull_request");
    expect(getChangeRequestTerm("gitlab")).toBe("merge_request");
  });
});

describe("getPolicyLabelKey", () => {
  it("gives a key that exists in the English locale for every field and provider", async () => {
    const keys = await loadEnglishKeys();
    const missing = POLICY_LABEL_FIELDS.flatMap((field) =>
      PROVIDERS.map((provider) => getPolicyLabelKey(field, provider))
    ).filter((key) => !keys.has(key));
    expect(missing).toEqual([]);
  });
});

describe("getAccountTypeLabelKey", () => {
  it("maps each provider account type to its label key", () => {
    expect(getAccountTypeLabelKey("Organization")).toBe("agent_git.accounts.organization");
    expect(getAccountTypeLabelKey("Group")).toBe("agent_git.accounts.group");
    expect(getAccountTypeLabelKey("User")).toBe("agent_git.accounts.user");
  });

  it("uses the account label for an unknown type", () => {
    expect(getAccountTypeLabelKey("Enterprise")).toBe("agent_git.accounts.user");
  });

  it("gives keys that exist in the English locale", async () => {
    const keys = await loadEnglishKeys();
    for (const type of ["Organization", "Group", "User"]) expect(keys.has(getAccountTypeLabelKey(type))).toBe(true);
  });
});
