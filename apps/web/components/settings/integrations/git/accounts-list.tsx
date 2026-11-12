/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR, { mutate } from "swr";
import { AnchorButton } from "@makeplane/propel/components/anchor-button";
import { Button } from "@makeplane/propel/components/button";
import { getAccountTypeLabelKey, isReconnectErrorCode } from "@plane/blocks/agent-run";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TAgentGitAccount, TAgentGitAccountRemoval, TAgentGitConnection, TAgentGitError } from "@plane/types";
import { useAgentGit } from "@/hooks/store/use-agent-git";
import { agentGitConnectionsKey, agentGitErrorMessage } from "./provider-meta";

type Props = {
  workspaceSlug: string;
  connection: TAgentGitConnection;
  canEdit: boolean;
};

function initials(login: string) {
  return login.slice(0, 2).toUpperCase();
}

function AccountRow(props: {
  account: TAgentGitAccount;
  canEdit: boolean;
  isBusy: boolean;
  onAttach: (account: TAgentGitAccount) => void;
  onRemove: (account: TAgentGitAccount) => void;
}) {
  const { account, canEdit, isBusy, onAttach, onRemove } = props;
  const { t } = useTranslation();
  const isAttached = account.state === "attached";
  const typeLabel = t(getAccountTypeLabelKey(account.account_type));
  const selectionLabel =
    account.repository_selection === "selected"
      ? t("agent_git.accounts.selected_repositories")
      : t("agent_git.accounts.all_repositories");

  return (
    <li className="flex flex-wrap items-center gap-3 border-b border-subtle px-4 py-3 last:border-b-0">
      <span
        aria-hidden="true"
        className="flex size-8 shrink-0 items-center justify-center rounded-md bg-layer-1 text-caption-sm-medium text-secondary"
      >
        {initials(account.login)}
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="truncate font-code text-body-sm-medium text-primary">{account.login}</span>
        <span className="text-caption-sm-regular text-tertiary">
          {typeLabel} · {selectionLabel}
        </span>
      </span>
      {isAttached ? (
        <span className="flex items-center gap-1.5 text-caption-sm-medium text-success-primary">
          <span aria-hidden="true" className="size-1.5 rounded-full bg-success-primary" />
          {t("agent_git.accounts.attached")}
        </span>
      ) : (
        <span className="text-caption-sm-medium text-tertiary">{t("agent_git.accounts.candidate")}</span>
      )}
      {canEdit && isAttached && account.provider === "github" && (
        <Button
          variant="tertiary"
          size="sm"
          stretch="auto"
          label={t("agent_git.accounts.remove")}
          aria-label={`${t("agent_git.accounts.remove")} ${account.login}`}
          disabled={isBusy}
          onClick={() => onRemove(account)}
        />
      )}
      {canEdit && !isAttached && (
        <Button
          variant="secondary"
          size="sm"
          stretch="auto"
          label={t("agent_git.accounts.attach")}
          aria-label={`${t("agent_git.accounts.attach")} ${account.login}`}
          disabled={isBusy}
          onClick={() => onAttach(account)}
        />
      )}
    </li>
  );
}

/** Installations of the GitHub connection: attach candidates, connect an organisation, refresh. */
export const GitAccountsList = observer(function GitAccountsList({ workspaceSlug, connection, canEdit }: Props) {
  const { t } = useTranslation();
  const { fetchAccounts, getAccounts, syncGithubAccounts, attachAccount, removeAccount } = useAgentGit();
  const [isBusy, setIsBusy] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<TAgentGitAccount | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);
  const [lastRemoval, setLastRemoval] = useState<TAgentGitAccountRemoval | null>(null);
  useSWR(`AGENT_GIT_ACCOUNTS_${workspaceSlug}_${connection.provider}`, () =>
    fetchAccounts(workspaceSlug, connection.provider)
  );
  // Removed installations are not offered; they stay removed until an admin attaches them again.
  const accounts = (getAccounts(workspaceSlug, connection.provider) ?? []).filter(
    (account) => account.state !== "detached"
  );

  const showError = (error: unknown) => {
    setToast({ type: "error", title: agentGitErrorMessage(t, error) });
    // The provider no longer accepts the token: reload the connection so the page shows the reconnect state.
    if (isReconnectErrorCode((error as TAgentGitError | undefined)?.error))
      void mutate(agentGitConnectionsKey(workspaceSlug));
  };

  const run = async (action: () => Promise<unknown>, successMessage: string) => {
    setIsBusy(true);
    try {
      await action();
      setToast({ type: "success", title: successMessage });
    } catch (error) {
      showError(error);
    } finally {
      setIsBusy(false);
    }
  };

  const handleRefresh = () => run(() => syncGithubAccounts(workspaceSlug), t("agent_git.accounts.synced"));
  const handleAttach = (account: TAgentGitAccount) =>
    void run(
      () => attachAccount(workspaceSlug, connection.provider, account.id),
      t("agent_git.accounts.attached_toast", { name: account.login })
    );

  const handleRemove = async () => {
    if (!removeTarget) return;
    setIsRemoving(true);
    try {
      const removal = await removeAccount(workspaceSlug, connection.provider, removeTarget.id);
      setLastRemoval(removal);
      setRemoveTarget(null);
    } catch (error) {
      // The installation stays visible: the store changes only after a successful response.
      showError(error);
    } finally {
      setIsRemoving(false);
    }
  };

  return (
    <section className="flex flex-col gap-3" aria-labelledby="agent-git-accounts-title">
      <ConfirmDialog
        isOpen={removeTarget !== null}
        variant="danger"
        title={t("agent_git.accounts.remove_confirm_title", { name: removeTarget?.login ?? "" })}
        content={t("agent_git.accounts.remove_confirm_content", { name: removeTarget?.login ?? "" })}
        handleClose={() => setRemoveTarget(null)}
        handleSubmit={handleRemove}
        isSubmitting={isRemoving}
        primaryButtonText={{ default: t("agent_git.accounts.remove"), loading: t("agent_git.accounts.removing") }}
      />
      <div className="flex flex-wrap items-center gap-2">
        <h4 id="agent-git-accounts-title" className="flex-1 text-body-sm-semibold text-primary">
          {t("agent_git.accounts.title")}
        </h4>
        {canEdit && connection.provider === "github" && (
          <>
            <Button
              variant="tertiary"
              size="sm"
              stretch="auto"
              label={t("agent_git.accounts.refresh")}
              loading={isBusy}
              onClick={() => void handleRefresh()}
            />
            {connection.install_url && (
              <AnchorButton
                variant="secondary"
                size="sm"
                href={connection.install_url}
                external
                label={t("agent_git.accounts.connect_organization")}
              />
            )}
          </>
        )}
      </div>
      {canEdit && connection.provider === "github" && (
        <p className="text-caption-sm-regular text-tertiary">{t("agent_git.accounts.connect_organization_hint")}</p>
      )}
      {lastRemoval && (
        <div
          role="status"
          className="flex flex-wrap items-center gap-2 rounded-md border border-subtle bg-layer-1 px-3 py-2 text-caption-sm-regular text-secondary"
        >
          <span className="flex-1">
            {t("agent_git.accounts.removed", { name: lastRemoval.login })} {t("agent_git.accounts.removed_hint")}
          </span>
          <AnchorButton
            variant="secondary"
            size="sm"
            href={lastRemoval.settings_url}
            external
            label={t("agent_git.accounts.open_settings")}
          />
        </div>
      )}
      <ul className="rounded-lg border border-subtle bg-surface-1">
        {accounts.length === 0 && (
          <li className="px-4 py-3 text-caption-sm-regular text-tertiary">{t("agent_git.accounts.empty")}</li>
        )}
        {accounts.map((account) => (
          <AccountRow
            key={account.id}
            account={account}
            canEdit={canEdit}
            isBusy={isBusy}
            onAttach={handleAttach}
            onRemove={setRemoveTarget}
          />
        ))}
        {connection.provider === "github" && (
          <li className="flex flex-wrap items-center gap-3 px-4 py-3">
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="text-body-sm-medium text-primary">{t("agent_git.accounts.personal_title")}</span>
              <span className="text-caption-sm-regular text-tertiary">{t("agent_git.accounts.personal_hint")}</span>
            </span>
            <span className="font-code text-caption-sm-regular text-secondary">{connection.account_login}</span>
          </li>
        )}
      </ul>
    </section>
  );
});
