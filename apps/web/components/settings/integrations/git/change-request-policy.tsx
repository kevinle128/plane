/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useId, useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { Switch } from "@makeplane/propel/components/switch";
import { setToast } from "@plane/blocks/toast";
import { AGENT_GIT_BRANCH_FORMATS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TAgentGitPolicy, TAgentGitProvider } from "@plane/types";
import { useAgentGit } from "@/hooks/store/use-agent-git";

type Props = {
  workspaceSlug: string;
  provider: TAgentGitProvider;
  canEdit: boolean;
};

type TPolicyChange = Partial<Omit<TAgentGitPolicy, "provider">>;

function SwitchRow(props: {
  label: string;
  hint: string;
  checked: boolean;
  disabled: boolean;
  onChange: (checked: boolean) => void;
}) {
  const { label, hint, checked, disabled, onChange } = props;
  const labelId = useId();
  const hintId = useId();
  return (
    <li className="flex flex-wrap items-center gap-3 border-b border-subtle px-4 py-3 last:border-b-0">
      <span className="flex min-w-45 flex-1 flex-col">
        <span id={labelId} className="text-body-sm-medium text-primary">
          {label}
        </span>
        <span id={hintId} className="text-caption-sm-regular text-tertiary">
          {hint}
        </span>
      </span>
      <Switch
        size="sm"
        checked={checked}
        disabled={disabled}
        aria-labelledby={labelId}
        aria-describedby={hintId}
        onCheckedChange={onChange}
      />
    </li>
  );
}

function BranchFormatRow(props: {
  label: string;
  hint: string;
  value: TAgentGitPolicy["branch_format"];
  disabled: boolean;
  onChange: (value: TAgentGitPolicy["branch_format"]) => void;
}) {
  const { label, hint, value, disabled, onChange } = props;
  const selectId = useId();
  const hintId = useId();
  return (
    <li className="flex flex-wrap items-center gap-3 border-b border-subtle px-4 py-3 last:border-b-0">
      <span className="flex min-w-45 flex-1 flex-col">
        <label htmlFor={selectId} className="text-body-sm-medium text-primary">
          {label}
        </label>
        <span id={hintId} className="text-caption-sm-regular text-tertiary">
          {hint}
        </span>
      </span>
      <select
        id={selectId}
        value={value}
        disabled={disabled}
        aria-describedby={hintId}
        onChange={(event) => onChange(event.target.value as TAgentGitPolicy["branch_format"])}
        className="max-w-full min-w-50 rounded-md border border-subtle bg-surface-1 px-2 py-1 font-code text-caption-sm-regular text-primary disabled:cursor-not-allowed disabled:text-tertiary"
      >
        {AGENT_GIT_BRANCH_FORMATS.map((format) => (
          <option key={format.key} value={format.key}>
            {format.label}
          </option>
        ))}
      </select>
    </li>
  );
}

/** Change-request defaults of one provider. Members see the values; only admins change them. */
export const GitChangeRequestPolicy = observer(function GitChangeRequestPolicy(props: Props) {
  const { workspaceSlug, provider, canEdit } = props;
  const { t } = useTranslation();
  const { fetchPolicy, getPolicy, updatePolicy } = useAgentGit();
  const [isSaving, setIsSaving] = useState(false);
  useSWR(`AGENT_GIT_POLICY_${workspaceSlug}_${provider}`, () => fetchPolicy(workspaceSlug, provider));
  const policy = getPolicy(workspaceSlug, provider);
  const term = "pull_request";

  const save = async (change: TPolicyChange) => {
    setIsSaving(true);
    try {
      await updatePolicy(workspaceSlug, provider, change);
      setToast({ type: "success", title: t("agent_git.policy.saved") });
    } catch {
      setToast({ type: "error", title: t("agent_git.policy.save_failed") });
    } finally {
      setIsSaving(false);
    }
  };

  if (!policy) return null;
  const disabled = !canEdit || isSaving;

  return (
    <section className="flex flex-col gap-3" aria-labelledby="agent-git-policy-title">
      <div className="flex flex-col gap-1">
        <h4 id="agent-git-policy-title" className="text-body-sm-semibold text-primary">
          {t(`agent_git.policy.title.${term}`)}
        </h4>
        <p className="text-caption-sm-regular text-tertiary">{t(`agent_git.policy.description.${term}`)}</p>
        {!canEdit && <p className="text-caption-sm-regular text-tertiary">{t("agent_git.integrations.read_only")}</p>}
      </div>
      <ul className="rounded-lg border border-subtle bg-surface-1">
        <SwitchRow
          label={t(`agent_git.policy.open_as_draft.${term}`)}
          hint={t(`agent_git.policy.open_as_draft_hint.${term}`)}
          checked={policy.open_as_draft}
          disabled={disabled}
          onChange={(checked) => void save({ open_as_draft: checked })}
        />
        <SwitchRow
          label={t(`agent_git.policy.mirror_conclusions.${term}`)}
          hint={t(`agent_git.policy.mirror_conclusions_hint.${term}`)}
          checked={policy.mirror_conclusions}
          disabled={disabled}
          onChange={(checked) => void save({ mirror_conclusions: checked })}
        />
        <BranchFormatRow
          label={t("agent_git.policy.branch_format")}
          hint={t("agent_git.policy.branch_format_hint")}
          value={policy.branch_format}
          disabled={disabled}
          onChange={(branchFormat) => void save({ branch_format: branchFormat })}
        />
      </ul>
    </section>
  );
});
