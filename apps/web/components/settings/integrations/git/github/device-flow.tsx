/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { observer } from "mobx-react";
import { Button } from "@makeplane/propel/components/button";
import { getDeviceCodeDeadline, getDeviceCodeExpiry, getDevicePollErrorAction } from "@plane/blocks/agent-run";
import { Spinner } from "@plane/blocks/spinner";
import { useTranslation } from "@plane/i18n";
import type {
  TAgentGitError,
  TAgentGithubDeviceAuthorization,
  TAgentGithubDeviceAuthorizationStatus,
} from "@plane/types";
import { useAgentGit } from "@/hooks/store/use-agent-git";
import { agentGitErrorMessage } from "../provider-meta";

/** Final state of the device flow. `failed` means a poll error that another poll cannot fix. */
export type TDeviceFlowOutcome = Exclude<TAgentGithubDeviceAuthorizationStatus, "pending"> | "failed";

type Props = {
  workspaceSlug: string;
  authorization: TAgentGithubDeviceAuthorization;
  /** Local time when the start response arrived; the countdown starts from it. */
  receivedAt: number;
  /** `authorization` is the last state from the server; `message` is set for the `failed` outcome. */
  onSettled: (outcome: TDeviceFlowOutcome, authorization: TAgentGithubDeviceAuthorization, message?: string) => void;
};

/**
 * The device code card: shows the code and polls GitHub at the interval it asked for. The poll status
 * from the server decides when the flow ends; the countdown is for display only.
 */
export const GithubDeviceFlowCard = observer(function GithubDeviceFlowCard(props: Props) {
  const { workspaceSlug, authorization: initial, receivedAt, onSettled } = props;
  const { t } = useTranslation();
  const { pollGithubDeviceAuthorization, cancelGithubDeviceAuthorization } = useAgentGit();
  const [authorization, setAuthorization] = useState(initial);
  const [deadline] = useState(() => getDeviceCodeDeadline(initial, receivedAt));
  const [now, setNow] = useState(() => Date.now());
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Changes after a poll fails with a temporary error, so the poll timer starts again.
  const [retryCount, setRetryCount] = useState(0);
  const settledRef = useRef(false);
  const expiry = getDeviceCodeExpiry(deadline, now);

  const settle = useCallback(
    (outcome: TDeviceFlowOutcome, last: TAgentGithubDeviceAuthorization, message?: string) => {
      if (settledRef.current) return;
      settledRef.current = true;
      onSettled(outcome, last, message);
    },
    [onSettled]
  );

  const poll = useCallback(async () => {
    if (settledRef.current) return;
    try {
      const next = await pollGithubDeviceAuthorization(workspaceSlug, authorization.id);
      setError(null);
      setAuthorization(next);
      if (next.status !== "pending") settle(next.status, next);
    } catch (pollError) {
      const message = agentGitErrorMessage(t, pollError);
      if (getDevicePollErrorAction((pollError as TAgentGitError | undefined)?.status) === "stop") {
        settle("failed", authorization, message);
        return;
      }
      setError(message);
      setRetryCount((count) => count + 1);
    }
  }, [authorization, pollGithubDeviceAuthorization, settle, t, workspaceSlug]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void poll(), Math.max(authorization.interval, 1) * 1000);
    return () => window.clearTimeout(timer);
  }, [authorization, poll, retryCount]);

  const handleEntered = async () => {
    setIsBusy(true);
    await poll();
    setIsBusy(false);
  };

  const handleCancel = async () => {
    setIsBusy(true);
    try {
      const cancelled = await cancelGithubDeviceAuthorization(workspaceSlug, authorization.id);
      settle("cancelled", cancelled);
    } catch (cancelError) {
      setError(agentGitErrorMessage(t, cancelError));
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <section
      aria-label={t("agent_git.github.device.region_label")}
      className="flex flex-col gap-4 rounded-lg border border-subtle bg-surface-1 px-6 py-6"
    >
      <div className="flex items-center gap-2" role="status" aria-live="polite">
        <Spinner height="14px" width="14px" />
        <span className="text-body-sm-semibold text-primary">{t("agent_git.github.device.waiting")}</span>
        <span className="ml-auto font-code text-caption-sm-regular text-tertiary">
          {t("agent_git.github.device.expires_in", { time: expiry.label })}
        </span>
      </div>
      {error && (
        <p role="alert" className="text-caption-sm-regular text-danger-primary">
          {error}
        </p>
      )}
      <p className="text-body-sm-regular text-secondary">
        {t("agent_git.github.device.instructions", { url: authorization.verification_uri })}
      </p>
      <div className="flex flex-col gap-1">
        <span id="agent-github-device-code-label" className="text-caption-sm-medium text-tertiary">
          {t("agent_git.github.device.code_label")}
        </span>
        <output
          aria-labelledby="agent-github-device-code-label"
          className="w-fit rounded-md border border-subtle bg-layer-1 px-4 py-2 font-code text-h5-medium tracking-[0.18em] text-primary select-all"
        >
          {authorization.user_code}
        </output>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <a
          href={authorization.verification_uri}
          target="_blank"
          rel="noopener noreferrer"
          className="text-body-sm-medium text-link-primary underline-offset-2 hover:underline"
        >
          {t("agent_git.github.device.open_url")}
        </a>
        <Button
          variant="primary"
          size="md"
          stretch="auto"
          label={t("agent_git.github.device.entered")}
          loading={isBusy}
          onClick={() => void handleEntered()}
        />
        <Button
          variant="tertiary"
          size="md"
          stretch="auto"
          label={t("agent_git.github.device.cancel")}
          disabled={isBusy}
          onClick={() => void handleCancel()}
        />
      </div>
    </section>
  );
});
