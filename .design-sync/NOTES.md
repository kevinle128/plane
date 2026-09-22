# design-sync notes: @plane/propel

Repo-specific facts a re-sync needs. One bullet per gotcha. `[GENERAL]` marks
items that apply beyond a single component.

## Setup

- `[GENERAL]` Install with `pnpm i --frozen-lockfile` at the repo root (pnpm 11.10.0 pinned via `packageManager`).
  The first sync found `pnpm-lock.yaml` internally inconsistent: the `apps/space` importer still resolved
  `@makeplane/propel@0.2.0` while the catalog and every other importer resolved `0.3.0`. Fixed by a one-line
  edit of that importer's `version:` line (the `0.3.0` snapshot with the same peer suffix already existed).
- `[GENERAL]` Build with `pnpm -F "@plane/propel..." build` (the trailing `...` builds the workspace
  deps `@plane/utils`, `@plane/hooks`, `@plane/constants`, `@plane/types`).
- `[GENERAL]` Reference storybook (both steps, every time the DS source or stories change):
  `(cd packages/propel && npx storybook build -c .storybook -o "$(git rev-parse --show-toplevel)/.design-sync/sb-reference") && node .design-sync/inject-reference-fonts.mjs`.
  39 story titles / 396 stories at the first sync. `iframe.html` is ~18 KB when the build succeeded.
- `[GENERAL]` Verification commands (repo root). The story cap MUST be raised - the default is 6 and the
  first sync graded every story (up to 22 per component) at cap 24; a run without the flag silently
  verifies only the first 6 stories of each re-captured component:
  `node .ds-sync/resync.mjs --config .design-sync/config.json --node-modules packages/propel/node_modules --entry packages/propel/dist/index.js --out ./ds-bundle --remote .design-sync/.cache/remote-sync.json`
  then, for anything it lists under `pendingGrade`:
  `node .ds-sync/storybook/compare.mjs --out ./ds-bundle --storybook-static .design-sync/sb-reference --components <A,B> --max-stories 24`.
- `[GENERAL]` Converter deps live in `.ds-sync/` (`npm i esbuild ts-morph @types/react playwright` +
  `npx playwright install chromium`). The fork in `.design-sync/overrides/dts.mjs` imports `ts-morph`
  bare, so on a fresh clone recreate the symlink: `ln -sfn ../.ds-sync/node_modules .design-sync/node_modules`.
- `[GENERAL]` `--node-modules packages/propel/node_modules` (pnpm links react / react-dom / @types/react there).
- `[GENERAL]` Machine-local: the user's global Claude hook (`~/.claude/hooks/scout-block.cjs`) blocks any shell
  command whose text contains `dist` or `node_modules`. `~/.claude/.ckignore` carries `!node_modules` and
  `!dist` exceptions added for this sync; without them every converter command is blocked.

## Entry / types (the repo's main strangeness)

- `[GENERAL]` `@plane/propel` exports subpaths only (`./button`, `./dialog`, ...): no `.` export, no `main`,
  no `types`. The converter needs one JS entry and one `.d.ts` entry. Solution, all inside `.design-sync/`:
  - `gen-entry.mjs` writes `packages/propel/dist/index.js` and `dist/index.d.ts` barrels (derived from
    `package.json` `exports`) after each package build; `buildCmd` chains it.
  - `overrides/dts.mjs` is a fork of the converter's `lib/dts.mjs` with two edits, both marked
    `FORK (propel)`: (1) in `projectFor`, when `<pkgDir>/index.d.ts` (the default types entry) doesn't
    exist, use `<typesRoot>/index.d.ts` instead (`findTypesRoot` already lands on `dist/` because tsdown
    emits shared `.d.ts` chunks there); (2) in `typeText`, normalise `React$N.` to `React.` - tsdown's
    `.d.ts` chunks import react under per-chunk aliases (`React$1`, `React$2`) and the checker printed them
    verbatim into 17 `<Name>.d.ts` files, where only `React` is declared.
  - Alternative the maintainers could choose instead: add a root barrel (`src/index.ts`, tsdown entry,
    `"."` export, `"types"`) to the package itself. That is a public-contract change, so it was not made here.
- One type-name collision across subpaths: `TPlacement` (menu + utils). Type-only, harmless for the barrel.
- `dtsPropsFor.Icon` is hand-written: `Icon.name` is `keyof typeof ICON_REGISTRY` (75 dotted keys such as
  `"action.add"`), which the extractor collapsed to `unknown`. The JSDoc lists every key; regenerate it from
  `packages/propel/src/icons/registry.ts` when icons are added (`grep -o '"[a-z0-9.-]*":' registry.ts`).
- `dtsPropsFor.Button` is hand-written too: Button's dist type is `React$1.ForwardRefExoticComponent<
React$1.ButtonHTMLAttributes<...> & VariantProps<...>>`, so its inherited members are printed from
  @types/react's own scope as bare `CSSProperties` / `ReactElement` / `JSXElementConstructor` (the fork's
  `React$N.` regex cannot reach them - Button is the only affected component). Re-derive the body from
  `packages/propel/src/button/helper.ts` when the variant/size unions change.
- `readmeHeader` points at `conventions.md` (the design-agent conventions header stitched into README.md).
  Every class/token/prop it names was grepped against `ds-bundle/_ds_bundle.css` and the built `.d.ts`
  files at the first sync; re-validate it against a fresh build before every upload (base SKILL.md rule).

## Story imports

- `[GENERAL]` Story files import components by kebab-case relative path (`./button`, `./root`, `./core`,
  `./index`). The converter's rule 2 matches resolved file/dir names against PascalCase exports, so none of
  these would shim to the shipped bundle and every preview would compile a second copy from source.
  `storyImports.shim: ["/packages/propel/src/"]` forces the root-namespace shim for everything under src;
  `storyImports.bundle` exempts `icons/constants` (its `*IconsMap` objects aren't package exports).
- `separator/` has a story (`Components/Separator`) but the component is not in `package.json` `exports`
  nor the tsdown entries, so it never ships. Excluded via `titleMap`.
- `design-system/design-system-philosophy.stories.tsx` (`Design System/Philosophy`) is a docs page rendered
  as a story, not a component. Excluded via `titleMap`.
- `empty-state/assets-showcase.stories.tsx` (`Components/EmptyState/Assets Showcase`) is an asset gallery;
  its title falls through to the `EmptyState` export, so `titleMap.EmptyState: null` excludes it. The real
  previews are `EmptyStateCompact` / `EmptyStateDetailed` (mapped from the `Compact` / `Detailed` segments).
- `Icons` (single-segment title) maps to the `Icon` registry component so the icon gallery ships as its card.
- `@makeplane/propel/icons` (external npm package) is merged onto the global via `extraEntries`: components
  and stories both import from it.

## Bundle runtime / styling

- `[GENERAL]` `@plane/constants` (bundled workspace dep) reads `process.env.VITE_*` at module scope
  (`packages/constants/src/endpoints.ts`). Vite/Storybook define `process.env` at build time; the converter
  only defines `NODE_ENV`, so the first bundle threw `ReferenceError: process is not defined` on load and
  every card rendered empty (`[BUNDLE_EXPORT] 36/36 not a component`). Fix: `.design-sync/process-env-shim.mjs`
  listed FIRST in `extraEntries` (evaluates before every other module and defines an empty `process.env`).
- `[GENERAL]` Component CSS is Tailwind v4 compiled only by the Storybook build; the converter scrapes it
  (`[CSS_FROM_STORYBOOK]`, ~202 KB). No `cssEntry` needed. Tokens come from `@makeplane/propel/styles`
  through `@plane/tailwind-config/index.css`.
- `[GENERAL]` Fonts: the DS CSS references Inter Variable, IBM Plex Mono and Material Symbols Rounded but
  ships no `@font-face`; the apps load them from `@fontsource*` packages (`apps/web/app/root.tsx`).
  `extraFonts` points at those packages through `apps/web/node_modules/`. Material Symbols ships weight
  400 only (`400.css`, the only weight the shipped CSS uses; the app loads `index.css` = 100-400).
  The reference Storybook loads no fonts either, so `.design-sync/inject-reference-fonts.mjs` links the same
  files into `sb-reference/iframe.html` - re-run it after every reference rebuild or grading compares
  fallback fonts on the left against real fonts on the right.
- `[TOKENS_MISSING]` (19 vars) is expected: `--custom-*` are only defined under `[data-custom-theme=true]`
  (app-side custom themes); the rest (`--popup-height`, `--accordion-panel-height`, `--active-tab-*`, ...)
  are set at runtime by base-ui / the components. Render check passes 36/36.
- Card modes: 15 components use `cardMode: "column"` (stories wider than a grid cell), `ModalPortal` uses
  `single` + `primaryStory: Default` (fixed-position content). Presentation-only; grades unaffected.

## Harness behaviour (learned in the fan-out waves)

- `[GENERAL]` Fork/config edits and the full rebuild must land TOGETHER, before a wave launches. Editing
  `.design-sync/overrides/*.mjs` (or provider/storyImports/extraEntries) after the stamped build makes
  `preview-rebuild.mjs` refuse every targeted rebuild with `[CONFIG_STALE]` for every subagent; only a full
  `package-build.mjs` re-stamps. Fork bytes are in the GLOBAL grade slice, so any fork edit - even a
  `.d.ts`-only one like the `React$N.` normalization - re-keys every component and clears every grade.
- `[GENERAL]` Storybook's `parameters.layout: "centered"` is not emulated: the harness mounts `?story=` in a
  block `div.ds-single` at the top-left, so `w-full` / block-level roots (Card, Table, Calendar,
  AnimatedCounter) fill the 852px mount while Storybook shrink-wraps them, and anchored overlays with
  `side="top"/"left"` collision-flip. Container framing, graded `match` under the "judge the component"
  clause; do NOT wrap a generated preview per component to fake it (it would shadow a harness fix).
  Owned overlay previews (Popover, Tooltip) use an inline-styled centred frame (`minHeight: 60vh`) instead.
- `[GENERAL]` Mount-time-open overlays get Chromium's `:focus-visible` outline on whatever base-ui focuses
  (no trusted pointer event precedes the programmatic focus); a real click never shows it. Knobs used:
  `initialFocus={false}` on `Popover.Panel`; blur the first focus after opening (ContextMenu); popups with
  `outline-none` (Combobox, Menu) need nothing. Dialog's accepted preview shows it on its Cancel button.
- `[GENERAL]` Overlays with no open prop are opened the way a user does, from a mount `useEffect`
  (Tooltip and the Menu submenu hover defer one `requestAnimationFrame` because base-ui attaches its
  native listeners a commit after the trigger ref lands; Menu's trigger click and ContextMenu's
  `contextmenu` dispatch synchronously in the effect): Tooltip dispatches `mouseenter`/`mousemove`
  (base-ui useHover rest timer; `openDelay: 0` on args-driven stories), Menu dispatches
  pointerdown/mousedown/click (useClick opens on `mousedown`), ContextMenu
  dispatches a `contextmenu` MouseEvent on the trigger (`defaultOpen` works but anchors at (0,0) because
  `ContextMenuRoot` seeds a 0x0 anchor rect). Combobox forwards `open`; Popover stories are hand-mirrored
  with `useState(true)`; ModalPortal inlines the story's module-local `ModalDemo` open.
- `[GENERAL]` Gated overlays are verified numerically as well as by eye: `.design-sync/.cache/tools/wave2-e/probe.mjs`
  (gitignored) opens a Storybook story the way a user would (click / hover / contextmenu) and dumps popup
  rects; the preview side dumps the same. Every Popover/Tooltip story matched rect-for-rect.
- `[GENERAL]` One pointer at a time: a multi-trigger story hovered on every trigger paints a composite no
  user can produce (overlapping tooltips) - open the first trigger only, unless the popups sit apart and
  the story exists to show them together (Tooltip `AllPositions`, nested ContextMenu submenus). Hover-opened
  submenus (Menu `WithSubmenu`, `ComplexMenu`) are opened per frame until `aria-expanded`, then the active
  element is blurred to drop the focus ring (base-ui keeps hover-opened submenus open on blur). Combobox
  `CustomEmptyMessage` seeds `searchQuery="ember"` because the empty message only renders on a no-match query.
- `[GENERAL]` `useArgs()` gating is not only an overlay thing: Collapsible (`isOpen`) and Switch (`value`)
  read state from `useArgs()` in `meta.render`, so `DefaultOpen` / `Checked` mount closed/unchecked. Owned
  previews mirror `meta.render` seeded from the story args. Delete those files if the `useArgs` stub is
  ever made real.
- `[GENERAL]` EmojiPicker / EmojiReactionPicker: `defaultOpen` is the default TAB, not popover state; every
  `render()` hardcodes `useState(false)`, so hand-mirrored open stories were required. frimousse fetches
  emojibase data from a CDN at mount - an open emoji grid needs network on both sides; an empty grid on a
  later capture is a network artefact. Material tab renders real Material Symbols glyphs (weight-400 face
  from `extraFonts` satisfies `use-font-face-observer`).
- `[GENERAL]` TabNavigationList `close` (capture artefact, not a DS defect): the active-item pill is a
  framer-motion WAAPI animation synced to `performance.now()`; `compare.mjs`'s fixed clock keeps ticking
  across navigations while `document.timeline` restarts per document, so on the 2nd+ navigation of the
  reused page the animation has a negative `currentTime` when `animations:'disabled'` cancels it, and the
  inline `opacity:0` stays. A fresh-page capture with identical stabilisation shows the pill. Storybook's
  side shows the same desync and rendered by timing luck. Harness-level (`.ds-sync/storybook/compare.mjs`,
  skill code - reported, not patched); only TabNavigation uses framer-motion in this DS.
- `[GENERAL]` Pixel-sampling tips: alpha fills (`bg-accent-primary/10`) composite differently over the grey
  Storybook canvas vs the white preview page - judge opaque colours; fills equal to the canvas colour
  (`bg-layer-3`, the Tabs track, the Switch track) are invisible on the left and visible on the right;
  `pair-sheet.mjs` trims to non-white pixels, so a story whose only fill is a non-theme palette class
  collapses to its text and looks smaller - check a sibling with a theme fill or the raw `__ds.png`.
- `[GENERAL]` `[REFERENCE_STALE?]` fires once on the first capture after any full build that follows a
  fork/config edit (bundle bytes moved, DS source didn't). Benign when `packages/propel` is git-clean.
- `[GENERAL]` Re-running `inject-reference-fonts.mjs` rewrites `sb-reference/iframe.html`, so the next
  driver run reports `verification.canary` with `trigger: "reference_drift"` and spot-checks ~5 carried
  components (grades kept). Confirm their sheets and move on - seen on the first no-change re-sync
  (2026-09-22): all five identical to the recorded grades, `upload.any: false`.
- `[GENERAL]` White-on-white stories (only ink is `text-on-color` on a non-theme fill) cannot be proven
  from images - DOM-probe both sides (text, color, bg, box size) and record it in the grade note.
  Components under ~30px (Switch) need an upscaled crop to judge; the wave-2 batches left
  `probe.mjs` / `probe-sb.mjs` / `pair-zoom.mjs` under `.design-sync/.cache/tools/wave2-f/` (gitignored).
- `[GENERAL]` The shipped CSS is Storybook's Tailwind output, so only classes the repo already uses exist:
  arbitrary values (`min-h-[60vh]`) and stock palette names do nothing in owned previews or in designs.
- Story-authoring / DS notes (both sides, not sync defects): EmojiReactionPicker nests a `<button>` in
  `Popover.Button` (React warning); `Menu.SubMenu` trigger has `className=""` so its chevron wraps;
  `SearchDisabled` emoji stories re-enable + focus the search input on mount (`EmojiRoot` effect);
  Tooltip `OnDisabledButton` never opens (Chromium sends no mouse events to a disabled button);
  Menu `CustomStyles` passes non-theme `border-purple-300`, and tailwind-merge drops the component's
  `border-strong` for it (dark currentColor border); `ContextMenu.Content` defaults `side="bottom"`, so
  submenus that reuse it inside `Submenu.Portal` open below and overlap the parent menu
  (`packages/propel/src/context-menu/context-menu.tsx:55`) - worth relaying to the DS maintainers.

## Verification

- `[GENERAL]` Storybook renders on the DS canvas colour (`body { @apply bg-canvas }` from
  `@plane/tailwind-config`), while the generated card frame paints `body{background:#fff}`. Every compare
  pair therefore shows a light-grey backdrop on the left and white on the right - framing, not a component
  difference. Judge the component only.
- `[GENERAL]` The compare sheet shrinks the 900x675 preview capture so components look tiny next to the
  tightly cropped Storybook shot. `.design-sync/.cache/tools/pair-sheet.mjs <Name>` (machine-local, gitignored)
  renders a 1:1 composite with the preview trimmed to its content - use it instead of squinting. Its
  canvases are capped at 560px wide, so a `w-full` preview is scaled down on the right while the
  shrink-wrapped Storybook root stays 1:1 - confirm type/digit size on the raw `__ds.png` before grading.
- Button: all 19 stories graded `match` from images (cap raised to 19 for the solo component).
- `[GENERAL]` Interaction-gated overlays: Dialog, Popover, Combobox and ModalPortal stories keep the overlay
  closed (`open: false` in meta args; opened via `useArgs()` or `useState(args.open)` on a click). The
  `storybook/preview-api` stub makes `useArgs()` return `{}`, so useArgs-driven stories can never open.
  Pattern (see `.design-sync/previews/Dialog.tsx`): copy the generated wrapper, add an `extraArgs` parameter
  to `compose()` and pass `{open: true}` for useState-driven stories; mirror useArgs-driven stories by hand
  with the overlay open; import components from `@plane/propel` (root shim). Grade under the rubric's
  gated-reference clause (judge the open render on its own, note the gating). Stories whose open state
  is picked by a click among several: Dialog `AllWidths` is SKIPPED (`cfg.overrides.Dialog.skip`, first
  sync) while ModalPortal `Positions`/`Widths` and Combobox `Disabled` are composed unchanged and graded
  `match` on their closed trigger row - both are rubric-legal; keep each as it is (a `skip` change re-keys
  the component and costs a full build + re-grade) unless the story itself changes.
- `[GENERAL]` Stories that use Tailwind palette classes outside Plane's theme (`bg-blue-500`, `bg-red-500`,
  `text-gray-600`) render without those colours on BOTH sides (the theme doesn't define them) - e.g. the
  Dialog trigger/confirm buttons are white-on-white. Story authoring, not a DS defect; grade as match.
- `[GENERAL]` The preview side is captured at a fixed 900x700 viewport (`fullPage:false`), the Storybook
  side as its root element. Stories taller than 700px (Toast `DesignTokens`, 1309px) are clipped on the
  right; confirm the full page renders (`scrollHeight`) and grade the visible portion.
- `[GENERAL]` `?story=` takes the EXPORT name (`DesignTokens`), not the display name (`Design Tokens`).
- Solo set graded match: Button 19/19, Avatar 15/15, Toast 22/22, EmptyStateDetailed 14/14, Dialog 8/8
  (AllWidths skipped). `[ASSETS_BLOCKED]` did not fire (Avatar loads i.pravatar.cc on both sides).
- `[RENDER_THIN]` on ContextMenu and Menu (measured height 0px) is benign: their owned previews open the
  menu, and base-ui portals the popup to a fixed-position positioner outside the measured story root.
  Screenshots (`_screenshots/components__ContextMenu.png`, `__Menu.png`) show the open menu. Expected forever.

## Re-sync risks (watch-list for the next run)

- **Owned previews are tied to story internals.** `.design-sync/previews/*.tsx` mirror `meta.render` /
  story JSX by hand (Dialog, Popover, Combobox, ModalPortal, EmojiPicker, EmojiReactionPicker, Collapsible,
  Switch) or drive base-ui through dispatched DOM events (Tooltip, Menu, ContextMenu). A story edit shows
  up as `[STORY_CHANGED]` and the owned file must be updated by hand; a base-ui upgrade that changes the
  trigger event (`useClick` on `mousedown`, `useHover` rest timer, the `contextmenu` anchor) silently
  breaks the open state - re-grade those from images, don't trust carry-forward.
- **`useArgs()` stub.** Collapsible/Switch owned previews exist only because the `storybook/preview-api`
  stub returns `{}`. If the converter ever ships a real `useArgs`, delete those two files (they would
  shadow the corrected generated previews).
- **Fonts come from the web app's `@fontsource*` dependencies** (not from the DS package). A fontsource
  bump or an app-side font change (`apps/web/app/root.tsx`) moves the shipped faces;
  `inject-reference-fonts.mjs` hard-codes the same three packages and must be re-run after every
  reference rebuild.
- **`gen-entry.mjs` and the `dts.mjs` fork** depend on tsdown's dist layout (`dist/<sub>/index.js` plus
  shared `.d.ts` chunks with `React$N` aliases). A tsdown/rolldown upgrade or a root `.` export added to
  the package makes both redundant - remove the fork and `entry` then (fork removal re-keys every grade).
- **`process-env-shim.mjs`** exists because `@plane/constants` reads `process.env` at module scope; if that
  package moves to `import.meta.env`, the shim becomes dead weight (harmless).
- **Partially verified:** TabNavigationList is `close` (capture-harness artefact on the framer-motion pill;
  the product card renders it). Stories taller than 700px were graded on the visible portion. ModalPortal
  `Positions`/`Widths` and Combobox `Disabled` are graded on their closed trigger rows (no static open
  state). Dialog `AllWidths` is skipped.
- **Network at grade time:** Avatar (i.pravatar.cc) and the emoji pickers (emojibase CDN via frimousse)
  need egress on BOTH capture sides; `[ASSETS_BLOCKED]` or an empty emoji grid means a sandboxed shell,
  not a DS regression.
- **Toolchain assumed:** node 22.22, pnpm 11.10, storybook 10 (`@storybook/react-vite`), Playwright
  chromium-headless-shell 153, converter scripts from bundled-skills 2.1.274.
