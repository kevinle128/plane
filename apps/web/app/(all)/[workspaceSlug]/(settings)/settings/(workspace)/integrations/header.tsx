/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { WORKSPACE_SETTINGS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Breadcrumbs } from "@plane/blocks/breadcrumb";
import type { TAgentGitProvider } from "@plane/types";
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { agentGitProviderLabel } from "@/components/settings/integrations/git/provider-meta";
import { SettingsPageHeader } from "@/components/settings/page-header";
import { WORKSPACE_SETTINGS_ICONS } from "@/components/settings/workspace/sidebar/item-icon";

/** `provider` names a Git provider page; `title` names any other detail page, for example a Harness. */
type Props = { workspaceSlug: string; provider?: TAgentGitProvider; title?: string };

export const IntegrationsWorkspaceSettingsHeader = observer(function IntegrationsWorkspaceSettingsHeader({
  workspaceSlug,
  provider,
  title,
}: Props) {
  const { t } = useTranslation();
  const settingsDetails = WORKSPACE_SETTINGS.integrations;
  const Icon = WORKSPACE_SETTINGS_ICONS.integrations;
  const detailLabel = provider ? agentGitProviderLabel(provider) : title;

  return (
    <SettingsPageHeader
      leftItem={
        <div className="flex items-center gap-2">
          <Breadcrumbs>
            <Breadcrumbs.Item
              component={
                <BreadcrumbLink
                  label={t(settingsDetails.i18n_label)}
                  href={detailLabel ? `/${workspaceSlug}/settings/integrations` : undefined}
                  icon={<Icon className="size-4 text-tertiary" />}
                />
              }
            />
            {detailLabel && <Breadcrumbs.Item component={<BreadcrumbLink label={detailLabel} />} />}
          </Breadcrumbs>
        </div>
      }
    />
  );
});
