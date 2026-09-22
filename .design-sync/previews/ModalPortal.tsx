// Owned preview: the Default story wraps ModalPortal in a module-local
// `ModalDemo` whose own useState(false) overrides the `isOpen` arg, so the static
// render is only the "Open Modal" button. Mirror the demo with the modal open.
// `Positions` / `Widths` have no single static open state (a click picks one of
// several modals) and `BasicPortal` has none, so they compose unchanged.
import * as React from "react";
import { Button, ModalPortal } from "@plane/propel";
import * as S from "@ds-stories/packages/propel/src/portal/portal.stories";

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

// Mirrors the story's module-local ModalContent helper.
function ModalContent({
  title = "Modal Title",
  showCloseButton = true,
  description = "This is a modal portal component with full accessibility support. Try pressing Tab to navigate through elements or Escape to close.",
  onClose,
}: {
  title?: string;
  showCloseButton?: boolean;
  description?: string;
  onClose?: () => void;
}) {
  return (
    <div className="flex h-full flex-col bg-white">
      <div className="border-gray-200 flex items-center justify-between border-b p-6">
        <div>
          <h2 className="text-gray-900 text-18 font-semibold">{title}</h2>
          <p className="text-gray-500 mt-1 text-13">Modal demonstration</p>
        </div>
        {showCloseButton && onClose && (
          <Button variant="ghost" onClick={onClose} aria-label="Close modal">
            ✕
          </Button>
        )}
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        <p className="text-gray-600 mb-6">{description}</p>

        <div className="space-y-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-gray-900 mb-2 font-medium">Feature Highlights</h3>
            <ul className="text-gray-600 space-y-1 text-13">
              <li>• ESC key closes the modal</li>
              <li>• Click outside overlay to close</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

// Mirrors meta.render + ModalDemo from portal.stories.tsx with the modal open.
export const Default = () => {
  const [isOpen, setIsOpen] = React.useState(true);
  return (
    <>
      <Button variant="primary" onClick={() => setIsOpen(true)}>
        Open Modal
      </Button>
      <ModalPortal isOpen={isOpen} onClose={() => setIsOpen(false)}>
        <ModalContent
          title="Default Modal"
          description="A standard modal with all default settings. Demonstrates focus management, keyboard navigation, and accessibility features."
        />
      </ModalPortal>
    </>
  );
};

export const Positions = /* Different Positions */ compose(S, "Positions");
export const Widths = /* Different Widths */ compose(S, "Widths");
export const BasicPortal = /* Basic Portal */ compose(S, "BasicPortal");
