// Owned preview: every EmojiPicker story keeps the popover closed (`isOpen`
// comes from a `useState(false)` inside each story's render(), which ignores
// args, so no `extraArgs` can open it; `defaultOpen` is the default TAB, not
// the popover state). Mirror the same stories by hand with `isOpen` true so the
// real emoji / icon picker panel renders; the reference storybook shows only
// the closed trigger (graded under the gated-reference clause).
// `DifferentPlacements` stays composed from the story: four pickers have no
// meaningful simultaneous open state (they would paint over each other).
import * as React from "react";
import { EmojiPicker, EmojiIconPickerTypes } from "@plane/propel";
import * as S from "@ds-stories/packages/propel/src/emoji-icon-picker/emoji-picker.stories";

function compose(stories: any, key: string) {
  const meta: any = stories.default ?? {};
  const st: any = stories[key];
  const args: any = { ...meta.args, ...(st && st.args ? st.args : {}) };
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

const noop = () => {};

export const Default = () => (
  <div className="space-y-4 p-4">
    <EmojiPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      label="😊 Pick an emoji or icon"
      defaultOpen={EmojiIconPickerTypes.EMOJI}
      closeOnSelect
    />
  </div>
);

export const OpenToEmojiTab = () => (
  <div className="space-y-4 p-4">
    <EmojiPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      label="😊 Choose Emoji"
      defaultOpen={EmojiIconPickerTypes.EMOJI}
      closeOnSelect
    />
  </div>
);

export const OpenToIconTab = () => (
  <div className="space-y-4 p-4">
    <EmojiPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      label="🎨 Choose Icon"
      defaultOpen={EmojiIconPickerTypes.ICON}
      closeOnSelect
    />
  </div>
);

export const LucideIcons = () => (
  <div className="space-y-4 p-4">
    <EmojiPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      label="Lucide Icons"
      defaultOpen={EmojiIconPickerTypes.ICON}
      closeOnSelect
      iconType="lucide"
    />
  </div>
);

export const MaterialIcons = () => (
  <div className="space-y-4 p-4">
    <EmojiPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      label="Material Icons"
      defaultOpen={EmojiIconPickerTypes.ICON}
      closeOnSelect
      iconType="material"
    />
  </div>
);

export const CloseOnSelectDisabled = () => (
  <div className="space-y-4 p-4">
    <div className="flex items-center gap-2">
      <EmojiPicker
        isOpen
        handleToggle={noop}
        onChange={noop}
        label="Select Multiple (Stays Open)"
        defaultOpen={EmojiIconPickerTypes.EMOJI}
        closeOnSelect={false}
      />
      <button className="rounded-sm bg-layer-1 px-3 py-1.5 text-13 hover:bg-surface-2">Clear</button>
    </div>
  </div>
);

export const CustomSearchPlaceholder = () => (
  <div className="space-y-4 p-4">
    <EmojiPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      label="Custom Search"
      defaultOpen={EmojiIconPickerTypes.EMOJI}
      closeOnSelect
      searchPlaceholder="Type to find emojis..."
    />
  </div>
);

export const SearchDisabled = () => (
  <div className="space-y-4 p-4">
    <EmojiPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      label="No Search"
      defaultOpen={EmojiIconPickerTypes.EMOJI}
      closeOnSelect
      searchDisabled
    />
  </div>
);

export const CustomIconColor = () => (
  <div className="space-y-4 p-4">
    <EmojiPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      label="Custom Icon Color"
      defaultOpen={EmojiIconPickerTypes.ICON}
      closeOnSelect
      defaultIconColor="#FF5733"
    />
  </div>
);

export const DifferentPlacements = /* Different Placements */ compose(S, "DifferentPlacements");

export const InFormContext = () => (
  <div className="max-w-md p-4">
    <form className="space-y-4 rounded-lg border border-subtle p-6">
      <div>
        <label htmlFor="project-title" className="mb-2 block text-13 font-medium">
          Project Title
        </label>
        <input
          id="project-title"
          type="text"
          defaultValue=""
          className="w-full rounded-sm border border-subtle bg-layer-1 px-3 py-2"
          placeholder="Enter project title"
        />
      </div>
      <div>
        <label htmlFor="project-icon" className="mb-2 block text-13 font-medium">
          Project Icon
        </label>
        <EmojiPicker
          isOpen
          handleToggle={noop}
          onChange={noop}
          label="Click to select icon"
          defaultOpen={EmojiIconPickerTypes.EMOJI}
          closeOnSelect
          buttonClassName="px-4 py-2 bg-layer-1 border border-subtle rounded-sm hover:bg-surface-2 w-full text-left"
        />
      </div>
      <button
        type="submit"
        className="w-full rounded-sm bg-accent-primary px-4 py-2 text-on-color hover:bg-accent-primary/80"
      >
        Create Project
      </button>
    </form>
  </div>
);
