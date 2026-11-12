/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { PageHead } from "@/components/core/page-title";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { IntegrationsIndexPage } from "@/components/settings/integrations/index-page";
import { useWorkspace } from "@/hooks/store/use-workspace";
import type { Route } from "./+types/page";
import { IntegrationsWorkspaceSettingsHeader } from "./header";

/** Workspace members can read Integrations; changes are limited to admins on each provider page. */
function WorkspaceIntegrationsPage({ params }: Route.ComponentProps) {
  const { workspaceSlug } = params;
  const { t } = useTranslation();
  const { currentWorkspace } = useWorkspace();
  const pageTitle = currentWorkspace?.name
    ? `${currentWorkspace.name} - ${t("workspace_settings.settings.integrations.title")}`
    : undefined;

  return (
    <SettingsContentWrapper header={<IntegrationsWorkspaceSettingsHeader workspaceSlug={workspaceSlug} />}>
      <PageHead title={pageTitle} />
      <IntegrationsIndexPage workspaceSlug={workspaceSlug} />
    </SettingsContentWrapper>
  );
}

export default observer(WorkspaceIntegrationsPage);
