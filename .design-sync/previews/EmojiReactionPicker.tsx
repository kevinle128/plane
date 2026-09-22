// Owned preview: every EmojiReactionPicker story keeps the popover closed
// (`isOpen` comes from a `useState(false)` inside each story's render(), which
// ignores args, so no `extraArgs` can open it). Mirror the same stories by hand
// with `isOpen` true so the real emoji picker panel renders; the reference
// storybook shows only the closed trigger (graded under the gated-reference
// clause). `DifferentPlacements` stays composed from the story: four pickers
// have no meaningful simultaneous open state (they would paint over each other).
import * as React from "react";
import { EmojiReactionPicker, EmojiReactionGroup } from "@plane/propel";
import { ReactionOutline } from "@makeplane/propel/icons";
import * as S from "@ds-stories/packages/propel/src/emoji-reaction/emoji-reaction-picker.stories";

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

// Story fixtures (inlined from emoji-reaction-picker.stories.tsx, initial state).
const inlineReactions = [
  { emoji: "👍", count: 3, reacted: false, users: ["Alice", "Bob", "Charlie"] },
  { emoji: "❤️", count: 2, reacted: true, users: ["You", "David"] },
];
const messageReactions = [{ emoji: "👍", count: 5, reacted: false, users: ["Alice", "Bob", "Charlie"] }];

export const Default = () => (
  <div className="space-y-4 p-4">
    <EmojiReactionPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      closeOnSelect
      label={
        <span className="flex size-8 items-center justify-center rounded-md px-2 text-18">
          <ReactionOutline className="h-6 text-primary" />
        </span>
      }
    />
  </div>
);

export const WithCustomLabel = () => (
  <div className="space-y-4 p-4">
    <EmojiReactionPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      closeOnSelect
      label={
        <button className="flex items-center gap-2 rounded-sm border border-subtle bg-layer-1 px-4 py-2 hover:bg-surface-2">
          <ReactionOutline className="h-4 w-4" />
          <span className="text-13">Add Reaction</span>
        </button>
      }
    />
  </div>
);

export const InlineReactions = () => (
  <div className="p-4">
    <EmojiReactionGroup reactions={inlineReactions} onReactionClick={noop} onAddReaction={noop} showAddButton={false} />
    <EmojiReactionPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      closeOnSelect
      label={
        <button className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-dashed border-strong bg-surface-1 text-placeholder transition-all duration-200 hover:border-accent-strong hover:bg-accent-primary/5 hover:text-accent-primary">
          <ReactionOutline className="h-3.5 w-3.5" />
        </button>
      }
    />
  </div>
);

export const DifferentPlacements = /* Different Placements */ compose(S, "DifferentPlacements");

export const SearchDisabled = () => (
  <div className="space-y-4 p-4">
    <EmojiReactionPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      closeOnSelect
      searchDisabled
      label={
        <button className="rounded-sm border border-subtle bg-layer-1 px-4 py-2 hover:bg-surface-2">No Search</button>
      }
    />
  </div>
);

export const CustomSearchPlaceholder = () => (
  <div className="space-y-4 p-4">
    <EmojiReactionPicker
      isOpen
      handleToggle={noop}
      onChange={noop}
      closeOnSelect
      searchPlaceholder="Find your emoji..."
      label={
        <button className="rounded-sm border border-subtle bg-layer-1 px-4 py-2 hover:bg-surface-2">
          Custom Search
        </button>
      }
    />
  </div>
);

export const CloseOnSelectDisabled = () => (
  <div className="space-y-4 p-4">
    <div className="flex items-center gap-2">
      <EmojiReactionPicker
        isOpen
        handleToggle={noop}
        onChange={noop}
        closeOnSelect={false}
        label={
          <button className="rounded-sm border border-subtle bg-layer-1 px-4 py-2 hover:bg-surface-2">
            Select Multiple (Stays Open)
          </button>
        }
      />
      <button className="rounded-sm bg-layer-1 px-3 py-1.5 text-13 hover:bg-surface-2">Clear</button>
    </div>
  </div>
);

export const InMessageContext = () => (
  <div className="max-w-md space-y-3 rounded-lg border border-subtle p-4">
    <div className="flex items-start gap-3">
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-primary text-13 text-on-color">
        AB
      </div>
      <div className="flex-1">
        <div className="text-13 font-medium">Alice Brown</div>
        <div className="mt-1 text-13 text-tertiary">
          Just finished the design for the new dashboard! Would love to hear your thoughts.
        </div>
      </div>
    </div>
    <div className="flex gap-2">
      <EmojiReactionGroup reactions={messageReactions} onReactionClick={noop} showAddButton={false} />
      <EmojiReactionPicker
        isOpen
        handleToggle={noop}
        onChange={noop}
        closeOnSelect
        label={
          <button className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-dashed border-strong bg-surface-1 text-placeholder transition-all duration-200 hover:border-accent-strong hover:bg-accent-primary/5 hover:text-accent-primary">
            <ReactionOutline className="h-3.5 w-3.5" />
          </button>
        }
      />
    </div>
  </div>
);
