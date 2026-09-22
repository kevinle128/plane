// Owned preview: every Dialog story keeps the dialog closed until a click
// (`open: false` in meta args, opened via useArgs/useState), so the static
// render is only a trigger button. Compose the same stories with `open: true`
// so the real dialog renders; `Default` (useArgs-driven) is mirrored by hand.
import * as React from "react";
import { Dialog } from "@plane/propel";
import * as S from "@ds-stories/packages/propel/src/dialog/dialog.stories";

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

// Mirrors meta.render from dialog.stories.tsx with the dialog open.
export const Default = () => (
  <>
    <button className="bg-blue-500 hover:bg-blue-600 rounded-sm px-4 py-2 text-on-color">Open Dialog</button>
    <Dialog open onOpenChange={() => {}}>
      <Dialog.Panel>
        <div className="p-6">
          <Dialog.Title>Dialog Title</Dialog.Title>
          <div className="mt-4">
            <p className="text-gray-600 text-13">This is the dialog content. You can put any content here.</p>
          </div>
          <div className="mt-6 flex justify-end gap-2">
            <button className="bg-gray-200 hover:bg-gray-300 rounded-sm px-4 py-2 text-13">Cancel</button>
            <button className="bg-blue-500 hover:bg-blue-600 rounded-sm px-4 py-2 text-13 text-on-color">
              Confirm
            </button>
          </div>
        </div>
      </Dialog.Panel>
    </Dialog>
  </>
);
export const TopPosition = /* Top Position */ compose(S, "TopPosition", OPEN);
export const SmallWidth = /* Small Width */ compose(S, "SmallWidth", OPEN);
export const LargeWidth = /* Large Width */ compose(S, "LargeWidth", OPEN);
export const WithCloseButton = /* With Close Button */ compose(S, "WithCloseButton", OPEN);
export const ConfirmationDialog = /* Confirmation Dialog */ compose(S, "ConfirmationDialog", OPEN);
export const FormDialog = /* Form Dialog */ compose(S, "FormDialog", OPEN);
export const ScrollableContent = /* Scrollable Content */ compose(S, "ScrollableContent", OPEN);
// AllWidths has no static open state (a click picks the width) - skipped via cfg.overrides.Dialog.skip.
