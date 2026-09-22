// Owned preview: a Menu only opens on a click of its trigger - the component
// keeps its own isOpen state and passes no open/defaultOpen to base-ui - so the
// static story render is just the trigger button. Every story composes
// unchanged and is opened the way a user opens it: base-ui's trigger opens on
// `mousedown` (useClick, event: 'mousedown') and the component styles its
// trigger as open from the `click`, so both are dispatched on mount.
import * as React from "react";
import * as S from "@ds-stories/packages/propel/src/menu/menu.stories";

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

// The story's first <button> is the menu trigger (a customButton story nests
// its button inside the trigger, so the trigger is still first). A story with
// a Menu.SubMenu then hovers the submenu trigger (`withSubmenu`) the way a
// user reveals it: base-ui opens submenus on hover only, and the popup is
// portaled to body, so it is looked up on the document once the menu has
// rendered.
function clicked(Story: () => any, withSubmenu = false) {
  return function Clicked() {
    const ref = React.useRef<HTMLDivElement>(null);
    React.useEffect(() => {
      const trigger = ref.current?.querySelector("button");
      if (!trigger) return;
      for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
        trigger.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, button: 0 }));
      }
      if (!withSubmenu) return;
      // base-ui attaches the submenu trigger's hover listeners a commit after
      // the popup mounts, so the hover is re-dispatched each frame until the
      // trigger reports itself expanded (its own open delay is ~100ms). Opening
      // also focuses the trigger, and with no pointer interaction before the
      // mount Chromium paints its :focus-visible ring on it (SubmenuTrigger has
      // no outline-none) - a ring a real hover never shows - so that focus is
      // dropped for a few frames after the submenu opens; the submenu stays open.
      let frame = 0;
      let tries = 0;
      let settle = 0;
      const hover = () => {
        const sub = document.querySelector('[role="menuitem"][aria-haspopup="menu"]');
        if (tries++ > 90) return;
        if (sub?.getAttribute("aria-expanded") === "true") {
          const active = document.activeElement as HTMLElement | null;
          if (active && active.closest('[role="menu"]')) active.blur();
          if (settle++ > 10) return;
        } else if (sub) {
          const r = sub.getBoundingClientRect();
          const at = { clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 };
          sub.dispatchEvent(new MouseEvent("mouseenter", { bubbles: false, ...at }));
          sub.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, ...at }));
        }
        frame = requestAnimationFrame(hover);
      };
      frame = requestAnimationFrame(hover);
      return () => cancelAnimationFrame(frame);
    }, []);
    return (
      <div ref={ref} style={{ display: "contents" }}>
        <Story />
      </div>
    );
  };
}

export const Default = /* Default */ clicked(compose(S, "Default"));
export const WithIcons = /* With Icons */ clicked(compose(S, "WithIcons"));
export const Ellipsis = /* Ellipsis */ clicked(compose(S, "Ellipsis"));
export const VerticalEllipsis = /* Vertical Ellipsis */ clicked(compose(S, "VerticalEllipsis"));
export const NoBorder = /* No Border */ clicked(compose(S, "NoBorder"));
export const NoChevron = /* No Chevron */ clicked(compose(S, "NoChevron"));
// A disabled trigger ignores the click - the story's point is the disabled button.
export const Disabled = /* Disabled */ compose(S, "Disabled");
export const DisabledItems = /* Disabled Items */ clicked(compose(S, "DisabledItems"));
export const CustomButton = /* Custom Button */ clicked(compose(S, "CustomButton"));
export const WithSubmenu = /* With Submenu */ clicked(compose(S, "WithSubmenu"), true);
export const MaxHeightSmall = /* Max Height Small */ clicked(compose(S, "MaxHeightSmall"));
export const MaxHeightLarge = /* Max Height Large */ clicked(compose(S, "MaxHeightLarge"));
export const ComplexMenu = /* Complex Menu */ clicked(compose(S, "ComplexMenu"), true);
export const CustomStyles = /* Custom Styles */ clicked(compose(S, "CustomStyles"));
