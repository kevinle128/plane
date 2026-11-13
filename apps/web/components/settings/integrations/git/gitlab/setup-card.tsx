/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { AgentGitProviderIcon } from "../provider-meta";
import { GitlabTokenForm } from "./token-form";

type Props = { workspaceSlug: string; canEdit: boolean };

/** Disconnected GitLab state: the same card as GitHub, with the token form in place of the device code. */
export function GitlabSetupCard({ workspaceSlug, canEdit }: Props) {
  const { t } = useTranslation();
  return (
    <section className="flex flex-col items-center gap-4 rounded-lg border border-subtle bg-surface-1 px-6 py-8 text-center">
      <span className="flex size-8 items-center justify-center rounded-full bg-layer-1">
        <AgentGitProviderIcon provider="gitlab" className="size-5" />
      </span>
      <div className="flex flex-col gap-1">
        <h4 className="text-body-md-semibold text-primary">{t("agent_git.gitlab.setup.title")}</h4>
        <p className="max-w-[620px] text-body-xs-regular text-tertiary">{t("agent_git.gitlab.setup.description")}</p>
      </div>
      {canEdit ? (
        <GitlabTokenForm workspaceSlug={workspaceSlug} />
      ) : (
        <p className="text-caption-sm-regular text-tertiary">{t("agent_git.integrations.read_only")}</p>
      )}
    </section>
  );
}
