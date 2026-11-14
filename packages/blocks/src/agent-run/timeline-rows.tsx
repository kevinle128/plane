/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useId, useState } from "react";
import type { ReactNode } from "react";
import { Icon } from "@makeplane/propel/components/icon";
import type { IconGlyph } from "@makeplane/propel/components/icon";
import {
  AgentOutline,
  AlertCircleOutline,
  ChevronRightOutline,
  CodeOutline,
  InfoOutline,
  MessageSupportOutline,
  TickOutline,
  UserOutline,
} from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import type { TAgentRunEvent } from "@plane/types";
import { cn } from "@plane/utils";
import { formatRunDuration } from "./run-time";
import type { TTimelineEntry, TTimelineStep, TTimelineToolStep, TTimelineWorkEntry } from "./timeline-group";

type TRenderMarkdown = (text: string) => ReactNode;

export type RunTimelineRowsProps = {
  entries: TTimelineEntry[];
  /** Renders Agent answers and the conclusion. Defaults to plain text with line breaks. */
  renderMarkdown?: TRenderMarkdown;
  /** Glyph of the member's request, for example the requester avatar. */
  requesterGlyph?: ReactNode;
};

const plainText: TRenderMarkdown = (text) => <p className="whitespace-pre-wrap">{text}</p>;

const textOf = (value: unknown) => (typeof value === "string" ? value : "");

function Glyph({ icon, children, className }: { icon?: IconGlyph; children?: ReactNode; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "relative z-[1] grid size-6 shrink-0 place-items-center rounded-md border border-subtle bg-layer-2 text-tertiary",
        className
      )}
    >
      {icon ? <Icon icon={icon} /> : children}
    </span>
  );
}

function Row({ glyph, children, last }: { glyph: ReactNode; children: ReactNode; last: boolean }) {
  return (
    <li className={cn("relative flex items-start gap-3", { "pb-4": !last })}>
      {!last && <span aria-hidden className="absolute top-6 bottom-0 left-3 w-px bg-layer-3" />}
      {glyph}
      <div className="min-w-0 flex-1 pt-0.5 text-body-sm-regular text-primary">{children}</div>
    </li>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <span className={cn("inline-flex shrink-0 text-tertiary transition-transform", { "rotate-90": open })}>
      <Icon icon={ChevronRightOutline} />
    </span>
  );
}

/** A scrollable code block that keyboard and screen-reader users can reach by name. */
function CodeBlock({ label, children, danger }: { label: string; children: string; danger?: boolean }) {
  return (
    <pre
      role="region"
      aria-label={label}
      tabIndex={0}
      className={cn(
        "max-h-80 overflow-auto rounded-md border border-subtle bg-surface-2 p-2 font-code text-caption-sm-regular break-words whitespace-pre-wrap text-secondary focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:outline-none",
        { "text-danger-primary": danger }
      )}
    >
      {children}
    </pre>
  );
}

function formatToolInput(input: unknown): string {
  if (input === undefined) return "";
  if (input && typeof input === "object" && (input as { truncated?: unknown }).truncated === true)
    return textOf((input as { text?: unknown }).text);
  return typeof input === "string" ? input : JSON.stringify(input, null, 2);
}

function ThoughtStep({ step }: { step: Extract<TTimelineStep, { type: "thought" }> }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      type="button"
      aria-expanded={open}
      onClick={() => setOpen(!open)}
      className="flex w-full min-w-0 items-start gap-1.5 rounded-sm text-start text-body-sm-regular text-secondary italic focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:outline-none"
    >
      <Chevron open={open} />
      <span className={cn("min-w-0 flex-1", open ? "break-words whitespace-pre-wrap" : "truncate")}>{step.text}</span>
    </button>
  );
}

function ToolStep({ step }: { step: TTimelineToolStep }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const detailsId = useId();
  const input = formatToolInput(step.input);
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={detailsId}
        onClick={() => setOpen(!open)}
        className="flex w-full min-w-0 items-center gap-1.5 rounded-sm text-start focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:outline-none"
      >
        <Chevron open={open} />
        <span className="inline-flex shrink-0 text-tertiary">
          <Icon icon={CodeOutline} />
        </span>
        <span className="shrink-0 font-code text-caption-sm-medium text-primary">
          {step.name || t("agent_run.timeline.tool_output")}
        </span>
        {step.target && (
          <span className="min-w-0 truncate font-code text-caption-sm-regular text-tertiary">{step.target}</span>
        )}
        {step.result?.isError && (
          <span className="shrink-0 text-caption-sm-medium text-danger-primary">
            {t("agent_run.timeline.tool_failed")}
          </span>
        )}
      </button>
      {open && (
        <div id={detailsId} className="flex flex-col gap-1.5 ps-5">
          {input && <CodeBlock label={t("agent_run.timeline.tool_input")}>{input}</CodeBlock>}
          {step.result && (
            <CodeBlock label={t("agent_run.timeline.tool_result")} danger={step.result.isError}>
              {step.result.text}
            </CodeBlock>
          )}
          {step.result && !step.result.complete && (
            <span className="text-caption-sm-regular text-tertiary">{t("agent_run.timeline.result_partial")}</span>
          )}
        </div>
      )}
    </div>
  );
}

function WorkGroup({ entry }: { entry: TTimelineWorkEntry }) {
  const { t } = useTranslation();
  // `null` follows the Run: open while it works there, closed when done. A member's choice then stays.
  const [choice, setChoice] = useState<boolean | null>(null);
  const open = choice ?? entry.active;
  const stepsId = useId();
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={stepsId}
        onClick={() => setChoice(!open)}
        className="flex w-fit items-center gap-1.5 rounded-sm text-body-sm-medium text-secondary focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:outline-none"
      >
        <Chevron open={open} />
        {entry.active
          ? t("agent_run.timeline.working", { count: entry.stepCount })
          : t("agent_run.timeline.worked_for", { duration: formatRunDuration(entry.durationMs) })}
      </button>
      {open && (
        <ul id={stepsId} className="flex flex-col gap-2 border-s border-subtle ps-3">
          {entry.steps.map((step) => (
            <li key={step.id} className="min-w-0">
              {step.type === "thought" ? <ThoughtStep step={step} /> : <ToolStep step={step} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function EventRow({
  event,
  renderMarkdown,
  requesterGlyph,
  last,
}: {
  event: TAgentRunEvent;
  renderMarkdown: TRenderMarkdown;
  requesterGlyph?: ReactNode;
  last: boolean;
}) {
  const { t } = useTranslation();
  switch (event.kind) {
    case "message":
      return event.payload.role === "user" ? (
        <Row glyph={requesterGlyph ? <Glyph>{requesterGlyph}</Glyph> : <Glyph icon={UserOutline} />} last={last}>
          <p className="break-words whitespace-pre-wrap">{textOf(event.payload.text)}</p>
        </Row>
      ) : (
        <Row glyph={<Glyph icon={AgentOutline} />} last={last}>
          {renderMarkdown(textOf(event.payload.text))}
        </Row>
      );
    case "conclusion":
      return (
        <Row glyph={<Glyph icon={TickOutline} className="text-success-primary" />} last={last}>
          <span className="mb-1 block text-caption-sm-medium text-tertiary">{t("agent_run.timeline.conclusion")}</span>
          {textOf(event.payload.text) && renderMarkdown(textOf(event.payload.text))}
        </Row>
      );
    case "error":
      return (
        <Row glyph={<Glyph icon={AlertCircleOutline} className="text-danger-primary" />} last={last}>
          <div role="alert" className="flex flex-col gap-1 rounded-md bg-danger-subtle px-3 py-2">
            <span className="break-words text-danger-primary">{textOf(event.payload.message)}</span>
            {textOf(event.payload.code) && (
              <span className="font-code text-caption-sm-regular text-tertiary">{textOf(event.payload.code)}</span>
            )}
          </div>
        </Row>
      );
    default:
      // Status lines and kinds this panel does not lay out yet show their text.
      return (
        <Row glyph={<Glyph icon={InfoOutline} />} last={last}>
          <span className="text-caption-sm-regular text-tertiary">
            {textOf((event.payload as { text?: unknown }).text) || textOf((event.payload as { code?: unknown }).code)}
          </span>
        </Row>
      );
  }
}

/** The Run timeline: requests, answers, status and errors, with tool work collapsed into Working groups. */
export function RunTimelineRows({ entries, renderMarkdown = plainText, requesterGlyph }: RunTimelineRowsProps) {
  return (
    <ol className="flex flex-col">
      {entries.map((entry, index) => {
        const last = index === entries.length - 1;
        return entry.type === "work" ? (
          <Row key={entry.id} glyph={<Glyph icon={MessageSupportOutline} />} last={last}>
            <WorkGroup entry={entry} />
          </Row>
        ) : (
          <EventRow
            key={entry.event.id}
            event={entry.event}
            renderMarkdown={renderMarkdown}
            requesterGlyph={requesterGlyph}
            last={last}
          />
        );
      })}
    </ol>
  );
}
