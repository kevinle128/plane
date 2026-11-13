# Code review: Phase 2 frontend (agent settings and Claude connection)

- Date: 2026-11-13 (Asia/Saigon)
- Branch: feat/local-cli-agents-phase-2, diff `origin/feat/local-cli-agents...HEAD -- apps/web apps/admin packages`
- Scope: 40 files, +3205/-4 (19 locale files of 92 lines each)
- Mode: read-only review; no code changed.

## Findings (appended as confirmed)

### C1 (Critical) Connect never starts polling; page stays "Connecting" forever

- File: `apps/web/components/settings/integrations/harness/harness-detail-page.tsx:36-37, 352-354`; `connection-row.tsx:66-75`
- Evidence: SWR 2.4.2 polling loop (`node_modules/.pnpm/swr@2.4.2_react@19.2.8/node_modules/swr/dist/index/index.mjs:600-635`) calls `refreshInterval(getCache().data)` once when the effect mounts and then only after a poll it started itself. `pollWhilePending` is a stable module function, so the effect never re-runs. `connect()` writes the new `connecting` Agent into the MobX store only (`agent.store.ts:68-72`); the SWR cache still holds the pre-connect list, and nothing calls `mutate()`.
- Failure: admin opens Claude detail (state Not connected), clicks Connect. Tag shows Connecting with spinner; action is `null` (no Retry, no Disconnect). No poll runs, so the Connected / Connection failed result and the server-derived 120 s "Worker did not answer" failure never show. Each window refocus (global `revalidateOnFocus: true`) gives one refetch, but no poll runs; an admin who watches the page sees no change until refocus, navigation or reload. Same on a direct page load while a probe is running (cache empty at mount -> interval 0 -> no timer).
- Fix: drive the interval from the store, not SWR data, and re-arm it: for example `refreshInterval: isPending ? AGENT_CONNECTION_POLL_MS : 0` with `isPending` computed from `getAgent(...)` in the observer (a changing number re-runs the SWR effect). Do not rely on `mutate()` after `connect()`: a manual revalidate does not call the polling effect's `next()`, so it does not re-arm the loop; only a change in the effect deps (numeric interval or key) does. Apply the same store-derived interval to the Integrations index `useSWR` (`index-page.tsx`, no `refreshInterval` today), or lift the fetch into one shared hook, so the card tags stay live after the admin goes back during a probe. Add a test that proves polling starts after Connect.

### I1 (Important) Form draft is never reconciled with store updates; Save reverts other changes or fails

- File: `apps/web/components/settings/integrations/harness/harness-detail-page.tsx:78-86, 137-141, 400`
- Evidence: `draft` is seeded once (`useState(() => draftOf(agent))`, `key={agent.id}` is stable). Every later store write (focus revalidation, which is on globally in `packages/constants/src/swr.ts:19`; poll; connect/disconnect response; Mentionable response) replaces `agent` but not `draft`. `changesOf(draft, agent)` then reports the stale draft value as a user change. The comment at :78 claims the opposite.
- Failure A (lost update): admin B renames the Agent in another tab. Admin A refocuses; SWR refetches; A's Name field still shows the old name and Save turns on. A edits Instructions and saves; the PATCH carries `name: <old>` and silently reverts B's rename.
- Failure B (blocked save): Claude connected with `opus` selected. Admin disconnects and connects again; the new report omits `opus`, so `apply_report` clears `selected_model` (`apps/api/plane/agent/services/harness_probe.py`, end of `apply_report`). The store gets `selected_model: ""`, the draft keeps `opus`, Save is enabled with no user edit, and any Save (for example a name change) returns 400 `not_reported` and saves nothing.
- Fix: diff against a baseline snapshot (the values the draft started from or last saved), not the live agent; when `agent` changes, copy server values into fields the user did not touch (draft[field] === baseline[field]). Add a component test for both scenarios.

### I2 (Important) Tests do not cover the feature behavior that broke

- File: `packages/blocks/src/agent-run/connection-state.test.ts` (only test in the diff)
- Evidence: 5 tests on pure lookup tables. No test for `AgentStore`, the polling hook, `changesOf`/draft behavior, `fieldErrorMessage` code mapping, permission gating, or the model selector rule in the component. AGENTS.md: "All features require unit tests". Browser check is recorded as NOT RUN (`reports/phase-02-implementation-report.md:81`).
- Failure: C1 and I1 pass every gate (vitest, types, oxlint, i18n sync all pass in this review) and would reach users.
- Fix: add Vitest tests for the store (setAgent/fetchAgents replace), the poll-interval decision derived from store state, `changesOf` with a baseline, and `fieldErrorMessage` (known code, unknown code, missing key). Run the scene 11 browser script once with a real Worker before merge.

### M1 (Minor) Save locks only the form; Mentionable, Connect and Disconnect stay live during Save

- File: `harness-detail-page.tsx:163, 390, 398`
- Evidence: `MentionableSwitch` and `HarnessConnectionRow` are outside the `<fieldset disabled>`. Spec: "Save disables the whole fieldset while the request runs".
- Failure: admin saves Name and toggles Mentionable during the request. Both PATCHes are partial so the server is right, but `setAgent` keeps whichever response lands last; if the Save response (read before the toggle committed) lands last, the switch flips back on screen until the next fetch.
- Fix: share one `isBusy` flag across the card (form Save, Mentionable, Connect/Disconnect), or confirm with the spec owner that only the form fields must lock.

### M2 (Minor) Field error stays after the user edits the field

- File: `harness-detail-page.tsx:138, 168, 185`
- Failure: handle collision shows "already exists"; the admin types a new handle; the red message and `aria-invalid` stay until the next Save, so screen readers still report the field as invalid.
- Fix: clear `error[field]` in each `onChange`.

### M3 (Minor) `<label htmlFor>` points at a `<span>` when the model selector is unavailable

- File: `model-select.tsx:27-33`, `harness-detail-page.tsx:104`
- Failure: in Not connected / failed states the Model label is not associated with any labelable element; clicking it does nothing and AT gets no name/value pair. Low impact.
- Fix: render the unavailable text as the row value with `aria-labelledby` (or drop `htmlFor` in that state).

### M4 (Minor) Dead code and cross-module coupling

- `AgentStore.fetchAgent` and `AgentService.retrieve` are unused (`agent.store.ts:56`, `agent.service.ts:37`).
- `index-page.tsx` imports `AgentsLoadError` from the 400-line `harness-detail-page.tsx`; `agentsKey` lives in `harness-card.tsx`. Move both to a small shared module.
- The detail page reuses `agent_git.integrations.back` for its back link; correct copy ("Integrations") but couples the Harness page to the Git namespace.

### M5 (Minor) Non-English locales are English copies

- 18 locales contain `agent_settings` byte-identical to `en` (checked vi-VN, fr, ja). Same as Phase 1 `agent_git`, and `check:sync` passes, so this is the project's chosen convention, not a defect. Record it so the translate step is not forgotten before release.

## Checks with no finding

- Permission gating: page `canEdit` = workspace ADMIN; API GET allows ADMIN+MEMBER, PATCH/connect/disconnect ADMIN only (`apps/api/plane/app/views/agent/settings.py`). Members see disabled fields, read-only note, no Connect/Disconnect. Integrations is hidden from guests (`packages/constants/src/settings/workspace.ts:62`).
- Connect/Retry double-submit: Propel `Button` sets `disabled` when `loading` (`@makeplane/propel/dist/components/button/button.js`), and the button is gone once the state is `connecting`.
- Save keeps the draft on error, and maps server `codes` to `agent_settings.errors.<field>_<code>`; every code the serializer emits (`blank`, `required`, `max_length`, `invalid`, `taken`, `not_connected`, `not_reported`) has an `en` key. Unknown code falls back to the API message (`t()` returns the key on a miss, `packages/i18n/src/hooks/use-translation.ts:36`).
- Model selector renders only for `connected` with reported models; the value is sent only on Save.
- Codex/Grok/Omp: no action button, hint "not available yet", Mentionable and settings still editable (matches "configured but not connected").
- "Enabled" switch of the design is implemented as the Mentionable switch in the header (story 2.5 wording); acceptable.
- Poll cleanup: SWR clears the timer in the polling effect cleanup on unmount or key change (`swr/dist/index/index.mjs:627-631`).
- MobX: store in `apps/web/store/agent/`, registered and reset in `root.store.ts`; mutations inside `runInAction`.
- COPYRIGHT headers present on all new `.ts`/`.tsx` files. Propel and `@plane/blocks` subpath imports used. Semantic tokens only.
- Gates run in this review: blocks vitest 5/5 pass; `check:types` web + blocks pass; oxlint on changed paths 0 issues; `@plane/i18n check:sync` pass.

## Counts and verdict

- Critical 1, Important 2, Minor 5.
- Verdict: REQUEST CHANGES. C1 blocks story 2.1 in the browser (no path from Connecting to Connected or to the 120 s failure without reload). Fix C1 and I1 with tests (I2), then run the scene 11 browser check.
