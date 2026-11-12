/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Button } from "@makeplane/propel/components/button";
import { InputField } from "@makeplane/propel/components/input-field";
import { TextAreaField } from "@makeplane/propel/components/text-area-field";
import { useTranslation } from "@plane/i18n";
import { useAgentGit } from "@/hooks/store/use-agent-git";
import { agentGitErrorMessage } from "../provider-meta";

type Props = { workspaceSlug: string };

/** GitLab connect form. The token is sent once; the API never returns it. */
export const GitlabTokenForm = observer(function GitlabTokenForm({ workspaceSlug }: Props) {
  const { t } = useTranslation();
  const { connectGitlab } = useAgentGit();
  const [baseUrl, setBaseUrl] = useState("");
  const [groupPath, setGroupPath] = useState("");
  const [token, setToken] = useState("");
  const [caBundle, setCaBundle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const canSubmit = Boolean(baseUrl.trim() && groupPath.trim() && token.trim()) && !isSubmitting;

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await connectGitlab(workspaceSlug, {
        base_url: baseUrl.trim(),
        group_path: groupPath.trim(),
        token: token.trim(),
        ...(caBundle.trim() ? { ca_bundle: caBundle } : {}),
      });
      setToken("");
    } catch (connectError) {
      setError(agentGitErrorMessage(t, connectError));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="flex w-full max-w-xl flex-col gap-4 text-left">
      <InputField
        size="lg"
        orientation="vertical"
        type="url"
        name="gitlab-base-url"
        label={t("agent_git.gitlab.setup.base_url_label")}
        hint={t("agent_git.gitlab.setup.base_url_hint")}
        placeholder="https://gitlab.example.com"
        required
        value={baseUrl}
        onChange={(event) => setBaseUrl(event.target.value)}
      />
      <InputField
        size="lg"
        orientation="vertical"
        name="gitlab-group-path"
        label={t("agent_git.gitlab.setup.group_label")}
        hint={t("agent_git.gitlab.setup.group_hint")}
        placeholder="platform"
        required
        value={groupPath}
        onChange={(event) => setGroupPath(event.target.value)}
      />
      <InputField
        size="lg"
        orientation="vertical"
        type="password"
        name="gitlab-token"
        autoComplete="off"
        label={t("agent_git.gitlab.setup.token_label")}
        hint={t("agent_git.gitlab.setup.token_hint")}
        required
        value={token}
        onChange={(event) => setToken(event.target.value)}
      />
      <TextAreaField
        size="lg"
        resize="vertical"
        name="gitlab-ca-bundle"
        label={t("agent_git.gitlab.setup.ca_label")}
        hint={t("agent_git.gitlab.setup.ca_hint")}
        placeholder="-----BEGIN CERTIFICATE-----"
        value={caBundle}
        onChange={(event) => setCaBundle(event.target.value)}
      />
      {error && (
        <p role="alert" className="text-caption-sm-regular text-danger-primary">
          {error}
        </p>
      )}
      <div>
        <Button
          type="submit"
          variant="primary"
          size="lg"
          stretch="auto"
          disabled={!canSubmit}
          loading={isSubmitting}
          label={isSubmitting ? t("agent_git.gitlab.setup.connecting") : t("agent_git.gitlab.setup.connect")}
        />
      </div>
    </form>
  );
});
