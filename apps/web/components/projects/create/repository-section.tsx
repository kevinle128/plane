/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useId, useMemo, useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
import { Input } from "@makeplane/propel/components/input";
import { UnlinkOutline } from "@makeplane/propel/icons";
import {
  describeRepositoryRow,
  filterRepositories,
  getRepositoryGroupLabel,
  getRepositoryOwners,
  groupRepositories,
} from "@plane/blocks/agent-run";
import { AGENT_GIT_PROVIDERS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TAgentGitRepository, TAgentGitRepositorySelection } from "@plane/types";
import { cn } from "@plane/utils";
import { AgentGitProviderIcon, agentGitProviderLabel } from "@/components/settings/integrations/git/provider-meta";
import { useAgentGit } from "@/hooks/store/use-agent-git";

const NO_REPOSITORIES: TAgentGitRepository[] = [];

type Props = {
  workspaceSlug: string;
  value: TAgentGitRepositorySelection | null;
  onChange: (value: TAgentGitRepositorySelection | null) => void;
};

function RepositoryRow(props: {
  row: TAgentGitRepository;
  name: string;
  selectedId: string | null;
  onSelect: (row: TAgentGitRepository) => void;
}) {
  const { row, name, selectedId, onSelect } = props;
  const { t } = useTranslation();
  const state = describeRepositoryRow(row, selectedId);
  const availabilityText =
    state.availability === "already_used"
      ? t("agent_git.repository.already_used", { project: state.boundProjectName ?? "" })
      : null;

  return (
    <label
      className={cn("flex items-center gap-3 border border-transparent px-3 py-2", {
        "cursor-pointer hover:bg-layer-1-hover": state.selectable,
        "cursor-not-allowed opacity-70": !state.selectable,
        "border-accent-strong bg-layer-1-selected": state.selected,
      })}
    >
      <input
        type="radio"
        name={name}
        value={row.id}
        checked={state.selected}
        disabled={!state.selectable}
        onChange={() => onSelect(row)}
        className="size-3.5 shrink-0 accent-[var(--bg-accent-primary)]"
      />
      <span className="min-w-0 flex-1 truncate font-code text-body-sm-regular text-primary">{row.full_name}</span>
      <span className="rounded-full bg-layer-1 px-2 py-0.5 text-caption-sm-regular text-secondary">
        {row.private ? t("agent_git.repository.private") : t("agent_git.repository.public")}
      </span>
      {availabilityText && <span className="text-caption-sm-medium text-tertiary">{availabilityText}</span>}
    </label>
  );
}

/** Repository choice in the create-project form: one repository per project, or none. */
export const ProjectRepositorySection = observer(function ProjectRepositorySection(props: Props) {
  const { workspaceSlug, value, onChange } = props;
  const { t } = useTranslation();
  const { fetchConnections, isConnected, fetchRepositories, repositoriesByWorkspace } = useAgentGit();
  const [search, setSearch] = useState("");
  const [owner, setOwner] = useState("");
  const radioName = useId();
  const headingId = useId();

  const { isLoading: isLoadingConnections } = useSWR(`AGENT_GIT_CONNECTIONS_${workspaceSlug}`, () =>
    fetchConnections(workspaceSlug)
  );
  const connectedProviders = AGENT_GIT_PROVIDERS.filter((provider) => isConnected(workspaceSlug, provider));
  const hasConnection = connectedProviders.length > 0;
  const { isLoading: isLoadingRepositories, error } = useSWR(
    hasConnection ? `AGENT_GIT_REPOSITORIES_${workspaceSlug}` : null,
    () => fetchRepositories(workspaceSlug)
  );

  const rows = repositoriesByWorkspace[workspaceSlug] ?? NO_REPOSITORIES;
  const owners = useMemo(() => getRepositoryOwners(rows), [rows]);
  const groups = useMemo(() => groupRepositories(filterRepositories(rows, { search, owner })), [rows, search, owner]);
  const selectedRow = rows.find((row) => row.id === value?.repository_id) ?? null;

  if (isLoadingConnections) return null;

  if (!hasConnection) {
    return (
      <section
        aria-labelledby={headingId}
        className="flex items-start gap-3 rounded-lg border border-dashed border-subtle px-4 py-3"
      >
        <UnlinkOutline className="mt-0.5 size-4 shrink-0 text-tertiary" aria-hidden="true" />
        <div className="flex flex-col gap-1">
          <h4 id={headingId} className="text-body-sm-semibold text-primary">
            {t("agent_git.repository.not_connected_title")}
          </h4>
          <p className="text-caption-sm-regular text-tertiary">{t("agent_git.repository.not_connected_description")}</p>
          <Link
            href={`/${workspaceSlug}/settings/integrations`}
            className="w-fit text-caption-sm-medium text-link-primary hover:underline"
          >
            {t("agent_git.repository.open_integrations")}
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <h4 id={headingId} className="text-body-sm-semibold text-primary">
          {t("agent_git.repository.title")}
        </h4>
        {connectedProviders.map((provider) => (
          <span key={provider} className="flex items-center gap-1 text-caption-sm-regular text-secondary">
            <AgentGitProviderIcon provider={provider} className="size-3.5" />
            {agentGitProviderLabel(provider)}
          </span>
        ))}
        <span className="text-caption-sm-regular text-tertiary">{t("agent_git.repository.description")}</span>
        <Link
          href={`/${workspaceSlug}/settings/integrations`}
          className="ml-auto text-caption-sm-medium text-link-primary hover:underline"
        >
          {t("agent_git.repository.manage_access")}
        </Link>
      </div>
      <div className="flex flex-wrap gap-2">
        <div className="min-w-48 flex-1">
          <Input
            size="md"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("agent_git.repository.search_placeholder")}
            aria-label={t("agent_git.repository.search_label")}
          />
        </div>
        <select
          value={owner}
          onChange={(event) => setOwner(event.target.value)}
          aria-label={t("agent_git.repository.owner_label")}
          className="rounded-md border border-subtle bg-surface-1 px-2 text-body-sm-regular text-primary"
        >
          <option value="">{t("agent_git.repository.all_owners")}</option>
          {owners.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </div>
      <div
        role="radiogroup"
        aria-label={t("agent_git.repository.list_label")}
        className="max-h-60 overflow-y-auto rounded-lg border border-subtle bg-surface-1"
      >
        <label
          className={cn("flex cursor-pointer items-center gap-3 border border-transparent px-3 py-2", {
            "border-accent-strong bg-layer-1-selected": value === null,
          })}
        >
          <input
            type="radio"
            name={radioName}
            value=""
            checked={value === null}
            onChange={() => onChange(null)}
            className="size-3.5 shrink-0 accent-[var(--bg-accent-primary)]"
          />
          <span className="text-body-sm-regular text-secondary">{t("agent_git.repository.none_option")}</span>
        </label>
        {isLoadingRepositories && (
          <p role="status" className="px-3 py-2 text-caption-sm-regular text-tertiary">
            {t("agent_git.repository.loading")}
          </p>
        )}
        {error && (
          <p role="alert" className="px-3 py-2 text-caption-sm-regular text-danger-primary">
            {t("agent_git.repository.load_error")}
          </p>
        )}
        {!isLoadingRepositories && !error && groups.length === 0 && (
          <p className="px-3 py-2 text-caption-sm-regular text-tertiary">{t("agent_git.repository.empty")}</p>
        )}
        {groups.map((group) =>
          group.accounts.map((account) => (
            <div key={account.accountId} role="group" aria-label={getRepositoryGroupLabel(group.provider, account)}>
              <div className="tracking-wider flex items-center gap-1.5 px-3 pt-3 pb-1 text-11 font-semibold text-tertiary uppercase">
                <AgentGitProviderIcon provider={group.provider} className="size-3" />
                {t("agent_git.repository.account_group", {
                  login: getRepositoryGroupLabel(group.provider, account),
                  type: account.type,
                })}
              </div>
              {account.rows.map((row) => (
                <RepositoryRow
                  key={row.id}
                  row={row}
                  name={radioName}
                  selectedId={value?.repository_id ?? null}
                  onSelect={(selected) => onChange({ repository_id: selected.id })}
                />
              ))}
            </div>
          ))
        )}
      </div>
      {value === null && (
        <p role="note" className="text-caption-sm-regular text-tertiary">
          {t("agent_git.repository.none_warning")}
        </p>
      )}
      {selectedRow && value && (
        <div className="flex flex-col gap-1">
          <label htmlFor={`${radioName}-base-ref`} className="text-caption-sm-medium text-secondary">
            {t("agent_git.repository.base_ref_label")}
          </label>
          <div className="max-w-xs font-code">
            <Input
              size="md"
              id={`${radioName}-base-ref`}
              value={value.base_ref ?? ""}
              placeholder={selectedRow.default_branch}
              onChange={(event) =>
                onChange({ repository_id: value.repository_id, base_ref: event.target.value || undefined })
              }
            />
          </div>
          <p className="text-caption-sm-regular text-tertiary">
            {t("agent_git.repository.base_ref_hint", { branch: selectedRow.default_branch })}
          </p>
        </div>
      )}
    </section>
  );
});
