// Owned preview: a context menu only opens on right-click / long-press, so the
// static story render is just the trigger area. Each story is mirrored verbatim
// and opened the way a user opens it: a `contextmenu` event on the trigger
// (base-ui reads the pointer position from it as the menu anchor - the root's
// `open` prop alone anchors the menu at the viewport origin). Submenus take
// `defaultOpen` (SubmenuRoot accepts it) so their real placement shows too.
import * as React from "react";
import { ContextMenu } from "@plane/propel";
import {
  ArchiveOutline,
  ChevronRightOutline,
  CopyOutline,
  DeleteOutline,
  DownloadOutline,
  EditOutline,
  ShareOutline,
  StarOutline,
} from "@makeplane/propel/icons";

const TRIGGER_BOX =
  "flex h-[150px] w-[300px] items-center justify-center rounded-md border border-dashed border-strong text-13";

// Dispatches the right-click on mount. base-ui then moves focus into the menu;
// with no pointer interaction before the mount Chromium paints its default
// :focus-visible outline on it - a ring a real right-click never shows - so
// that first focus is dropped.
function RightClicked({ children }: { children: React.ReactNode }) {
  const ref = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    // base-ui's Trigger is a block-level div; aim at the story's own box inside it.
    const trigger = ref.current?.firstElementChild as HTMLElement | null;
    const box = (trigger?.firstElementChild as HTMLElement | null) ?? trigger;
    if (!trigger || !box) return;
    const dropFocus = (e: FocusEvent) => {
      if (ref.current?.contains(e.target as Node)) return;
      (e.target as HTMLElement).blur();
      document.removeEventListener("focusin", dropFocus, true);
    };
    document.addEventListener("focusin", dropFocus, true);
    const r = box.getBoundingClientRect();
    trigger.dispatchEvent(
      new MouseEvent("contextmenu", {
        bubbles: true,
        cancelable: true,
        button: 2,
        clientX: r.left + r.width / 2,
        clientY: r.top + r.height / 2,
      })
    );
    return () => document.removeEventListener("focusin", dropFocus, true);
  }, []);
  return (
    <div ref={ref} style={{ display: "contents" }}>
      {children}
    </div>
  );
}

export const Default = () => (
  <RightClicked>
    <ContextMenu>
      <ContextMenu.Trigger>
        <div className={TRIGGER_BOX}>Right click here</div>
      </ContextMenu.Trigger>
      <ContextMenu.Portal>
        <ContextMenu.Content>
          <ContextMenu.Item>Back</ContextMenu.Item>
          <ContextMenu.Item>Forward</ContextMenu.Item>
          <ContextMenu.Item>Reload</ContextMenu.Item>
          <ContextMenu.Separator />
          <ContextMenu.Item>More Tools</ContextMenu.Item>
        </ContextMenu.Content>
      </ContextMenu.Portal>
    </ContextMenu>
  </RightClicked>
);

export const WithIcons = () => (
  <RightClicked>
    <ContextMenu>
      <ContextMenu.Trigger>
        <div className={TRIGGER_BOX}>Right click here</div>
      </ContextMenu.Trigger>
      <ContextMenu.Portal>
        <ContextMenu.Content>
          <ContextMenu.Item>
            <CopyOutline className="mr-2 h-4 w-4" />
            Copy
          </ContextMenu.Item>
          <ContextMenu.Item>
            <EditOutline className="mr-2 h-4 w-4" />
            Edit
          </ContextMenu.Item>
          <ContextMenu.Item>
            <DownloadOutline className="mr-2 h-4 w-4" />
            Download
          </ContextMenu.Item>
          <ContextMenu.Separator />
          <ContextMenu.Item>
            <ShareOutline className="mr-2 h-4 w-4" />
            Share
          </ContextMenu.Item>
          <ContextMenu.Item>
            <DeleteOutline className="mr-2 h-4 w-4 text-danger-primary" />
            <span className="text-danger-primary">Delete</span>
          </ContextMenu.Item>
        </ContextMenu.Content>
      </ContextMenu.Portal>
    </ContextMenu>
  </RightClicked>
);

export const WithSubmenus = () => (
  <RightClicked>
    <ContextMenu>
      <ContextMenu.Trigger>
        <div className={TRIGGER_BOX}>Right click here</div>
      </ContextMenu.Trigger>
      <ContextMenu.Portal>
        <ContextMenu.Content>
          <ContextMenu.Item>
            <CopyOutline className="mr-2 h-4 w-4" />
            Copy
          </ContextMenu.Item>
          <ContextMenu.Item>
            <EditOutline className="mr-2 h-4 w-4" />
            Edit
          </ContextMenu.Item>
          <ContextMenu.Separator />
          <ContextMenu.Submenu defaultOpen>
            <ContextMenu.SubmenuTrigger>
              <ShareOutline className="mr-2 h-4 w-4" />
              Share
              <ChevronRightOutline className="ml-auto h-4 w-4" />
            </ContextMenu.SubmenuTrigger>
            <ContextMenu.Portal>
              <ContextMenu.Content>
                <ContextMenu.Item>Email</ContextMenu.Item>
                <ContextMenu.Item>Message</ContextMenu.Item>
                <ContextMenu.Item>Copy Link</ContextMenu.Item>
              </ContextMenu.Content>
            </ContextMenu.Portal>
          </ContextMenu.Submenu>
          <ContextMenu.Separator />
          <ContextMenu.Item>
            <DeleteOutline className="mr-2 h-4 w-4 text-danger-primary" />
            <span className="text-danger-primary">Delete</span>
          </ContextMenu.Item>
        </ContextMenu.Content>
      </ContextMenu.Portal>
    </ContextMenu>
  </RightClicked>
);

export const DisabledItems = () => (
  <RightClicked>
    <ContextMenu>
      <ContextMenu.Trigger>
        <div className={TRIGGER_BOX}>Right click here</div>
      </ContextMenu.Trigger>
      <ContextMenu.Portal>
        <ContextMenu.Content>
          <ContextMenu.Item>
            <CopyOutline className="mr-2 h-4 w-4" />
            Copy
          </ContextMenu.Item>
          <ContextMenu.Item disabled>
            <EditOutline className="mr-2 h-4 w-4" />
            Edit (Disabled)
          </ContextMenu.Item>
          <ContextMenu.Item>
            <DownloadOutline className="mr-2 h-4 w-4" />
            Download
          </ContextMenu.Item>
          <ContextMenu.Separator />
          <ContextMenu.Item disabled>
            <ShareOutline className="mr-2 h-4 w-4" />
            Share (Disabled)
          </ContextMenu.Item>
          <ContextMenu.Item>
            <DeleteOutline className="mr-2 h-4 w-4 text-danger-primary" />
            <span className="text-danger-primary">Delete</span>
          </ContextMenu.Item>
        </ContextMenu.Content>
      </ContextMenu.Portal>
    </ContextMenu>
  </RightClicked>
);

export const OnFileCard = () => (
  <RightClicked>
    <ContextMenu>
      <ContextMenu.Trigger>
        <div className="w-64 cursor-pointer rounded-lg border border-subtle p-4 hover:bg-layer-1">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-sm bg-accent-primary text-16 text-on-color">
              📄
            </div>
            <div className="flex-1">
              <div className="font-medium">Document.pdf</div>
              <div className="text-13 text-placeholder">2.4 MB</div>
            </div>
          </div>
        </div>
      </ContextMenu.Trigger>
      <ContextMenu.Portal>
        <ContextMenu.Content>
          <ContextMenu.Item>
            <DownloadOutline className="mr-2 h-4 w-4" />
            Download
          </ContextMenu.Item>
          <ContextMenu.Item>
            <CopyOutline className="mr-2 h-4 w-4" />
            Copy Link
          </ContextMenu.Item>
          <ContextMenu.Item>
            <StarOutline className="mr-2 h-4 w-4" />
            Add to Favorites
          </ContextMenu.Item>
          <ContextMenu.Separator />
          <ContextMenu.Item>
            <ArchiveOutline className="mr-2 h-4 w-4" />
            Archive
          </ContextMenu.Item>
          <ContextMenu.Item>
            <DeleteOutline className="mr-2 h-4 w-4 text-danger-primary" />
            <span className="text-danger-primary">Delete</span>
          </ContextMenu.Item>
        </ContextMenu.Content>
      </ContextMenu.Portal>
    </ContextMenu>
  </RightClicked>
);

export const OnImage = () => (
  <RightClicked>
    <ContextMenu>
      <ContextMenu.Trigger>
        <div className="relative h-56 w-80 cursor-pointer overflow-hidden rounded-lg bg-layer-1">
          <div className="absolute inset-0 flex items-center justify-center text-placeholder">Image Placeholder</div>
        </div>
      </ContextMenu.Trigger>
      <ContextMenu.Portal>
        <ContextMenu.Content>
          <ContextMenu.Item>
            <DownloadOutline className="mr-2 h-4 w-4" />
            Save Image
          </ContextMenu.Item>
          <ContextMenu.Item>
            <CopyOutline className="mr-2 h-4 w-4" />
            Copy Image
          </ContextMenu.Item>
          <ContextMenu.Item>
            <CopyOutline className="mr-2 h-4 w-4" />
            Copy Image URL
          </ContextMenu.Item>
          <ContextMenu.Separator />
          <ContextMenu.Item>Open Image in New Tab</ContextMenu.Item>
        </ContextMenu.Content>
      </ContextMenu.Portal>
    </ContextMenu>
  </RightClicked>
);

export const OnText = () => (
  <RightClicked>
    <ContextMenu>
      <ContextMenu.Trigger>
        <div className="w-96 rounded-lg border border-subtle p-6">
          <h3 className="mb-2 text-16 font-semibold">Context Menu on Text</h3>
          <p className="text-tertiary">
            Right click anywhere on this text area to see the context menu. This demonstrates how context menus can be
            applied to text content areas.
          </p>
        </div>
      </ContextMenu.Trigger>
      <ContextMenu.Portal>
        <ContextMenu.Content>
          <ContextMenu.Item>
            <CopyOutline className="mr-2 h-4 w-4" />
            Copy
          </ContextMenu.Item>
          <ContextMenu.Item>
            <EditOutline className="mr-2 h-4 w-4" />
            Edit
          </ContextMenu.Item>
          <ContextMenu.Separator />
          <ContextMenu.Item>Select All</ContextMenu.Item>
        </ContextMenu.Content>
      </ContextMenu.Portal>
    </ContextMenu>
  </RightClicked>
);

export const NestedSubmenus = () => (
  <RightClicked>
    <ContextMenu>
      <ContextMenu.Trigger>
        <div className={TRIGGER_BOX}>Right click here</div>
      </ContextMenu.Trigger>
      <ContextMenu.Portal>
        <ContextMenu.Content>
          <ContextMenu.Item>New File</ContextMenu.Item>
          <ContextMenu.Item>New Folder</ContextMenu.Item>
          <ContextMenu.Separator />
          <ContextMenu.Submenu defaultOpen>
            <ContextMenu.SubmenuTrigger>
              Import
              <ChevronRightOutline className="ml-auto h-4 w-4" />
            </ContextMenu.SubmenuTrigger>
            <ContextMenu.Portal>
              <ContextMenu.Content>
                <ContextMenu.Item>From File</ContextMenu.Item>
                <ContextMenu.Item>From URL</ContextMenu.Item>
                <ContextMenu.Submenu defaultOpen>
                  <ContextMenu.SubmenuTrigger>
                    From Cloud
                    <ChevronRightOutline className="ml-auto h-4 w-4" />
                  </ContextMenu.SubmenuTrigger>
                  <ContextMenu.Portal>
                    <ContextMenu.Content>
                      <ContextMenu.Item>Google Drive</ContextMenu.Item>
                      <ContextMenu.Item>Dropbox</ContextMenu.Item>
                      <ContextMenu.Item>OneDrive</ContextMenu.Item>
                    </ContextMenu.Content>
                  </ContextMenu.Portal>
                </ContextMenu.Submenu>
              </ContextMenu.Content>
            </ContextMenu.Portal>
          </ContextMenu.Submenu>
          <ContextMenu.Separator />
          <ContextMenu.Item>
            <DeleteOutline className="mr-2 h-4 w-4 text-danger-primary" />
            <span className="text-danger-primary">Delete</span>
          </ContextMenu.Item>
        </ContextMenu.Content>
      </ContextMenu.Portal>
    </ContextMenu>
  </RightClicked>
);

export const WithKeyboardShortcuts = () => (
  <RightClicked>
    <ContextMenu>
      <ContextMenu.Trigger>
        <div className={TRIGGER_BOX}>Right click here</div>
      </ContextMenu.Trigger>
      <ContextMenu.Portal>
        <ContextMenu.Content>
          <ContextMenu.Item>
            <CopyOutline className="mr-2 h-4 w-4" />
            Copy
            <span className="ml-auto text-11 text-placeholder">⌘C</span>
          </ContextMenu.Item>
          <ContextMenu.Item>
            <EditOutline className="mr-2 h-4 w-4" />
            Edit
            <span className="ml-auto text-11 text-placeholder">⌘E</span>
          </ContextMenu.Item>
          <ContextMenu.Item>
            <DownloadOutline className="mr-2 h-4 w-4" />
            Download
            <span className="ml-auto text-11 text-placeholder">⌘D</span>
          </ContextMenu.Item>
          <ContextMenu.Separator />
          <ContextMenu.Item>
            <DeleteOutline className="mr-2 h-4 w-4 text-danger-primary" />
            <span className="text-danger-primary">Delete</span>
            <span className="ml-auto text-11 text-placeholder">⌘⌫</span>
          </ContextMenu.Item>
        </ContextMenu.Content>
      </ContextMenu.Portal>
    </ContextMenu>
  </RightClicked>
);
