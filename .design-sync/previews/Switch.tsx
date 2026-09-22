// Owned preview: meta.render in switch.stories.tsx reads `value` from
// useArgs(), and the storybook/preview-api stub returns {} for it, so every
// story that falls through to meta.render (Default, Checked, Small, Medium,
// Large, Disabled, DisabledChecked) mounts unchecked whatever its args say.
// MetaRender mirrors that JSX reading args.value directly (useState keeps the
// switch interactive); stories with their own render() keep compose().
import * as React from "react";
import { Switch } from "@plane/propel";
import * as S from "@ds-stories/packages/propel/src/switch/switch.stories";

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

// Mirrors meta.render from switch.stories.tsx with value seeded from args.
function MetaRender(args: any) {
  const [value, setValue] = React.useState<boolean>(!!args.value);
  return <Switch {...args} value={value} onChange={setValue} />;
}
const metaStory = (key: string) => {
  const { args } = storyArgs(S, key);
  return () => <MetaRender {...args} />;
};

export const Default = /* Default */ metaStory("Default");
export const Checked = /* Checked */ metaStory("Checked");
export const WithLabel = /* With Label */ compose(S, "WithLabel");
export const Small = /* Small */ metaStory("Small");
export const Medium = /* Medium */ metaStory("Medium");
export const Large = /* Large */ metaStory("Large");
export const Disabled = /* Disabled */ metaStory("Disabled");
export const DisabledChecked = /* Disabled Checked */ metaStory("DisabledChecked");
export const AllSizes = /* All Sizes */ compose(S, "AllSizes");
export const AllStates = /* All States */ compose(S, "AllStates");
export const InForm = /* In Form */ compose(S, "InForm");
export const WithDescription = /* With Description */ compose(S, "WithDescription");
export const Interactive = /* Interactive */ compose(S, "Interactive");
export const CustomStyles = /* Custom Styles */ compose(S, "CustomStyles");
export const MultipleControls = /* Multiple Controls */ compose(S, "MultipleControls");
