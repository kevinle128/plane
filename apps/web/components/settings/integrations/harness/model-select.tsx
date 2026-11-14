/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Select, SelectContent, SelectItem, SelectList, SelectTrigger } from "@makeplane/propel/components/select";
import { canSelectModel, getModelSourceNoteKey } from "@plane/blocks/agent-run";
import { useTranslation } from "@plane/i18n";
import type { TAgentConnection } from "@plane/types";

type Props = {
  connection: TAgentConnection;
  /** Product name of the Harness, for the note on models it did not report. */
  harnessName: string;
  value: string;
  controlId: string;
  describedBy: string;
  invalid: boolean;
  onChange: (modelId: string) => void;
};

/**
 * Model choice from the models in the connection report. Without a verified report there is no
 * control, so no model is presented as verified. Models from the static fallback list carry a note
 * that the Harness did not report them.
 */
export function HarnessModelSelect({
  connection,
  harnessName,
  value,
  controlId,
  describedBy,
  invalid,
  onChange,
}: Props) {
  const { t } = useTranslation();
  if (!canSelectModel(connection)) {
    return (
      <span className="text-right text-caption-sm-regular text-tertiary">{t("agent_settings.model.unavailable")}</span>
    );
  }
  const items = connection.models.map((model) => ({ value: model.id, label: model.id }));
  return (
    <Select<string>
      items={items}
      value={value || null}
      onValueChange={(next) => {
        if (next) onChange(next);
      }}
    >
      <SelectTrigger
        id={controlId}
        size="md"
        width="auto"
        placeholder={t("agent_settings.model.placeholder")}
        aria-describedby={describedBy}
        aria-invalid={invalid || undefined}
      />
      <SelectContent side="bottom" align="end">
        <SelectList>
          {connection.models.map((model) => {
            const noteKey = getModelSourceNoteKey(model);
            return (
              <SelectItem
                key={model.id}
                value={model.id}
                label={model.id}
                secondaryText={model.label !== model.id ? model.label : undefined}
                description={(noteKey ? t(noteKey, { harness: harnessName }) : model.description) || undefined}
              />
            );
          })}
        </SelectList>
      </SelectContent>
    </Select>
  );
}
