/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { AGENT_HARNESSES, AGENT_HARNESS_LABELS, EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TAgentHarness } from "@plane/types";
import { PageHead } from "@/components/core/page-title";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { HarnessDetailPage } from "@/components/settings/integrations/harness/harness-detail-page";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserPermissions } from "@/hooks/store/user";
import type { Route } from "./+types/page";
import { IntegrationsWorkspaceSettingsHeader } from "../header";

const isHarness = (value: string): value is TAgentHarness => (AGENT_HARNESSES as string[]).includes(value);

function HarnessIntegrationPage({ params }: Route.ComponentProps) {
  const { workspaceSlug, harness } = params;
  const { t } = useTranslation();
  const { currentWorkspace } = useWorkspace();
  const { allowPermissions } = useUserPermissions();
  const canEdit = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE);
  const label = isHarness(harness) ? AGENT_HARNESS_LABELS[harness] : undefined;
  const pageTitle = currentWorkspace?.name && label ? `${currentWorkspace.name} - ${label}` : undefined;

  return (
    <SettingsContentWrapper
      header={<IntegrationsWorkspaceSettingsHeader workspaceSlug={workspaceSlug} title={label} />}
    >
      <PageHead title={pageTitle} />
      {isHarness(harness) ? (
        <HarnessDetailPage workspaceSlug={workspaceSlug} harness={harness} canEdit={canEdit} />
      ) : (
        <p className="text-body-sm-regular text-tertiary">{t("agent_settings.detail.not_found")}</p>
      )}
    </SettingsContentWrapper>
  );
}

export default observer(HarnessIntegrationPage);
