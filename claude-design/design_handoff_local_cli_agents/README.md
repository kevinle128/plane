# Handoff: Local CLI agents in Plane work items

Spec: `spec-plane-local-cli-agents`. Repo context: see `github.md` in this bundle.

## Overview

Lets a workspace member mention a harness (`@Claude`, `@Codex`, `@Grok`, `@Omp`) in a work-item comment. A worker on the member's own machine runs the matching CLI against the project's repository clone, streams progress back, and posts a single conclusion into the work item's activity. Humans steer, approve writes, and merge; the agent never pushes to the default branch.

Scope in this design:

1. Work-item detail with agent run cards in the activity feed.
2. Agent run side panel (timeline, plan, queue, composer, stop/steer, HITL permission).
3. Workspace settings → Integrations: GitHub (connect via device flow, detail page) and the four harnesses (connect / connected / failed, model list).
4. New project modal with a GitHub repository picker.
5. Error states: stale run, worker at capacity.

## About the design files

`Agent Runs.dc.html` is a **design reference built in HTML**, not production code. Recreate it in Plane's web app (Next.js/React, MobX stores, `@plane/propel` + `@plane/ui`, Tailwind with Plane's semantic tokens). Do not copy the HTML. Reuse existing Plane components wherever they exist (settings chrome, work-item detail, activity feed, comment editor, Propel Button/Badge/Avatar/Switch/Spinner/Input).

The prototype loads the real published `@plane/propel@1.4.2` bundle, so every Propel component you see is the real component with real props.

## Fidelity

**High-fidelity.** Colors, type, spacing and states are final and expressed entirely in Plane semantic tokens (`var(--bg-*)`, `var(--txt-*)`, `var(--border-color-*)`) and Propel utility classes. Match 1:1; there are no custom hex colors.

Anything already existing in Plane (top bar, sidebar, breadcrumb, work-item properties panel, settings nav) is drawn only as context — use the real Plane implementation, not the mock.

## Naming

- **Harness**: a supported CLI (Claude Code, Codex CLI, Grok CLI, Omp). Settings group title: `HARNESSES`.
- **Agent**: the mentionable identity of a harness inside a workspace (`@Claude`). One harness = one agent.
- **Run**: one invocation triggered by a mention. Has a status, a timeline, a plan, a queue.
- **Worker**: the process on the member's machine that invokes the CLI. Never surfaced by name in UI except in error copy ("worker at capacity").

Do not use "connect agent" as a separate flow. Connecting happens per harness on the harness detail page.

## Scenes (mock switcher, top strip)

`1 Mention · 2 In progress · 3 Elicit · 4 Completed · 5 Code job + PR · 6 Permission · 7 Failed · 8 Stale · 9 Capacity · 10 Stopped to steer · 11 Integrations · 12 New project`

Switch scenes with the strip; the strip itself is not part of the product.

---

## Screen 1 — Work item detail with agent activity

Plane's standard work-item page (`/plane-ce/work-items/PLAN-214`). Only the activity feed changes.

### Run card (in activity)

One card per run, in chronological position. No split view; the user's request and the agent's status live in the same card.

Layout (bg `--bg-surface-1`, border 1px `--border-color-subtle`, radius `--radius-lg`, padding 12px):

- Row 1: Avatar 24px of the requester · `Kevin Le mentioned @Claude` (caption-sm, secondary) · timestamp right.
- Row 2: the request text verbatim (body-sm, primary).
- Row 3 (status strip): status icon 15px + label (see status table) · run kind pill (`Q&A · read-only clone` or `Code job · worktree`) · elapsed mono · `Open run →` link (link-primary) right-aligned.
- Row 4 (when the run has concluded): the conclusion, rendered as ordinary comment markdown. For code jobs, a PR line: `merge` icon success, PR title mono link, `Draft` pill, branch + diff stats mono tertiary, footnote "Humans merge. The agent never pushes to the default branch."

Only conclusions land in activity. Thoughts, tool calls and intermediate output stay in the panel.

### Status table (icon · label · color)

| status | icon (Material Symbols Rounded) | label | color token |
|---|---|---|---|
| created | hourglass_empty | Waiting for pickup | `--txt-tertiary` |
| in_progress | progress_activity (spin) | In progress | `--txt-accent-primary` |
| awaiting | pause_circle | Waiting for you | `--txt-warning-primary` |
| approval | lock_open_right | Permission needed | `--txt-warning-primary` |
| completed | check_circle | Completed | `--txt-success-primary` |
| failed | error | Failed | `--txt-danger-primary` |
| stale | schedule | Stale | `--txt-warning-primary` |
| stopped | stop_circle | Stopped | `--txt-secondary` |

Badge variant mapping for Propel `Badge`: in_progress→brand, awaiting/approval/stale→warning, completed→success, failed→danger, stopped/created→neutral.

### Mention composer (scene 1)

Plane's comment editor. Typing `@` lists people **and** agents. Agent rows: Propel `AgentOutline` icon in a 20px accent-subtle circle, name, mono handle, and a right-aligned health tag (Connected / Not connected / Connection failed — same values as Settings). Not-connected agents are still listed but disabled with the tag as reason.

---

## Screen 2 — Agent run panel

Absolutely positioned drawer on the right of the work-item page, `top:0; right:0; bottom:0`, z-index above the page, border-left 1px subtle, bg `--bg-surface-1`, shadow `shadow-overlay-200`.

- **Resizable**: 7px invisible grab strip at the left edge, `cursor: col-resize`. Width clamps 380–960px, default 540. Persist per user.
- Column layout: header (shrink-0) → timeline (flex-1, scroll) → composer block (shrink-0).

### Header (px 16, py 12, border-b subtle)

- 24px agent glyph (Propel `AgentOutline` in `bg-layer-2` rounded-md with shadow-raised-100) · `Claude` body-sm-semibold · run kind pill.
- Right: Propel `Badge` (status) · elapsed mono · close `IconButton`.
- Second line (caption-sm tertiary, mono): `cwd /srv/agents/mirrors/plane · read-only · OS sandbox` and `started 14:02 today · N activities`.
- Optional banner (full width, 8px/12px, radius-md): warning for approval/stale, danger for failed, neutral for stopped. Copy below.

### Timeline

Vertical list of groups. Each group: 24px glyph column (icon in `bg-layer-2` rounded-md, 1px subtle border) + content. A 1px `--border-color-subtle` connector between glyphs.

Entry kinds and their default state:

| kind | glyph | default | content |
|---|---|---|---|
| user | requester avatar | expanded | request text |
| thought | `psychology` | **collapsed** to one line, chevron to expand | italic body-sm secondary |
| tool | `terminal` / `source` | **collapsed**, header shows tool + target mono | pre block, mono 12px |
| result | `check` | **expanded** | markdown |
| elicitation | `help` | expanded | question + option buttons (repo remote + cwd), warning-subtle card |
| permission | `lock_open_right` | expanded | see HITL below |
| error | `error` | expanded | danger-subtle card, hint mono |
| pr | `merge` | expanded | PR card as in activity |
| streaming tail | `bolt` | — | Spinner 14px + italic "working…" |

Collapsed thoughts/tools keep the panel readable; the full audit is still there on expand. Nothing in the panel is duplicated into activity except results.

### HITL permission card

Shown before the agent's **first write** in a worktree, and again for any escalation (network, new path).

Warning-subtle card: header `lock_open_right` + `Permission needed · <title>` + time · command in mono box (`bg-surface-1`) · scope path mono + risk pill (`bg-layer-1`) · buttons: `Allow for this run` (primary), `Allow once` (secondary), `Deny` (tertiary/danger text).

After a decision the card stays in the timeline with the decision stamped (`Allowed for this run · 14:07 · Kevin Le`) — approval history is part of the audit.

### Composer block (px 16, py 12, border-t subtle)

One rounded container (`bg-surface-2`, 1px subtle, radius-lg, overflow hidden) holding, top to bottom, each separated by a 1px subtle hairline:

1. **Plan** (only when the run has a plan)
   - Header row, min-height 30px, px 12: `ToDoOutline` 14px tertiary · `Plan` body-sm-semibold primary · `2 of 4 · ~1m left` caption tertiary · chevron right-aligned. Click toggles.
   - Rows (min-height 30px, px 12, border-t subtle): 16px glyph cell · label caption-sm · right meta.
     - done: tick 12px success inside 14px `--bg-success-subtle` circle; label `--txt-secondary`.
     - doing: Propel `Spinner` 10px accent inside 14px `--bg-accent-subtle` circle; label primary, weight 500; meta `now` mono.
     - todo: 10px circle, 1px **dashed** `--border-color-strong`; label tertiary.
2. **Queue** (only when ≥1 message queued)
   - Header row identical in structure: `ClockOutline` · `Queue` body-sm-semibold · `1 waiting · sent after this step` · chevron.
   - Rows: 16px numbered ring (1px dashed strong, 9px mono) · text caption-sm primary · `Send now` link-primary · `close` 14px (hover danger).
3. **Input row** (px 12, py 8): Propel `Input` transparent, placeholder depends on status (`Queue a message for Claude…` while in_progress, otherwise `Reply to Claude…`) · **Send** 28×28 square, `bg-accent-subtle-hover`/accent text, hover fills accent · **Stop** 28×28 square (only when `canStop`): 1px subtle border, `bg-surface-1`, 9px hollow square glyph 1.5px stroke; hover: danger border + danger-subtle bg + danger glyph. Tooltip: "Stop the current action and take over — the sandbox is kept".
4. **Live line** (only when `canStop`; px 12, pb 7): 5px accent dot with a 1.6s breathing opacity animation · status sentence caption tertiary · elapsed mono right.

Status sentences: in_progress → "Working — messages queue until the current step lands"; approval → "Holding before its first write, waiting on your approval"; awaiting → "Waiting on you — the sandbox is kept alive".

### Behavior

- Enter sends. If status is in_progress, the message is **queued** (appended to Queue) rather than sent; the worker drains the queue between steps. `Send now` interrupts the current step and sends immediately.
- **Stop** = interrupt to steer, not terminate. Opens a small confirm dialog (Propel `Dialog`): "Stop and take over? The current step is interrupted. The sandbox and worktree are kept, and the message queue is cleared." Buttons: `Stop` (danger), `Cancel`. On confirm: status → stopped, queue cleared, banner "Stopped by Kevin Le at 14:10. Reply to continue in the same sandbox." Composer stays enabled.
- Stale (scene 8): banner warning "No heartbeat from the worker for 7m 36s. The run is kept; it resumes when the worker reconnects." Actions: `Retry pickup`, `Mark failed`.
- Capacity (scene 9): banner "The worker is at its concurrency limit (2 of 2). This run starts when a slot frees up." Card shows created/waiting state.
- Failed (scene 7): error entry with exit code and hint; conclusion in activity says "Run failed" + one-line reason.

---

## Screen 3 — Workspace settings → Integrations

Uses Plane's real settings chrome (top bar, workspace settings sidebar with Integrations selected, breadcrumb `Mini Workspace / Settings / Integrations`, centered content `max-width 56.25rem`, padding 36px 1.35rem, `gap 24px`). No extra internal nav.

Page header: `Integrations` h3-medium + one-line blurb (body-xs tertiary, max-width 620px).

### Groups

Group title: `text-11 font-semibold text-tertiary`, letter-spacing .06em, uppercase.

**ESSENTIALS** — `GitHub` only (GitLab hidden for now).

**HARNESSES** — four cards: Claude Code, Codex CLI, Grok CLI, Omp.

### Card (button)

`flex: 1 1 210px; min-width 190px; max-width 260px`, bg surface-1, 1px subtle, radius-lg, padding 12px, gap 8px; hover border strong.

- Row: 28px icon square (`bg-layer-2`, 1px subtle) · name body-sm-semibold · right tag caption-sm.
- Blurb caption-sm secondary.
- Meta row: mono tertiary (`claude-code 2.1.4`) · right `Configure` link (harness cards only).

Tag values and colors: `Connected` success · `Not connected` tertiary · `Connection failed` danger · `Connecting` accent · `Connect` accent (for GitHub when not installed).

Harness tags are **derived from live connection state**, not stored copy.

### GitHub — not connected

Centered empty state in a surface-1 card (px 24, py 32): `GithubIcon` in 32px `bg-layer-1` circle · "Install the GitHub integration" body-md-semibold · blurb · a 3-row checklist box (tick icons) · `Authenticate with GitHub` primary lg · "I'll do this later" text.

Device flow state: surface-1 card with Spinner + "Waiting for GitHub" + "expires in 14:22"; paragraph explaining `github.com/login/device`; code `JQXK-7D24` in a mono h5 box, letter-spacing .18em; `I entered the code` link; `Cancel`.

### GitHub — detail page (click the Connected card)

Breadcrumb `… / GitHub`. Page title `GitHub`, blurb "Bind projects to repositories, clone them on the Mini, and let agents open draft pull requests."

- Back link `← Integrations` (caption tertiary, arrow icon).
- Meta strip (surface-1 card, px 16 py 12, wrap, gap 24): `ENABLED BY` Avatar sm + name + date · `SCOPES` mono `contents:read · pull_requests:write` · `DOCS` link · `Disconnect` right (tertiary → danger hover).
- **Connections**: title body-sm-semibold + right `Connect organisation` secondary sm. List card: per installation row (px 16 py 12, border-b): 32px initials square `bg-layer-1` · login mono body-sm-medium · `Organisation · All repositories` caption tertiary · green 6px dot + `Connected` · `Remove`. Last row: "Your personal GitHub account" + "Connected · used to attribute pull requests you approve" + `Manage`.
- **Pull requests from agents**: title + blurb. List card rows with Propel `Switch` sm: "Open pull requests as drafts" (on), "Post run conclusions as PR comments" (off), "Branch format" with a dropdown button `agent/identifier` (mono).

### Harness detail page (click a harness card)

Breadcrumb `… / <Harness>`. Title = harness name; blurb from the harness. Back link `← Integrations`.

Header row: 32px `AgentOutline` circle accent-subtle · name body-md-semibold · subtitle caption tertiary (`claude-code 2.1.4 on the Mini · last run 12 min ago` when connected, CLI only when not) · right `Enabled` Switch.

Settings card (surface-1, 1px subtle, radius-lg), rows wrap, px 16 py 12, border-b subtle, label column `flex: 1 1 180px`:

1. **Connection** — label + tag pill (see states) · hint line · error detail mono in a `bg-surface-2` box (failed only) · right actions.
   - `Not connected`: hint "Installed on your machine. Connect to verify it and read the models it offers." · `Connect` primary sm.
   - `Connecting`: Spinner 14px · hint "Connecting and asking the agent for its model list."
   - `Connection failed`: row bg `--bg-danger-subtle`; hint "Plane reached the agent but it refused the session, so no models could be read."; detail `codex exited 1 · not logged in (provider returned 401). Sign in with codex login on your machine, then retry.` · `Retry` secondary sm.
   - `Connected`: hint "Verified. Runs go to this agent on your machine." · `Disconnect` text (tertiary → danger hover).
2. **Name** — Input, default harness name.
3. **Handle** — `@Claude`, mono; validation: unique per workspace, error border + message "An agent with this handle already exists in this workspace."
4. **Instructions** — textarea 5 rows, placeholder from harness default.
5. **Model** — hint "Reported by the agent when it connects; picked per agent."
   - Connected: dropdown button (min-width 200px, mono current model + `unfold_more`) → popover list (min-width 260px, shadow-overlay-200): mono model · note tertiary right · tick on selected. Selected row bg `--bg-layer-1-selected`.
   - Not connected: right-aligned caption tertiary "Available after connecting". No control.

Model lists come from the harness on connect (mock data: Claude `claude-sonnet-4-5` default / `claude-opus-4-1` / `claude-haiku-4-5`; Codex `gpt-5-codex` / `gpt-5` / `o4-mini`; Grok `grok-code-fast-1` / `grok-4`; Omp `omp-default` / `omp-fast`). Persist the pick per workspace-agent.

There is no Harness selector row (harness is fixed by the page) and no Repository row (repository follows the project).

State machine per harness: `idle --Connect--> connecting --ok--> connected | --err--> error`; `error --Retry--> connecting`; `connected --Disconnect--> idle`. Mock: connecting resolves after ~900ms. How the worker actually reaches each harness (CLI, ACP, …) is out of scope for this design; only the button and the two outcomes are specified.

---

## Screen 4 — New project modal (scene 12)

Plane's existing Create Project modal, with one extra section under the standard fields:

**Repository** (only when GitHub is connected)
- Header line: `deployed_code_account` 15px tertiary · `GitHub` caption secondary · "Repositories the app has been granted access to" caption tertiary · right `Manage access on GitHub` link.
- Search input (Propel `Input`, sm) filtering by `owner/repo`.
- List (surface-1 card, max-height 240px scroll): rows px 12 py 8, `source` icon · `owner/repo` mono body-sm · visibility pill (`Private`/`Public`, bg-layer-1) · right: `Already used by <Project>` disabled tag when the repo is bound elsewhere, else radio/tick. Selected row: bg `--bg-layer-1-selected`, border accent-strong.
- Grouped by installation (`kevinle128 · Personal`, `plane-mini · Organisation`) with the group title style above.

When GitHub is **not** connected: dashed card with `link_off` icon, "GitHub isn't connected in this workspace", explanation, link "Open Workspace settings → Integrations".

One repository per project; the worker clones it to `/srv/agents/mirrors/<repo>` read-only, and creates worktrees under it for code jobs.

---

## Interactions summary

- Mention → run created (`Waiting for pickup`) → worker picks up → `In progress`.
- Q&A runs read the clone; code jobs create a worktree on `agent/<IDENTIFIER>` and require a permission grant before the first write.
- Queue: Enter while in_progress appends; `Send now` interrupts; Stop clears the queue.
- Stop → confirm → `Stopped`, sandbox kept, reply resumes in the same sandbox.
- Elicitation (ambiguous repo): agent asks with option buttons; picking one continues the run.
- Panel width drag; Plan/Queue collapsible (remember per user).
- Harness connect/disconnect updates: card tag on Integrations, health tag in the mention picker, availability of the Model dropdown.

## State management (suggested MobX stores)

- `agentRunStore`: runs by work item; `status`, `kind`, `elapsed`, `timeline[]`, `plan[]`, `queue[]`, `panelWidth`, `collapsed{}`.
- `harnessStore`: per harness `{connection: idle|connecting|connected|error, models[], selectedModel, name, handle, instructions, enabled, errorDetail}`.
- `githubIntegrationStore`: `{state: idle|pairing|connected, installations[], settings{draftPRs, mirrorConclusions, branchFormat}}`.
- `projectRepoStore`: repo binding per project; `taken` map for "Already used by".

Realtime: run timeline and status over the existing websocket channel; heartbeat timestamp drives `stale`.

## Design tokens

All from `@plane/propel` semantic set, theme-aware. No literal hex anywhere.

- Surfaces: `--bg-canvas`, `--bg-surface-1`, `--bg-surface-2`, `--bg-layer-1`, `--bg-layer-1-hover`, `--bg-layer-1-selected`, `--bg-layer-2`.
- Accent/status fills: `--bg-accent-primary`, `--bg-accent-subtle`, `--bg-accent-subtle-hover`, `--bg-success-subtle`, `--bg-warning-subtle`, `--bg-danger-subtle`.
- Text: `--txt-primary`, `--txt-secondary`, `--txt-tertiary`, `--txt-on-color`, `--txt-accent-primary`, `--txt-link-primary`, `--txt-success-primary`, `--txt-warning-primary`, `--txt-danger-primary`.
- Borders: `--border-color-subtle`, `--border-color-strong`, `--border-color-accent-strong`, `--border-color-danger-strong`.
- Radius: `--radius-sm` `--radius-md` `--radius-lg`; pills 999px.
- Shadows: `shadow-raised-100` (glyph chips), `shadow-overlay-200` (panel, popovers).
- Type roles: `text-h3-medium`, `text-body-md-semibold`, `text-body-sm-semibold`, `text-body-sm-medium`, `text-body-sm-regular`, `text-body-xs-regular`, `text-caption-sm-medium`, `text-caption-sm-regular`, `text-11 font-semibold` (group titles). Mono: `font-code` (IBM Plex Mono).
- Spacing used: 4 / 6 / 8 / 12 / 16 / 24 / 36 px. Control heights 26 / 28 / 30 / 32 px.
- Animations: `om-breathe` 1.6s ease-in-out infinite (opacity .35→1, scale .8→1) on the live dot.

## Assets

- Propel icons (from `@plane/propel`): `AgentOutline`, `AgentAltOutline`, `ArrowNarrowLeftOutline`, `ChevronDownOutline`, `TickOutline`, `ToDoOutline`, `ClockOutline`, `GithubIcon`, `IntegrationsOutline`, `SearchOutline`, `InboxOutline`, `HelpOutline`, `SidePanelIcon`, plus the standard nav/settings set.
- Material Symbols Rounded (only where Propel has no equivalent): `terminal`, `source`, `lock_open_right`, `pending`, `send`, `close`, `unfold_more`, `expand_more`, `chevron_right`, `merge`, `deployed_code_account`, `link_off`, `psychology`, `bolt`, and the status icons listed above.
- No raster images. Avatars are Propel `Avatar` with initials.

## Files

- `Agent Runs.dc.html` — the full prototype (all 12 scenes, all states, interactive).
- `support.js` — prototype runtime; ignore.
- `_ds/plane-propel-*/` — the Propel bundle the prototype loads; use the npm package instead.
- `github.md` — repository references used while designing.
- `settings-block.txt` — notes on the settings chrome, taken from Plane's real settings pages.

Open the HTML directly in a browser; the strip at the top switches scenes.
