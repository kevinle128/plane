// Owned preview: every Combobox story keeps the options popup closed until a
// click, so the static render is only the trigger button. `Default`
// (meta.render spreads args onto the root) is composed with `open: true`; the
// other stories ignore args, so they are mirrored by hand with an `open` state
// that starts true. `Disabled` stays closed - its intent is the disabled trigger.
// `CustomEmptyMessage` also seeds the search query, since its message only
// shows after a user types something that matches no option.
import * as React from "react";
import { Combobox } from "@plane/propel";
import { ChevronExpandOutline, TickOutline } from "@makeplane/propel/icons";
import * as S from "@ds-stories/packages/propel/src/combobox/combobox.stories";

function compose(stories: any, key: string, extraArgs: Record<string, unknown> = {}) {
  const meta: any = stories.default ?? {};
  const st: any = stories[key];
  const args: any = { ...meta.args, ...(st && st.args ? st.args : {}), ...extraArgs };
  const at: any = { ...meta.argTypes, ...(st && st.argTypes ? st.argTypes : {}) };
  for (const k of Object.keys(args)) {
    const m = at[k] && at[k].mapping;
    if (m && typeof m === "object" && args[k] in m) args[k] = m[args[k]];
  }
  const title: string = typeof meta.title === "string" ? meta.title : "";
  const ctx: any = {
    args,
    name: key,
    title,
    kind: title,
    id: "",
    componentId: "",
    globals: {},
    viewMode: "story",
    parameters: (st && st.parameters) ?? meta.parameters ?? {},
  };
  let render: (() => any) | null = null;
  if (st && typeof st.render === "function") render = () => st.render(args, ctx);
  else if (typeof st === "function") render = () => st(args, ctx);
  else if (typeof meta.render === "function") render = () => meta.render(args, ctx);
  else {
    const C = (st && st.component) || meta.component;
    if (C) render = () => React.createElement(C, args);
  }
  if (!render) return () => null;
  const decorators: any[] = ([] as any[]).concat((st && st.decorators) ?? []).concat(meta.decorators ?? []);
  return decorators.reduce(
    (inner: any, dec: any) => () => {
      const out = dec(inner, ctx);
      return out === undefined ? inner() : out;
    },
    render
  );
}

const OPEN = { open: true };

// Story-local fixture from combobox.stories.tsx.
const frameworks = [
  { value: "react", label: "React" },
  { value: "vue", label: "Vue" },
  { value: "angular", label: "Angular" },
  { value: "svelte", label: "Svelte" },
  { value: "solid", label: "Solid" },
  { value: "next", label: "Next.js" },
  { value: "nuxt", label: "Nuxt" },
  { value: "remix", label: "Remix" },
];

const BUTTON =
  "border-gray-300 hover:bg-gray-50 flex w-72 items-center justify-between rounded-md border bg-white px-4 py-2";

export const Default = /* Default */ compose(S, "Default", OPEN);

export const WithoutSearch = () => {
  const [value, setValue] = React.useState("");
  const [open, setOpen] = React.useState(true);
  return (
    <Combobox value={value} onValueChange={(v) => setValue(v as string)} open={open} onOpenChange={setOpen}>
      <Combobox.Button className={BUTTON}>
        <span>{value ? frameworks.find((f) => f.value === value)?.label : "Select framework..."}</span>
        <ChevronExpandOutline className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </Combobox.Button>
      <Combobox.Options className="w-72">
        {frameworks.map((framework) => (
          <Combobox.Option key={framework.value} value={framework.value} className="flex items-center gap-2 px-4 py-2">
            {value === framework.value && <TickOutline className="h-4 w-4" />}
            <span>{framework.label}</span>
          </Combobox.Option>
        ))}
      </Combobox.Options>
    </Combobox>
  );
};

export const MultiSelect = () => {
  const [value, setValue] = React.useState<string[]>([]);
  const [open, setOpen] = React.useState(true);
  return (
    <Combobox
      multiSelect
      value={value}
      onValueChange={(v) => setValue(v as string[])}
      open={open}
      onOpenChange={setOpen}
    >
      <Combobox.Button className={BUTTON}>
        <span className="truncate">{value.length > 0 ? `${value.length} selected` : "Select frameworks..."}</span>
        <ChevronExpandOutline className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </Combobox.Button>
      <Combobox.Options showSearch searchPlaceholder="Search framework..." className="w-72">
        {frameworks.map((framework) => (
          <Combobox.Option key={framework.value} value={framework.value} className="flex items-center gap-2 px-4 py-2">
            {value.includes(framework.value) && <TickOutline className="h-4 w-4" />}
            <span>{framework.label}</span>
          </Combobox.Option>
        ))}
      </Combobox.Options>
    </Combobox>
  );
};

export const MultiSelectWithLimit = () => {
  const [value, setValue] = React.useState<string[]>([]);
  const [open, setOpen] = React.useState(true);
  return (
    <div className="space-y-2">
      <Combobox
        multiSelect
        maxSelections={3}
        value={value}
        onValueChange={(v) => setValue(v as string[])}
        open={open}
        onOpenChange={setOpen}
      >
        <Combobox.Button className={BUTTON}>
          <span className="truncate">
            {value.length > 0 ? `${value.length}/3 selected` : "Select up to 3 frameworks..."}
          </span>
          <ChevronExpandOutline className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Combobox.Button>
        <Combobox.Options showSearch searchPlaceholder="Search framework..." className="w-72">
          {frameworks.map((framework) => (
            <Combobox.Option
              key={framework.value}
              value={framework.value}
              className="flex items-center gap-2 px-4 py-2"
            >
              {value.includes(framework.value) && <TickOutline className="h-4 w-4" />}
              <span>{framework.label}</span>
            </Combobox.Option>
          ))}
        </Combobox.Options>
      </Combobox>
      <p className="text-gray-500 text-11">Maximum 3 selections allowed</p>
    </div>
  );
};

// Disabled trigger is the story's point - a disabled combobox has no open state.
export const Disabled = /* Disabled */ compose(S, "Disabled");

export const DisabledOptions = () => {
  const [value, setValue] = React.useState("");
  const [open, setOpen] = React.useState(true);
  return (
    <Combobox value={value} onValueChange={(v) => setValue(v as string)} open={open} onOpenChange={setOpen}>
      <Combobox.Button className={BUTTON}>
        <span>{value ? frameworks.find((f) => f.value === value)?.label : "Select framework..."}</span>
        <ChevronExpandOutline className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </Combobox.Button>
      <Combobox.Options showSearch searchPlaceholder="Search framework..." className="w-72">
        {frameworks.map((framework) => (
          <Combobox.Option
            key={framework.value}
            value={framework.value}
            disabled={framework.value === "angular" || framework.value === "svelte"}
            className="flex items-center gap-2 px-4 py-2"
          >
            {value === framework.value && <TickOutline className="h-4 w-4" />}
            <span>{framework.label}</span>
          </Combobox.Option>
        ))}
      </Combobox.Options>
    </Combobox>
  );
};

export const CustomMaxHeight = () => {
  const [value, setValue] = React.useState("");
  const [open, setOpen] = React.useState(true);
  return (
    <Combobox value={value} onValueChange={(v) => setValue(v as string)} open={open} onOpenChange={setOpen}>
      <Combobox.Button className={BUTTON}>
        <span>{value ? frameworks.find((f) => f.value === value)?.label : "Select framework..."}</span>
        <ChevronExpandOutline className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </Combobox.Button>
      <Combobox.Options showSearch searchPlaceholder="Search framework..." maxHeight="sm" className="w-72">
        {frameworks.map((framework) => (
          <Combobox.Option key={framework.value} value={framework.value} className="flex items-center gap-2 px-4 py-2">
            {value === framework.value && <TickOutline className="h-4 w-4" />}
            <span>{framework.label}</span>
          </Combobox.Option>
        ))}
      </Combobox.Options>
    </Combobox>
  );
};

// The empty message only renders once a search query matches nothing, so the
// query a user would type is seeded (controlled, still editable).
export const CustomEmptyMessage = () => {
  const [value, setValue] = React.useState("");
  const [open, setOpen] = React.useState(true);
  const [query, setQuery] = React.useState("ember");
  return (
    <Combobox value={value} onValueChange={(v) => setValue(v as string)} open={open} onOpenChange={setOpen}>
      <Combobox.Button className={BUTTON}>
        <span>{value ? frameworks.find((f) => f.value === value)?.label : "Select framework..."}</span>
        <ChevronExpandOutline className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </Combobox.Button>
      <Combobox.Options
        showSearch
        searchPlaceholder="Search framework..."
        emptyMessage="No frameworks found. Try a different search."
        searchQuery={query}
        onSearchQueryChange={setQuery}
        className="w-72"
      >
        {frameworks.map((framework) => (
          <Combobox.Option key={framework.value} value={framework.value} className="flex items-center gap-2 px-4 py-2">
            {value === framework.value && <TickOutline className="h-4 w-4" />}
            <span>{framework.label}</span>
          </Combobox.Option>
        ))}
      </Combobox.Options>
    </Combobox>
  );
};
