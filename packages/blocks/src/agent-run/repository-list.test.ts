/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TAgentGitRepository } from "@plane/types";
import {
  describeRepositoryRow,
  filterRepositories,
  getRepositoryGroupLabel,
  getRepositoryOwners,
  groupRepositories,
} from "./repository-list";

function repo(overrides: Partial<TAgentGitRepository>): TAgentGitRepository {
  return {
    id: "row",
    provider: "github",
    host: "github.com",
    account_id: "acc-1",
    account_login: "plane-mini",
    account_type: "Organization",
    external_id: "1",
    full_name: "plane-mini/api",
    owner_login: "plane-mini",
    private: true,
    default_branch: "main",
    web_url: "https://github.com/plane-mini/api",
    available: true,
    bound_project: null,
    ...overrides,
  };
}

const ROWS: TAgentGitRepository[] = [
  repo({ id: "g2", full_name: "plane-mini/web", external_id: "2" }),
  repo({ id: "g1", full_name: "plane-mini/api" }),
  repo({
    id: "g3",
    account_id: "acc-2",
    account_login: "kevinle128",
    account_type: "User",
    owner_login: "kevinle128",
    full_name: "kevinle128/notes",
    external_id: "3",
  }),
  repo({
    id: "l1",
    provider: "gitlab",
    host: "git.example.com",
    account_id: "acc-3",
    account_login: "platform/tools",
    account_type: "Group",
    owner_login: "platform/tools",
    full_name: "platform/tools/cli",
    external_id: "1",
  }),
];

describe("groupRepositories", () => {
  it("groups by provider (GitHub first) and then by account, with rows sorted by name", () => {
    const groups = groupRepositories(ROWS.toReversed());
    expect(groups.map((group) => group.provider)).toEqual(["github", "gitlab"]);
    expect(groups[0].accounts.map((account) => account.login)).toEqual(["kevinle128", "plane-mini"]);
    expect(groups[0].accounts[1].rows.map((row) => row.id)).toEqual(["g1", "g2"]);
    expect(groups[1].accounts[0]).toMatchObject({ login: "platform/tools", type: "Group" });
  });

  it("returns no group for an empty list", () => {
    expect(groupRepositories([])).toEqual([]);
  });
});

describe("filterRepositories", () => {
  it("matches the search text case-insensitively on owner/name", () => {
    expect(filterRepositories(ROWS, { search: "WEB" }).map((row) => row.id)).toEqual(["g2"]);
    expect(filterRepositories(ROWS, { search: "  plane-mini/ " }).map((row) => row.id)).toEqual(["g2", "g1"]);
  });

  it("filters by owner", () => {
    expect(filterRepositories(ROWS, { owner: "kevinle128" }).map((row) => row.id)).toEqual(["g3"]);
  });

  it("returns every row without filters", () => {
    expect(filterRepositories(ROWS, {})).toHaveLength(4);
  });
});

describe("getRepositoryOwners", () => {
  it("lists each owner once, sorted", () => {
    expect(getRepositoryOwners(ROWS)).toEqual(["kevinle128", "plane-mini", "platform/tools"]);
  });
});

describe("describeRepositoryRow", () => {
  it("marks an available row as selectable and reports the selected state", () => {
    expect(describeRepositoryRow(ROWS[0], "g2")).toEqual({
      selectable: true,
      selected: true,
      availability: "available",
      boundProjectName: null,
    });
    expect(describeRepositoryRow(ROWS[0], null).selected).toBe(false);
  });

  it("marks a repository used by another project as unavailable and never selected", () => {
    const bound = repo({ id: "b", available: false, bound_project: { id: "p", name: "Atlas", identifier: "ATL" } });
    expect(describeRepositoryRow(bound, "b")).toEqual({
      selectable: false,
      selected: false,
      availability: "already_used",
      boundProjectName: "Atlas",
    });
  });
});

describe("getRepositoryGroupLabel", () => {
  it("names the provider in text, so the provider is not shown by the icon alone", () => {
    const groups = groupRepositories(ROWS);
    expect(getRepositoryGroupLabel(groups[0].provider, groups[0].accounts[1])).toBe("GitHub · plane-mini");
    expect(getRepositoryGroupLabel(groups[1].provider, groups[1].accounts[0])).toBe("GitLab · platform/tools");
  });
});
