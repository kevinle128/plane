/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useForm } from "react-hook-form";
// plane internal packages
import { Button } from "@makeplane/propel/components/button";
import { setToast } from "@plane/blocks/toast";
import type { IFormattedInstanceConfiguration, TInstanceGithubAppConfigurationKeys } from "@plane/types";
// components
import type { TControllerInputFormField } from "@/components/common/controller-input";
import { ControllerInput } from "@/components/common/controller-input";
// hooks
import { useInstance } from "@/hooks/store";

type GithubAppFormValues = Record<TInstanceGithubAppConfigurationKeys, string>;

type Props = {
  config: IFormattedInstanceConfiguration;
};

const GITHUB_APP_SETTINGS_URL = "https://github.com/settings/apps/new";

/**
 * GitHub App credentials for local CLI agents. Workspaces connect GitHub with this
 * App's device flow. When a value is empty here, Plane reads the environment variable
 * of the same name.
 */
export function InstanceGithubAppConfigForm({ config }: Props) {
  const { updateInstanceConfigurations } = useInstance();
  const {
    control,
    reset,
    handleSubmit,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<GithubAppFormValues>({
    defaultValues: {
      GITHUB_APP_CLIENT_ID: config.GITHUB_APP_CLIENT_ID ?? "",
      GITHUB_APP_CLIENT_SECRET: config.GITHUB_APP_CLIENT_SECRET ?? "",
      GITHUB_APP_SLUG: config.GITHUB_APP_SLUG ?? "",
    },
  });

  const fields: TControllerInputFormField<GithubAppFormValues>[] = [
    {
      key: "GITHUB_APP_CLIENT_ID",
      type: "text",
      label: "App client ID",
      description: (
        <>
          From your{" "}
          <a
            href={GITHUB_APP_SETTINGS_URL}
            target="_blank"
            className="text-accent-primary hover:underline"
            rel="noreferrer"
          >
            GitHub App settings
          </a>
          . Enable Device Flow on the App.
        </>
      ),
      placeholder: "Iv23liExampleClientId",
      error: Boolean(errors.GITHUB_APP_CLIENT_ID),
      required: false,
    },
    {
      key: "GITHUB_APP_CLIENT_SECRET",
      type: "password",
      label: "App client secret",
      description: <>Used to refresh tokens and to revoke a workspace token on disconnect.</>,
      placeholder: "",
      error: Boolean(errors.GITHUB_APP_CLIENT_SECRET),
      required: false,
    },
    {
      key: "GITHUB_APP_SLUG",
      type: "text",
      label: "App slug",
      description: <>The App name in its public URL, used for the organization install link.</>,
      placeholder: "plane-agents",
      error: Boolean(errors.GITHUB_APP_SLUG),
      required: false,
    },
  ];

  const onSubmit = async (formData: GithubAppFormValues) => {
    try {
      const response = await updateInstanceConfigurations(formData);
      setToast({ type: "success", title: "Done!", message: "The GitHub App for local agents is saved." });
      reset(
        Object.fromEntries(
          Object.keys(formData).map((key) => [key, response.find((item) => item.key === key)?.value ?? ""])
        ) as GithubAppFormValues
      );
    } catch (error) {
      console.error(error);
      setToast({ type: "error", title: "Error!", message: "The GitHub App settings were not saved. Try again." });
    }
  };

  return (
    <section className="flex flex-col gap-y-4 border-t border-subtle pt-8">
      <div className="flex flex-col gap-1">
        <div className="text-h6-medium text-primary">GitHub App for local agents</div>
        <p className="text-body-xs-regular text-tertiary">
          Workspaces use this App to connect GitHub, list granted repositories and open draft pull requests.
        </p>
      </div>
      <div className="flex max-w-xl flex-col gap-y-4">
        {fields.map((field) => (
          <ControllerInput
            key={field.key}
            control={control}
            type={field.type}
            name={field.key}
            label={field.label}
            description={field.description}
            placeholder={field.placeholder}
            error={field.error}
            required={field.required}
          />
        ))}
        <div>
          <Button
            variant="primary"
            size="md"
            stretch="auto"
            onClick={(event) => void handleSubmit(onSubmit)(event)}
            loading={isSubmitting}
            disabled={!isDirty}
            label={isSubmitting ? "Saving" : "Save GitHub App"}
          />
        </div>
      </div>
    </section>
  );
}
