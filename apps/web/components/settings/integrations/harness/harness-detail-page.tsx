/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useId, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { Button } from "@makeplane/propel/components/button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { Switch } from "@makeplane/propel/components/switch";
import { TextArea } from "@makeplane/propel/components/text-area";
import { AgentOutline, ArrowNarrowLeftOutline } from "@makeplane/propel/icons";
import {
  agentSettingsFormOf,
  canSelectModel,
  changesOf,
  clearFieldError,
  getFieldErrorMessage,
  mergeServerAgent,
  type TAgentSettingsDraft,
} from "@plane/blocks/agent-run";
import { setToast } from "@plane/blocks/toast";
import { AGENT_HARNESSES, AGENT_HARNESS_LABELS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TAgent, TAgentHarness, TAgentSettingsError } from "@plane/types";
import { cn } from "@plane/utils";
import { SettingsHeading } from "@/components/settings/heading";
import { useAgent } from "@/hooks/store/use-agent";
import { HarnessConnectionRow, HarnessStatusTag } from "./connection-row";
import type { TAgentCardAction, TRunCardAction } from "./connection-row";
import { harnessCliLabel } from "./harness-card";
import { HarnessModelSelect } from "./model-select";
import { AgentsLoadError, useWorkspaceAgents } from "./workspace-agents";

type Props = {
  workspaceSlug: string;
  harness: TAgentHarness;
  canEdit: boolean;
};

const MAX_INSTRUCTIONS_LENGTH = 10000;

function SettingRow(props: {
  label: string;
  hint: string;
  error: string | null;
  /** Puts the control under the label at full width, for long text. */
  stacked?: boolean;
  /** False when the row shows text in place of a control; the label then names no element. */
  hasControl?: boolean;
  children: (ids: TRowIds) => ReactNode;
}) {
  const { label, hint, error, stacked = false, hasControl = true, children } = props;
  const labelId = useId();
  const hintId = useId();
  const errorId = useId();
  const controlId = useId();
  return (
    <li className={cn("flex gap-2 border-b border-subtle px-4 py-3", stacked ? "flex-col" : "flex-wrap items-center")}>
      <span className="flex min-w-0 flex-1 basis-44 flex-col gap-0.5">
        {hasControl ? (
          <label id={labelId} htmlFor={controlId} className="text-body-sm-medium text-primary">
            {label}
          </label>
        ) : (
          <span id={labelId} className="text-body-sm-medium text-primary">
            {label}
          </span>
        )}
        <span id={hintId} className="text-caption-sm-regular text-tertiary">
          {hint}
        </span>
      </span>
      <span className={cn("flex min-w-0 flex-col gap-1", stacked ? "w-full" : "ml-auto w-full max-w-60 sm:w-60")}>
        {children({ controlId, describedBy: error ? `${hintId} ${errorId}` : hintId, invalid: !!error })}
        {error && (
          <span id={errorId} role="alert" className="text-caption-sm-regular text-danger-primary">
            {error}
          </span>
        )}
      </span>
    </li>
  );
}

type TRowIds = { controlId: string; describedBy: string; invalid: boolean };

type TCardProps = {
  workspaceSlug: string;
  agent: TAgent;
  canEdit: boolean;
  /** The card action that runs now; all card actions are disabled while one runs. */
  busy: TAgentCardAction | null;
  run: TRunCardAction;
};

/**
 * Agent settings with one Save. Save sends only the fields that the user changed. When the store gets
 * new server values (a poll, another tab, a new probe), the fields that the user did not change take them.
 */
const AgentSettingsForm = observer(function AgentSettingsForm(props: TCardProps) {
  const { workspaceSlug, agent, canEdit, busy, run } = props;
  const { t } = useTranslation();
  const { updateAgent } = useAgent();
  const [form, setForm] = useState(() => agentSettingsFormOf(agent));
  const [error, setError] = useState<TAgentSettingsError | null>(null);
  const isSaving = busy === "save";
  const changes = changesOf(form);
  const hasChanges = Object.keys(changes).length > 0;
  const { draft } = form;

  useEffect(() => {
    setForm((current) => mergeServerAgent(current, agent));
  }, [agent]);

  const edit = <F extends keyof TAgentSettingsDraft>(field: F, value: TAgentSettingsDraft[F]) => {
    setForm((current) => ({ ...current, draft: { ...current.draft, [field]: value } }));
    setError((current) => clearFieldError(current, field));
  };

  const save = (event: FormEvent) => {
    event.preventDefault();
    if (!hasChanges || busy) return;
    void run("save", async () => {
      try {
        const saved = await updateAgent(workspaceSlug, agent.harness, changes);
        setForm(agentSettingsFormOf(saved));
        setError(null);
        setToast({ type: "success", title: t("agent_settings.settings.saved") });
      } catch (saveError) {
        const body = (saveError ?? {}) as TAgentSettingsError;
        setError(body);
        if (!body.codes) setToast({ type: "error", title: t("agent_settings.settings.save_failed") });
      }
    });
  };

  return (
    <form onSubmit={save} noValidate>
      <fieldset disabled={!canEdit || isSaving} className="m-0 min-w-0 border-0 p-0">
        <ul>
          <SettingRow
            label={t("agent_settings.settings.name_label")}
            hint={t("agent_settings.settings.name_hint")}
            error={getFieldErrorMessage(t, error, "name")}
          >
            {({ controlId, describedBy, invalid }) => (
              <Input
                id={controlId}
                size="md"
                value={draft.name}
                maxLength={64}
                aria-describedby={describedBy}
                aria-invalid={invalid || undefined}
                onChange={(event) => edit("name", event.target.value)}
              />
            )}
          </SettingRow>
          <SettingRow
            label={t("agent_settings.settings.handle_label")}
            hint={t("agent_settings.settings.handle_hint")}
            error={getFieldErrorMessage(t, error, "handle")}
          >
            {({ controlId, describedBy, invalid }) => (
              <InputGroup size="md">
                <span aria-hidden="true" className="pl-2 font-code text-body-sm-regular text-tertiary">
                  @
                </span>
                <Input
                  id={controlId}
                  size="md"
                  value={draft.handle}
                  maxLength={33}
                  autoComplete="off"
                  spellCheck={false}
                  aria-describedby={describedBy}
                  aria-invalid={invalid || undefined}
                  onChange={(event) => edit("handle", event.target.value)}
                />
              </InputGroup>
            )}
          </SettingRow>
          <SettingRow
            stacked
            label={t("agent_settings.settings.instructions_label")}
            hint={t("agent_settings.settings.instructions_hint")}
            error={getFieldErrorMessage(t, error, "instructions")}
          >
            {({ controlId, describedBy, invalid }) => (
              <TextArea
                id={controlId}
                size="md"
                surface="field"
                rows={5}
                value={draft.instructions}
                maxLength={MAX_INSTRUCTIONS_LENGTH}
                placeholder={t("agent_settings.settings.instructions_placeholder")}
                aria-describedby={describedBy}
                aria-invalid={invalid || undefined}
                onChange={(event) => edit("instructions", event.target.value)}
              />
            )}
          </SettingRow>
          <SettingRow
            label={t("agent_settings.model.label")}
            hint={t("agent_settings.model.hint")}
            error={getFieldErrorMessage(t, error, "selected_model")}
            hasControl={canSelectModel(agent.connection)}
          >
            {({ controlId, describedBy, invalid }) => (
              <HarnessModelSelect
                connection={agent.connection}
                harnessName={AGENT_HARNESS_LABELS[agent.harness]}
                value={draft.selected_model}
                controlId={controlId}
                describedBy={describedBy}
                invalid={invalid}
                onChange={(modelId) => edit("selected_model", modelId)}
              />
            )}
          </SettingRow>
        </ul>
        {canEdit && (
          <div className="flex justify-end px-4 py-3">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              stretch="auto"
              label={isSaving ? t("agent_settings.settings.saving") : t("agent_settings.settings.save")}
              loading={isSaving}
              disabled={!hasChanges || (busy !== null && !isSaving)}
            />
          </div>
        )}
      </fieldset>
    </form>
  );
});

/** Saves on change. Off blocks new Runs from mentions; existing Runs stay available. */
const MentionableSwitch = observer(function MentionableSwitch(props: TCardProps) {
  const { workspaceSlug, agent, canEdit, busy, run } = props;
  const { t } = useTranslation();
  const { updateAgent } = useAgent();
  const labelId = useId();
  const hintId = useId();

  const toggle = (mentionable: boolean) =>
    run("mentionable", async () => {
      try {
        await updateAgent(workspaceSlug, agent.harness, { mentionable });
      } catch {
        setToast({ type: "error", title: t("agent_settings.settings.save_failed") });
      }
    });

  return (
    <span className="ml-auto flex shrink-0 items-center gap-2">
      <span id={labelId} className="text-caption-sm-regular text-secondary">
        {t("agent_settings.settings.mentionable_label")}
      </span>
      <span id={hintId} className="sr-only">
        {t("agent_settings.settings.mentionable_hint")}
      </span>
      <Switch
        size="sm"
        checked={agent.mentionable}
        disabled={!canEdit || busy !== null}
        aria-labelledby={labelId}
        aria-describedby={hintId}
        onCheckedChange={(checked) => void toggle(checked)}
      />
    </span>
  );
});

/**
 * Settings card of one Agent. Save, Mentionable, Connect and Disconnect share one busy state, so only
 * one request of the card runs at a time and a late response cannot replace a newer one.
 */
const AgentSettingsCard = observer(function AgentSettingsCard(props: {
  workspaceSlug: string;
  agent: TAgent;
  canEdit: boolean;
}) {
  const { workspaceSlug, agent, canEdit } = props;
  const { t } = useTranslation();
  const [busy, setBusy] = useState<TAgentCardAction | null>(null);
  const version = agent.connection.harness_version;

  const run: TRunCardAction = async (action, task) => {
    setBusy(action);
    try {
      await task();
    } finally {
      setBusy(null);
    }
  };
  const cardProps = { workspaceSlug, agent, canEdit, busy, run };

  return (
    <section
      aria-labelledby="agent-settings-title"
      className="min-w-0 flex-1 rounded-lg border border-subtle bg-surface-1 shadow-raised-100"
    >
      <div className="flex items-center gap-3 border-b border-subtle px-4 py-3">
        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-accent-subtle text-accent-primary">
          <AgentOutline className="size-4" aria-hidden="true" />
        </span>
        <div className="flex min-w-0 flex-col">
          <h4 id="agent-settings-title" className="truncate text-body-md-semibold text-primary">
            {agent.name}
          </h4>
          <span className="truncate text-caption-sm-regular text-tertiary">
            {agent.connection.state === "connected"
              ? t("agent_settings.detail.on_the_mini", { version: harnessCliLabel(agent.harness, version) })
              : harnessCliLabel(agent.harness, "")}
          </span>
        </div>
        <MentionableSwitch {...cardProps} />
      </div>
      {!canEdit && (
        <p className="border-b border-subtle px-4 py-2 text-caption-sm-regular text-tertiary">
          {t("agent_settings.detail.read_only")}
        </p>
      )}
      <ul>
        <HarnessConnectionRow {...cardProps} />
      </ul>
      <AgentSettingsForm {...cardProps} />
    </section>
  );
});

function AgentSelector({ workspaceSlug, current }: { workspaceSlug: string; current: TAgentHarness }) {
  const { t } = useTranslation();
  const { getAgent } = useAgent();
  return (
    <nav aria-label={t("agent_settings.detail.selector_label")} className="w-full shrink-0 md:w-56">
      <ul className="flex flex-col gap-1.5">
        {AGENT_HARNESSES.map((harness) => {
          const agent = getAgent(workspaceSlug, harness);
          const isCurrent = harness === current;
          return (
            <li key={harness}>
              <Link
                href={`/${workspaceSlug}/settings/integrations/${harness}`}
                aria-current={isCurrent ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg border px-3 py-2.5 focus-visible:outline-2 focus-visible:outline-accent-strong",
                  isCurrent
                    ? "border-accent-strong bg-layer-1-selected"
                    : "border-subtle bg-surface-1 hover:border-strong"
                )}
              >
                <span className="grid size-8 shrink-0 place-items-center rounded-full bg-accent-subtle text-accent-primary">
                  <AgentOutline className="size-4" aria-hidden="true" />
                </span>
                <span className="flex min-w-0 flex-col">
                  <span className="truncate text-body-sm-semibold text-primary">
                    {agent?.name ?? AGENT_HARNESS_LABELS[harness]}
                  </span>
                  {agent && (
                    <span className="truncate font-code text-caption-sm-regular text-tertiary">@{agent.handle}</span>
                  )}
                </span>
                {agent && <HarnessStatusTag state={agent.connection.state} className="ml-auto shrink-0" />}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/** Harness detail page: Agent selector with live tags, and the settings of the selected Agent. */
export const HarnessDetailPage = observer(function HarnessDetailPage({ workspaceSlug, harness, canEdit }: Props) {
  const { t } = useTranslation();
  const { getAgent } = useAgent();
  const { error, isLoading, mutate } = useWorkspaceAgents(workspaceSlug);
  const agent = getAgent(workspaceSlug, harness);

  return (
    <div className="flex w-full flex-col gap-6">
      <Link
        href={`/${workspaceSlug}/settings/integrations`}
        className="flex w-fit items-center gap-1 text-caption-sm-regular text-tertiary hover:text-secondary"
      >
        <ArrowNarrowLeftOutline className="size-3.5" aria-hidden="true" />
        {t("agent_settings.detail.back")}
      </Link>
      <SettingsHeading title={AGENT_HARNESS_LABELS[harness]} description={t("agent_settings.detail.description")} />
      {!!error && !isLoading && <AgentsLoadError onRetry={() => void mutate()} />}
      {agent && (
        <div className="flex flex-col gap-4 md:flex-row md:items-start">
          <AgentSelector workspaceSlug={workspaceSlug} current={harness} />
          <AgentSettingsCard key={agent.id} workspaceSlug={workspaceSlug} agent={agent} canEdit={canEdit} />
        </div>
      )}
    </div>
  );
});
