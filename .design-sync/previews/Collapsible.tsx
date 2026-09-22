// Owned preview: meta.render in collapsible.stories.tsx reads `isOpen` from
// useArgs(), and the storybook/preview-api stub returns {} for it, so every
// story that falls through to meta.render (Default, DefaultOpen) mounts closed
// whatever its args say. MetaRender mirrors that JSX reading args.isOpen
// directly (useState keeps the trigger interactive); stories with their own
// render() keep compose().
import * as React from "react";
import { Collapsible } from "@plane/propel";
import { ChevronDownOutline } from "@makeplane/propel/icons";
import * as S from "@ds-stories/packages/propel/src/collapsible/collapsible.stories";

function storyArgs(stories: any, key: string) {
  const meta: any = stories.default ?? {};
  const st: any = stories[key];
  const args: any = { ...meta.args, ...(st && st.args ? st.args : {}) };
  // Storybook resolves argTypes.mapping (control value -> real arg) before
  // rendering; mirror that so mapped args don't render raw.
  const at: any = { ...meta.argTypes, ...(st && st.argTypes ? st.argTypes : {}) };
  for (const k of Object.keys(args)) {
    const m = at[k] && at[k].mapping;
    if (m && typeof m === "object" && args[k] in m) args[k] = m[args[k]];
  }
  return { meta, st, args };
}

function compose(stories: any, key: string) {
  const { meta, st, args } = storyArgs(stories, key);
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
  // [].concat: a single function is legal CSF decorator shorthand. A
  // decorator returning undefined (stubbed addon) falls through to the inner
  // render — otherwise one unrecognized addon blanks the cell silently.
  const decorators: any[] = ([] as any[]).concat((st && st.decorators) ?? []).concat(meta.decorators ?? []);
  return decorators.reduce(
    (inner: any, dec: any) => () => {
      const out = dec(inner, ctx);
      return out === undefined ? inner() : out;
    },
    render
  );
}

// Mirrors meta.render from collapsible.stories.tsx with isOpen seeded from args.
function MetaRender(args: any) {
  const [isOpen, setIsOpen] = React.useState<boolean>(!!args.isOpen);
  return (
    <Collapsible.CollapsibleRoot {...args} isOpen={isOpen} onToggle={() => setIsOpen(!isOpen)} className="w-96">
      <Collapsible.CollapsibleTrigger className="bg-gray-100 hover:bg-gray-200 flex w-full items-center justify-between rounded-md px-4 py-2">
        <span className="font-semibold">Click to toggle</span>
        <ChevronDownOutline className="h-4 w-4 transition-transform group-data-[panel-open]:rotate-180" />
      </Collapsible.CollapsibleTrigger>
      <Collapsible.CollapsibleContent className="mt-2">
        <div className="border-gray-200 rounded-md border p-4">
          <p className="text-13">This is the collapsible content that can be shown or hidden.</p>
        </div>
      </Collapsible.CollapsibleContent>
    </Collapsible.CollapsibleRoot>
  );
}
const metaStory = (key: string) => {
  const { args } = storyArgs(S, key);
  return () => <MetaRender {...args} />;
};

export const Default = /* Default */ metaStory("Default");
export const DefaultOpen = /* Default Open */ metaStory("DefaultOpen");
export const Controlled = /* Controlled */ compose(S, "Controlled");
export const NestedContent = /* Nested Content */ compose(S, "NestedContent");
export const CustomStyling = /* Custom Styling */ compose(S, "CustomStyling");
export const MultipleCollapsibles = /* Multiple Collapsibles */ compose(S, "MultipleCollapsibles");
