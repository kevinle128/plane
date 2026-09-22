// Owned preview: a Tooltip only opens on hover (or keyboard focus) and the
// component forwards no open/defaultOpen to base-ui, so the static story render
// is just the trigger. Every story composes unchanged and is opened the way a
// user opens it: base-ui's trigger listens for a native `mouseenter` and then a
// `mousemove` that rests for `openDelay` (restMs), so both are dispatched to
// every element that can be a trigger. base-ui attaches those listeners in the
// commit after its trigger ref lands, so the dispatch waits one frame. The
// args-driven stories also get `openDelay: 0` - a timing prop, not a visual
// one - so `mouseenter` opens the tooltip synchronously instead of through a
// rest timer the capture would have to outwait. Stories are framed the way
// storybook's `parameters.layout: "centered"` frames them - at the page's
// top-left corner a top/left tooltip has no room and flips.
import * as React from "react";
import * as S from "@ds-stories/packages/propel/src/tooltip/tooltip.stories";

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

// Triggers are the story's buttons, the dashed <span> (OnText) and the help
// <svg> (InFormField). Hovering a non-trigger is a no-op. A pointer rests on
// one trigger at a time, so a multi-trigger story whose tooltips would collide
// hovers only its first trigger (`firstOnly`); AllPositions keeps all four open
// because they sit apart and the story exists to show the four placements.
// Inline styles: the shipped CSS is the storybook Tailwind output, so only
// classes the repo already uses exist in it.
function hovered(Story: () => any, firstOnly = false) {
  return function Hovered() {
    const ref = React.useRef<HTMLDivElement>(null);
    React.useEffect(() => {
      const frame = requestAnimationFrame(() => {
        const root = ref.current;
        if (!root) return;
        const targets = Array.from(root.querySelectorAll("button, span, svg"));
        for (const el of firstOnly ? targets.slice(0, 1) : targets) {
          const r = el.getBoundingClientRect();
          const at = { clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 };
          el.dispatchEvent(new MouseEvent("mouseenter", { bubbles: false, ...at }));
          el.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, ...at }));
        }
      });
      return () => cancelAnimationFrame(frame);
    }, []);
    return (
      <div ref={ref} style={{ display: "flex", minHeight: "60vh", alignItems: "center", justifyContent: "center" }}>
        <Story />
      </div>
    );
  };
}

const INSTANT = { openDelay: 0 };

export const Default = /* Default */ hovered(compose(S, "Default", INSTANT));
export const WithHeading = /* With Heading */ hovered(compose(S, "WithHeading", INSTANT));
export const PositionTop = /* Position Top */ hovered(compose(S, "PositionTop", INSTANT));
export const PositionBottom = /* Position Bottom */ hovered(compose(S, "PositionBottom", INSTANT));
export const PositionLeft = /* Position Left */ hovered(compose(S, "PositionLeft", INSTANT));
export const PositionRight = /* Position Right */ hovered(compose(S, "PositionRight", INSTANT));
export const WithIcon = /* With Icon */ hovered(compose(S, "WithIcon", INSTANT));
// `disabled: true` - the tooltip never opens; the story's point is the trigger.
export const Disabled = /* Disabled */ hovered(compose(S, "Disabled", INSTANT));
export const LongContent = /* Long Content */ hovered(compose(S, "LongContent", INSTANT));
export const CustomDelay = /* Custom Delay */ hovered(compose(S, "CustomDelay", INSTANT));
export const CustomOffset = /* Custom Offset */ hovered(compose(S, "CustomOffset", INSTANT));
// The render()-driven stories ignore args and keep their 200ms rest timer.
export const AllPositions = /* All Positions */ hovered(compose(S, "AllPositions"));
export const OnText = /* On Text */ hovered(compose(S, "OnText"));
export const OnDisabledButton = /* On Disabled Button */ hovered(compose(S, "OnDisabledButton"));
export const ComplexContent = /* Complex Content */ hovered(compose(S, "ComplexContent", INSTANT));
export const WithCustomStyling = /* With Custom Styling */ hovered(compose(S, "WithCustomStyling", INSTANT));
// Adjacent triggers: every tooltip open at once overlaps into one clipped strip.
export const MultipleTooltips = /* Multiple Tooltips */ hovered(compose(S, "MultipleTooltips"), true);
export const IconButtons = /* Icon Buttons */ hovered(compose(S, "IconButtons"), true);
export const InFormField = /* In Form Field */ hovered(compose(S, "InFormField"));
