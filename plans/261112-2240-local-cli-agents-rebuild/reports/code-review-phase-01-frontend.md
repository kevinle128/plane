# Code review: Phase 1 frontend (local CLI agents)

Date: 2026-11-13 (Asia/Saigon)
Scope: `git diff origin/preview...HEAD -- apps/web apps/admin packages`
Status: complete

## Findings

### F1 [Important] Device-flow poll errors are invisible and stop polling

- `apps/web/components/settings/integrations/git/github/setup-card.tsx:62-71,90-94` + `github/device-flow.tsx:46-65`
- `onError={setMessage}` sets `message`, but `message` renders only in the non-authorization branch; while the device card is shown nothing renders it. In `poll()` a thrown error skips `setAuthorization`, so the timer effect (deps `[authorization, poll]`) never re-arms: polling stops.
- Scenario: one transient 5xx/network error (or 403 after the admin is demoted) on a poll -> card keeps showing "Waiting" spinner + countdown, no automatic re-poll and no visible error (only a manual "I entered the code" click re-polls, and nothing tells the user to press it); user who already approved in GitHub waits up to 15 min until local expiry says "expired". Cancel failure is also silent.
- Fix: render `message` (role=alert) inside the device card branch too; on transient errors re-arm the timer (e.g. keep a `pollTick` state or schedule next poll in `finally`); on terminal codes (403/404) settle.

### F2 [Important] Removed (detached) GitHub installations can never be re-attached from the UI

- `apps/web/components/settings/integrations/git/accounts-list.tsx:108-111`
- The list filters out `state === "detached"`, so the Attach button is never rendered for them. The API (`apps/api/plane/app/views/agent/git.py:194-206`) accepts attach of a detached row, and the spec (phase-01 Key decisions, 1.3) says a detached installation "stays detached until an admin attaches it again explicitly". Sync never clears `detached`.
- Scenario: admin removes org `acme` by mistake -> it disappears; Refresh keeps it detached; no UI path to restore it; only workaround is disconnect + reconnect GitHub (which still keeps the detached row) or a raw API call. The code comment on line 108 claims the opposite of the effect.
- Fix: render detached rows with a "Removed" label and an Attach action for admins (or a collapsed "Removed installations" group).

### F3 [Important] GitHub detail page shows a false GitLab "token expires" warning after every connect/refresh

- `apps/web/components/settings/integrations/git/detail-page.tsx:140-148` (rendered for both providers at `:216`)
- `ConnectionWarnings` runs `getTokenExpiryState(connection.token_expires_at)` with the 14-day window for any provider. For GitHub, `token_expires_at` is the 8 h user-to-server access token expiry (`github_connection.py` `_apply_token_body`), which Plane refreshes automatically. So for 8 h after connect/each refresh, `expiresSoon` is true and the GitHub page shows `agent_git.gitlab.warnings.expires_soon`: "The token expires on <today>. Create a new token and connect again before then."
- Scenario: admin connects GitHub -> immediately sees a warning telling them to create a new token today; misleading, and invites needless reconnects.
- This is not App-config dependent in practice: `token_expires_at` is set only when GitHub returns `expires_in`, and the spec's locked refresh design requires expiring user tokens, so the 8 h value is the expected state.
- Fix: gate the expiry warning on `connection.provider === "gitlab"` (the 14-day rule is GitLab-only per spec Key decisions). Same applies to the `worker_error` text using a `gitlab.*` key for both providers (rename to a neutral key).

### F4 [Minor] Backend error codes with no i18n key fall back to "Something went wrong"

- `apps/web/components/settings/integrations/git/provider-meta.tsx:28-37`; keys in `packages/i18n/src/locales/en/agent.json` `agent_git.errors.*`
- Codes the API can return with no key: `github_token_invalid` (409, `apps/api/plane/agent/git_providers/github.py:35`, e.g. Refresh installations after the user revoked the App), `github_tls_failed`, `github_url_redirected` (`git_providers/http.py:185,197` use `f"{provider}_..."`), `invalid_kind`, `invalid_cursor`.
- Scenario: admin revoked the App in GitHub, clicks Refresh installations -> toast "Something went wrong. Try again." instead of "reconnect"; retry cannot help.
- Fix: add the keys (en + sync), and on `*_token_invalid` / `provider_reconnect_required` re-fetch connections so the page switches to the reconnect state.

### F5 [Minor] "denied" outcome ignores `last_error`; config failures read as user refusal

- `apps/web/components/settings/integrations/git/github/setup-card.tsx:27-31,53-60`
- Backend maps every non-pending GitHub error to `denied` with `last_error` (`device_code_unreadable`, `incorrect_client_credentials`, `unsupported_grant_type`, ...) (`github_connection.py:183,214-216`). UI always says "GitHub did not authorize Plane. Start again if this was a mistake."
- Scenario: wrong App client ID/secret or rotated SECRET_KEY -> admin retries forever thinking they clicked Cancel.
- Fix: when `last_error` is not `access_denied`, show `agent_git.errors.<last_error>` (fallback generic) instead of the "denied" copy.

### F6 [Minor] Device-code expiry uses the browser clock against the server timestamp

- `apps/web/components/settings/integrations/git/github/device-flow.tsx:32-35,67-69`; `packages/blocks/src/agent-run/device-flow.ts:15-25`
- Scenario: client clock 15+ min fast -> first render computes `expired`, card settles "expired" before any poll; admin can never connect from that machine. Smaller skew shortens/extends the countdown.
- Fix: derive the deadline from the response time (`receivedAt + (expires_at - server now)` or send `expires_in`), and let the server status be the authority for expiry.

### F7 [Minor] Repository picker: stale catalog after 409, heavy refetch on focus, silent truncation

- `apps/web/components/projects/create/repository-section.tsx:90-93`, `apps/web/components/projects/create/root.tsx:130-132`, `apps/web/store/agent/git.store.ts:149-164`
- (a) On 409 `repository_already_bound` the catalog is not revalidated; the row stays selectable and a retry hits 409 again. (b) `WEB_SWR_CONFIG.revalidateOnFocus=true` (`packages/constants/src/swr.ts:19`) re-runs `fetchRepositories`, up to 50 sequential page requests, on every window focus while the modal is open. (c) Catalog over 5,000 rows is cut silently at `MAX_REPOSITORY_PAGES`.
- Fix: `mutate` the repositories key after a repository error (and after a successful create); pass `{ revalidateOnFocus: false }`; long-term use server-side `search`/`owner` params instead of loading every page.

### F8 [Minor] Group heading shows raw, untranslated `account_type`

- `apps/web/components/projects/create/repository-section.tsx:208-211`
- `type: account.type` passes API strings `Organization` / `User` / `Group` into `agent_git.repository.account_group`; non-English UI shows English, and it differs from the settings page (`accounts.organization` = "Organisation", design `kevinle128 · Personal`).
- Fix: map through the same `typeLabels` used in `accounts-list.tsx:39-43` (extract a helper).

### F9 [Minor] Expired GitLab token shows no warning

- `apps/web/components/settings/integrations/git/detail-page.tsx:142-148`
- `getTokenExpiryState` returns `{expired:true, expiresSoon:false}` after `expires_at`; the component reads only `expiresSoon`. Status stays `connected` until the next 401 (no beat task), so the page shows a green connected state with no warning for an already-expired token.
- Fix: add an "expired" warning when `expiry.expired`.

### F10 [Minor] Connections fetch failure renders an empty page

- `apps/web/components/settings/integrations/git/detail-page.tsx:175,213-226`, `index-page.tsx:26`
- SWR `error` is ignored; on 5xx/network failure the detail page shows only the heading (no setup card, no error, no retry).
- Fix: render an error state with retry when `error` is set.

### F11 [Minor] Native `<select>` instead of Propel dropdown (design fidelity)

- `apps/web/components/settings/integrations/git/change-request-policy.tsx:78-91`, `apps/web/components/projects/create/repository-section.tsx:156-168`
- Design README Screen 3 specifies a dropdown button for Branch format; AGENTS.md says primitives come from `@makeplane/propel`. Native select ignores theme in some browsers' popups (dark mode option list). Tokens used are semantic; no hex found.
- Fix: use the Propel select/dropdown primitive.

### F12 [Minor] Tautological vitest

- `packages/blocks/src/agent-run/provider-terms.test.ts:24-33` asserts `POLICY_LABEL_FIELDS` equals its own literal; it proves nothing about the detail page. Better: assert every `getPolicyLabelKey(field, provider)` exists in `en/agent.json`.

### F13 [Minor] Enter in the repository search or base-branch field submits the create-project form

- `apps/web/components/projects/create/repository-section.tsx:147-154,237-245` inside the `<form>` of `apps/web/components/projects/create/root.tsx`
- No Enter guard on the search `Input`; implicit form submission fires `onSubmit`.
- Scenario: name/identifier already valid, user types "web" in search and presses Enter to filter -> project is created with whatever repository (or none) is selected.
- Fix: `onKeyDown={(e) => e.key === "Enter" && e.preventDefault()}` on the search input (keep Enter submit on base branch only if intended).

## Verified, no finding

- Guests blocked: `apps/web/app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/layout.tsx:32-37` + `components/settings/helper.ts:30-35` slice sub-routes to `/settings/integrations`; `packages/constants/src/settings/workspace.ts:58-64` access = Admin, Member. API: member read / admin write (`apps/api/plane/app/views/agent/git.py:73,84,101,112,120,147,168,176,195,210,244,290,296`).
- Members read-only: device-flow start, GitLab form, attach/remove/refresh, disconnect hidden behind `canEdit`; policy switches and select `disabled` (`change-request-policy.tsx:118`); `canEdit` = workspace Admin (`integrations/github/page.tsx`, `gitlab/page.tsx`).
- Duplicate polls: client can overlap (timer + manual), but the server locks the row and skips GitHub inside `interval`, handles `slow_down` (`apps/api/plane/agent/services/github_connection.py:162-213`). Timers cleared on unmount; late poll results are harmless (`settledRef`).
- Secrets: GitLab token lives only in component state, cleared on success, `type="password"`; `TAgentGitConnection` has no token field (`packages/types/src/agent/git.ts:20-44`). Admin App secret is shown decrypted in a password field, same as existing `GITHUB_CLIENT_SECRET` handling (instance-admin only); not new exposure. Admin hard-coded English matches the admin app convention.
- Q15 single code `gitlab_url_not_allowed_or_unresolved`, `gitlab_scope_missing` with `{detail}`, `gitlab_token_not_bot` warning: present in `en/agent.json` and rendered.
- Binding payload: only `{repository_id, base_ref?}` (`packages/types/src/agent/git.ts:97-100`, `root.tsx:100`); 409 `repository_already_bound` mapped to i18n; both providers listed and grouped (`packages/blocks/src/agent-run/repository-list.ts:48-66`).
- MobX: every state write is inside `runInAction` (`apps/web/store/agent/git.store.ts`); store reset on sign-out (`root.store.ts`); types in `packages/types`; service layer used.
- i18n: `agent` namespace registered (`packages/i18n/src/constants/namespaces.ts`); `sync:check` clean. COPYRIGHT header present on all new .ts/.tsx read. `next/link` resolves to the in-app compat shim (`apps/web/vite.config.ts:28`).
- Design tokens: semantic classes only; no hex literals; `--bg-accent-primary` exists in Propel `variables.css`.

## Checks run

- `vitest run src/agent-run` (packages/blocks): 4 files, 27 passed.
- `tsc --noEmit` (apps/web): clean.
- `oxlint` on changed web dirs: 0 warnings, 0 errors (21 files); `oxfmt --check`: clean.
- `pnpm --filter=@plane/i18n sync:check`: all locales in sync.

## Summary

Critical 0 / Important 3 (F1-F3) / Minor 10 (F4-F13).
Verdict: changes requested. Fix F1-F3 before merge; Minors can follow.

## Controller disposition (2026-11-13)

F2 is not fixed in Phase 1. The spec requires only an admin attach action and that sync never re-attaches a removed installation (phase-01 "Installation attachment"); it does not require a UI control. On 2026-11-13 the decision was to keep the mockup and track the gap in kevinle128/plane#2.
