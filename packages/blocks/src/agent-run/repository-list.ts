/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAgentGitProvider, TAgentGitRepository } from "@plane/types";

const PROVIDER_ORDER: TAgentGitProvider[] = ["github", "gitlab"];

export type TRepositoryAccountGroup = {
  accountId: string;
  login: string;
  type: string;
  rows: TAgentGitRepository[];
};

export type TRepositoryProviderGroup = {
  provider: TAgentGitProvider;
  accounts: TRepositoryAccountGroup[];
};

export type TRepositoryFilters = {
  search?: string;
  owner?: string | null;
};

export type TRepositoryRowState = {
  selectable: boolean;
  selected: boolean;
  availability: "available" | "already_used";
  boundProjectName: string | null;
};

const byText = (a: string, b: string) => a.localeCompare(b);

/** Keep the rows whose owner matches and whose `owner/name` contains the search text. */
export function filterRepositories(rows: TAgentGitRepository[], filters: TRepositoryFilters): TAgentGitRepository[] {
  const search = (filters.search ?? "").trim().toLowerCase();
  return rows.filter(
    (row) =>
      (!filters.owner || row.owner_login === filters.owner) && (!search || row.full_name.toLowerCase().includes(search))
  );
}

/** Group rows by provider (GitHub, then GitLab) and then by account, sorted by name. */
export function groupRepositories(rows: TAgentGitRepository[]): TRepositoryProviderGroup[] {
  return PROVIDER_ORDER.map((provider) => {
    const accounts = new Map<string, TRepositoryAccountGroup>();
    for (const row of rows) {
      if (row.provider !== provider) continue;
      const group = accounts.get(row.account_id) ?? {
        accountId: row.account_id,
        login: row.account_login,
        type: row.account_type,
        rows: [],
      };
      group.rows.push(row);
      accounts.set(row.account_id, group);
    }
    const sorted = [...accounts.values()].toSorted((a, b) => byText(a.login, b.login));
    for (const group of sorted) group.rows = group.rows.toSorted((a, b) => byText(a.full_name, b.full_name));
    return { provider, accounts: sorted };
  }).filter((group) => group.accounts.length > 0);
}

/** Unique owners for the owner filter, sorted. */
export function getRepositoryOwners(rows: TAgentGitRepository[]): string[] {
  return [...new Set(rows.map((row) => row.owner_login))].toSorted(byText);
}

/** Selection and availability of one row; a repository used by another project is never selectable. */
export function describeRepositoryRow(row: TAgentGitRepository, selectedId: string | null): TRepositoryRowState {
  const usedElsewhere = !row.available;
  return {
    selectable: !usedElsewhere,
    selected: !usedElsewhere && row.id === selectedId,
    availability: usedElsewhere ? "already_used" : "available",
    boundProjectName: row.bound_project?.name ?? null,
  };
}
