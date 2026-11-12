/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getChangeRequestTerm, getPolicyLabelKey, POLICY_LABEL_FIELDS } from "./provider-terms";

describe("getChangeRequestTerm", () => {
  it("uses pull request for GitHub and merge request for GitLab", () => {
    expect(getChangeRequestTerm("github")).toBe("pull_request");
    expect(getChangeRequestTerm("gitlab")).toBe("merge_request");
  });
});

describe("getPolicyLabelKey", () => {
  it.each(POLICY_LABEL_FIELDS)("gives a provider-specific key for %s", (field) => {
    expect(getPolicyLabelKey(field, "github")).toBe(`agent_git.policy.${field}.pull_request`);
    expect(getPolicyLabelKey(field, "gitlab")).toBe(`agent_git.policy.${field}.merge_request`);
  });

  it("covers every policy label of the detail page", () => {
    expect(POLICY_LABEL_FIELDS).toEqual([
      "title",
      "description",
      "open_as_draft",
      "open_as_draft_hint",
      "mirror_conclusions",
      "mirror_conclusions_hint",
    ]);
  });
});
