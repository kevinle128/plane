// Owned preview: every Popover story keeps the panel closed until a click
// (`open: undefined` in meta args, opened via useArgs/useState), so the static
// render is only a trigger button. Each story is mirrored with the panel open.
// The stories are mirrored by hand (not composed with `open: true`) so the
// panel can take `initialFocus={false}`: base-ui focuses the popup when it
// opens, and with no pointer interaction before the mount Chromium paints its
// default :focus-visible outline around the panel - a ring a click-opened
// popover never shows. Every story is framed the way storybook's
// `parameters.layout: "centered"` frames it: the harness mounts the trigger at
// the page's top-left corner, where a `side="top"` / `side="left"` panel has no
// room and flips to the opposite side.
import * as React from "react";
import { Popover } from "@plane/propel";
import { CloseOutline } from "@makeplane/propel/icons";

const BUTTON = "bg-blue-500 hover:bg-blue-600 rounded-sm px-4 py-2 text-on-color";
const PANEL = "border-gray-200 shadow-lg w-64 rounded-lg border bg-white p-4";

// Inline styles: the shipped CSS is the storybook build's Tailwind output, so
// only classes the repo itself uses exist in it.
function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "60vh", alignItems: "center", justifyContent: "center" }}>{children}</div>
  );
}

// Mirrors meta.render from popover.stories.tsx with the panel open.
export const Default = () => {
  const [open, setOpen] = React.useState(true);
  return (
    <Centered>
      <Popover open={open} onOpenChange={setOpen}>
        <Popover.Button className={BUTTON}>Open Popover</Popover.Button>
        <Popover.Panel initialFocus={false} className={PANEL}>
          <h3 className="text-13 font-semibold">Popover Title</h3>
          <p className="text-gray-600 mt-2 text-13">This is the popover content. You can put any content here.</p>
        </Popover.Panel>
      </Popover>
    </Centered>
  );
};

// Mirrors the Controlled story (its useState(false) ignores args) with the panel open.
export const Controlled = () => {
  const [open, setOpen] = React.useState(true);
  return (
    <Centered>
      <div className="space-y-4">
        <div className="flex gap-2">
          <button onClick={() => setOpen(true)} className="bg-blue-500 rounded-sm px-3 py-1.5 text-13 text-on-color">
            Open
          </button>
          <button onClick={() => setOpen(false)} className="bg-gray-500 rounded-sm px-3 py-1.5 text-13 text-on-color">
            Close
          </button>
        </div>
        <Popover open={open} onOpenChange={setOpen}>
          <Popover.Button className={BUTTON}>Controlled Popover</Popover.Button>
          <Popover.Panel initialFocus={false} className={PANEL}>
            <div className="flex items-start justify-between">
              <h3 className="text-13 font-semibold">Controlled State</h3>
              <button onClick={() => setOpen(false)} className="hover:bg-gray-100 rounded-full p-1">
                <CloseOutline className="h-4 w-4" />
              </button>
            </div>
            <p className="text-gray-600 mt-2 text-13">Current state: {open ? "Open" : "Closed"}</p>
          </Popover.Panel>
        </Popover>
      </div>
    </Centered>
  );
};

// The Side*/Align*/CustomOffset stories share one shape (useState(args.open)
// root, one button, a titled panel) and differ only in these values.
type PanelStoryProps = {
  label: string;
  title: string;
  text: string;
  side?: "top" | "bottom" | "left" | "right";
  align?: "start" | "center" | "end";
  sideOffset?: number;
};
function PanelStory({ label, title, text, ...panelProps }: PanelStoryProps) {
  const [open, setOpen] = React.useState(true);
  return (
    <Centered>
      <Popover open={open} onOpenChange={setOpen}>
        <Popover.Button className={BUTTON}>{label}</Popover.Button>
        <Popover.Panel {...panelProps} initialFocus={false} className={PANEL}>
          <h3 className="text-13 font-semibold">{title}</h3>
          <p className="text-gray-600 mt-2 text-13">{text}</p>
        </Popover.Panel>
      </Popover>
    </Centered>
  );
}

export const SideTop = () => (
  <PanelStory label="Open Above" side="top" title="Top Positioned" text="This popover appears above the button." />
);
export const SideBottom = () => (
  <PanelStory
    label="Open Below"
    side="bottom"
    title="Bottom Positioned"
    text="This popover appears below the button."
  />
);
export const SideLeft = () => (
  <PanelStory
    label="Open Left"
    side="left"
    title="Left Positioned"
    text="This popover appears to the left of the button."
  />
);
export const SideRight = () => (
  <PanelStory
    label="Open Right"
    side="right"
    title="Right Positioned"
    text="This popover appears to the right of the button."
  />
);
export const AlignStart = () => (
  <PanelStory label="Align Start" align="start" title="Start Aligned" text="This popover is aligned to the start." />
);
export const AlignEnd = () => (
  <PanelStory label="Align End" align="end" title="End Aligned" text="This popover is aligned to the end." />
);
export const CustomOffset = () => (
  <PanelStory
    label="Custom Offset"
    sideOffset={20}
    title="Custom Side Offset"
    text="This popover has a custom side offset of 20px."
  />
);

export const WithForm = () => {
  const [open, setOpen] = React.useState(true);
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    alert("Form submitted!");
    setOpen(false);
  };
  return (
    <Centered>
      <Popover open={open} onOpenChange={setOpen}>
        <Popover.Button className={BUTTON}>Open Form</Popover.Button>
        <Popover.Panel initialFocus={false} className="border-gray-200 shadow-lg w-72 rounded-lg border bg-white p-4">
          <h3 className="text-13 font-semibold">Quick Form</h3>
          <form onSubmit={handleSubmit} className="mt-3 space-y-3">
            <div>
              <label htmlFor="name" className="text-gray-700 block text-11 font-medium">
                Name
              </label>
              <input
                type="text"
                id="name"
                className="border-gray-300 mt-1 w-full rounded-sm border px-2 py-1.5 text-13"
                placeholder="Enter name"
              />
            </div>
            <div>
              <label htmlFor="email" className="text-gray-700 block text-11 font-medium">
                Email
              </label>
              <input
                type="email"
                id="email"
                className="border-gray-300 mt-1 w-full rounded-sm border px-2 py-1.5 text-13"
                placeholder="Enter email"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="bg-gray-200 hover:bg-gray-300 rounded-sm px-3 py-1.5 text-11"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="bg-blue-500 hover:bg-blue-600 rounded-sm px-3 py-1.5 text-11 text-on-color"
              >
                Submit
              </button>
            </div>
          </form>
        </Popover.Panel>
      </Popover>
    </Centered>
  );
};

export const WithList = () => {
  const [open, setOpen] = React.useState(true);
  return (
    <Centered>
      <Popover open={open} onOpenChange={setOpen}>
        <Popover.Button className={BUTTON}>Show Options</Popover.Button>
        <Popover.Panel initialFocus={false} className="border-gray-200 shadow-lg w-56 rounded-lg border bg-white">
          <div className="p-2">
            <h3 className="text-gray-500 px-2 py-1.5 text-11 font-semibold">Options</h3>
            <button className="hover:bg-gray-100 w-full rounded-sm px-2 py-1.5 text-left text-13">Option 1</button>
            <button className="hover:bg-gray-100 w-full rounded-sm px-2 py-1.5 text-left text-13">Option 2</button>
            <button className="hover:bg-gray-100 w-full rounded-sm px-2 py-1.5 text-left text-13">Option 3</button>
          </div>
        </Popover.Panel>
      </Popover>
    </Centered>
  );
};

// Mirrors the ColorPicker story (uncontrolled Popover) with the panel open by default.
export const ColorPicker = () => {
  const [selectedColor, setSelectedColor] = React.useState("#3b82f6");
  const colors = ["#ef4444", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ec4899", "#6b7280", "#000000", "#ffffff"];
  return (
    <Centered>
      <Popover defaultOpen>
        <Popover.Button className="border-gray-300 hover:bg-gray-50 flex items-center gap-2 rounded-sm border bg-white px-4 py-2">
          <div className="h-4 w-4 rounded-sm" style={{ backgroundColor: selectedColor }} />
          <span className="text-13">Pick Color</span>
        </Popover.Button>
        <Popover.Panel initialFocus={false} className="border-gray-200 shadow-lg w-48 rounded-lg border bg-white p-3">
          <h3 className="mb-2 text-11 font-semibold">Select Color</h3>
          <div className="grid grid-cols-5 gap-2">
            {colors.map((color) => (
              <button
                key={color}
                onClick={() => setSelectedColor(color)}
                className="h-8 w-8 rounded-sm border-2 transition-transform hover:scale-110"
                style={{
                  backgroundColor: color,
                  borderColor: selectedColor === color ? "#000" : "transparent",
                }}
              />
            ))}
          </div>
        </Popover.Panel>
      </Popover>
    </Centered>
  );
};
