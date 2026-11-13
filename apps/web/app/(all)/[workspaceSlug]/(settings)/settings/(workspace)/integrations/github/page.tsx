/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { PageHead } from "@/components/core/page-title";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { GitProviderDetailPage } from "@/components/settings/integrations/git/detail-page";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserPermissions } from "@/hooks/store/user";
import type { Route } from "./+types/page";
import { IntegrationsWorkspaceSettingsHeader } from "../header";

function GithubIntegrationPage({ params }: Route.ComponentProps) {
  const { workspaceSlug } = params;
  const { currentWorkspace } = useWorkspace();
  const { allowPermissions } = useUserPermissions();
  const canEdit = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE);
  const pageTitle = currentWorkspace?.name ? `${currentWorkspace.name} - GitHub` : undefined;

  return (
    <SettingsContentWrapper
      header={<IntegrationsWorkspaceSettingsHeader workspaceSlug={workspaceSlug} provider="github" />}
    >
      <PageHead title={pageTitle} />
      <GitProviderDetailPage workspaceSlug={workspaceSlug} provider="github" canEdit={canEdit} />
    </SettingsContentWrapper>
  );
}

export default observer(GithubIntegrationPage);
