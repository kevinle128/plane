# Shared contracts, verified codebase facts and carried lessons

All phases use this file. Phase files refer to sections here and do not repeat them.
Base: branch `feat/local-cli-agents` at `46b19a1324` (on top of `preview` `6190932e2b`).
Every `file:line` below was read in this worktree on 2026-11-12.

## 1. Authority

- Acceptance authority: [epics.md](../2026-09-28-plane-local-cli-agents-epics/epics.md) (43 stories).
- Governing documents: [PRD](../2026-09-27-local-cli-agents-prd/prd.md), [Architecture Spine](../2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md) AD-1..AD-11, [design handoff](../../claude-design/design_handoff_local_cli_agents/README.md).
- The PRD and Spine govern when the older SPEC or the prototype differs (epics.md:28).
- Mockup coverage: 65 `CHANGE_FEATURE` rows in [mockup inventory](../reports/mockup-inventory-260928-0020-local-cli-agents.json). Each phase lists its rows.
- Prior plan (reference only, code lost): [2026-09-28 implementation plan](../2026-09-28-plane-local-cli-agents-implementation/plan.md).

## 2. Verified codebase facts that changed since the prior plan

| Topic | Prior plan assumed | Current fact (verified) | Effect on this plan |
| --- | --- | --- | --- |
| Web source root | `apps/web/core/components/...` | No `core/` folder. Code is in `apps/web/components`, `apps/web/store`, `apps/web/hooks`, `apps/web/services` | All web paths use the new root |
| UI primitives | `@plane/propel`, `@plane/ui` in `packages/` | `packages/propel` and `packages/ui` do not exist. Primitives come from npm `@makeplane/propel` 0.9.7 (`pnpm-workspace.yaml` catalog). Composites live in `packages/blocks` (`packages/blocks/package.json:11-46`) | Map handoff `@plane/propel`/`@plane/ui` names to `@makeplane/propel/*` and `@plane/blocks/*` |
| Web unit tests | `apps/web/tests/*.mjs` scripts | `apps/web/package.json` has no `test` script. Vitest runs in `packages/blocks` (`package.json:50`, jsdom project in `vitest.config.ts`), `packages/editor`, `packages/services`, `packages/codemods` | Put testable agent UI logic and presentational parts in `packages/blocks/src/agent-run/`; keep observer wrappers in `apps/web` |
| Browser e2e | Ad hoc `.mjs` browser scripts | No Playwright config in the repo | Browser acceptance is recorded evidence, not a committed suite (decision Q5: Vitest for UI logic plus a manual browser check script per phase) |
| Migrations | Up to `0144_agent_run_questions` | Latest is `apps/api/plane/db/migrations/0125_reset_project_deploy_board_identity.py`; lockfile `apps/api/migrations_lockfile.txt` lists `db: 0125_...` | First new migration is `0126_*`. Generate with `makemigrations`; never edit the lockfile |
| Integrations page | Existing GitHub/Slack page to extend | `app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/integrations/page.tsx` exists but has no route in `apps/web/app/routes/core.ts:258-285` and no entry in `packages/constants/src/settings/workspace.ts:29-81`. It returns `NotAuthorizedView` for non-admins (`page.tsx:39`) and calls a backend list with no URL in `plane/app/urls/` | Phase 1 routes and rewrites this page. Members get read access; admins get write access |
| Legacy GitHub models | Reuse `plane/db/models/integration/github.py` | `GithubRepository*` models have no consumer outside the model package; credentials sit in a plain JSONField | Add new agent-owned models. Do not touch the legacy models |
| Trigram search | `pg_trgm` GIN index on the catalog | No `pg_trgm` or `GinIndex` in current code | Use B-tree indexes and `icontains`; measure before adding an extension |
| Comment create | Assumed atomic | `IssueCommentViewSet.create` (`plane/app/views/issue/comment.py:94-145`) has no `transaction.atomic`; `ATOMIC_REQUESTS` and Celery eager mode are not set in `plane/settings/` | Phase 3 saves the comment and its Runs inside one `transaction.atomic` block and keeps both `.delay` calls after the block, as today. The Worker polls, so no new dispatch is needed |
| Mention parsing | Not analysed | `notification_task.py:123,137` filter `entity_name="user_mention"`; `email_notification_task.py:130-138` (`process_mention`) treats every `mention-component` as a user | Phase 3 adds an `entity_name` filter to `process_mention` before agent mentions exist |
| Mention picker | Not analysed | `TSearchEntities` (`packages/types/src/search.ts:15`) has no agent kind; `TMentionSuggestion` (`packages/editor/src/types/mention.ts:10-17`) has no disabled state; `useAdditionalEditorMention` (`apps/web/hooks/use-additional-editor-mention.tsx:51`) is the extension point; backend `SearchEndpoint` (`plane/app/views/search/base.py:329-402`) serves `user_mention` | Add `agent_mention` end to end; add `disabled` and `disabledReason` to the editor type |
| Bot comment authors | Not analysed | `User.is_bot`/`bot_type` exist (`plane/db/models/user.py:115-116`); `WorkspaceIntegration.actor` uses a bot user (`integration/base.py:44`); the comment card already renders bot actors (`apps/web/components/comments/card/display.tsx:69-72`) | One bot `User` per Agent writes conclusion comments. The bot user is not a `WorkspaceMember` |
| Worker auth | Registered Worker tokens | External API keys use `ApiKeyRateThrottle` at `API_KEY_RATE_LIMIT=60/minute` (`plane/api/rate_limit.py:12-14`, `plane/settings/common.py:163`) | A polling Worker exceeds 60/min. Add a dedicated Worker token model, authentication class and URL module |
| Peek overview | Not analysed | Peek view renders the same `IssueActivity` (`apps/web/components/issues/peek-overview/view.tsx:26,246,279`) as the full page (`issue-detail/main-content.tsx:245`) | One Run panel mounts through a portal from both surfaces |
| Panel width store | Not analysed | `useLocalStorage` (`apps/web/hooks/use-local-storage.tsx:31-64`) is per browser | Key panel and disclosure preferences by user ID |
| i18n | Not analysed | `packages/i18n/package.json:19-20` has `sync:check` and `check:sync` only; no fill script | Each UI story adds keys to every locale with the `translate` skill |
| API CI | Not analysed | `pull-request-build-lint-api.yml:43-48` runs ruff only on `apps/api` | A new `apps/agent-worker` gets no CI unless added (decision Q6: add an `apps/agent-worker` CI job) |
| Encryption | Not analysed | `encrypt_data`/`decrypt_data` (`plane/license/utils/encryption.py:20,34`) use Fernet from `SECRET_KEY` | Use them for GitHub tokens and device codes |
| Instance config | Not analysed | `get_configuration_value` (`plane/license/utils/instance_value.py:17-39`); GitHub login keys at `plane/utils/instance_config_variables/core.py:73` | Add GitHub App keys beside them (decision Q3) |
| Safe HTTP | Not analysed | `pinned_fetch` (`plane/utils/url_security.py`, used at `bgtasks/webhook_task.py:55,317`) | GitHub host is fixed; the GitHub client uses `requests` with timeouts. No new HTTP library |
| Celery | Beat scan for stale | `beat_schedule` in `plane/celery.py:46-101` with `DatabaseScheduler` (`:124`) | Derive Stale at read time from lease expiry. Use Celery only for catalog refresh and PR comment mirroring |
| Test markers | Not analysed | `apps/api/pytest.ini` uses `--strict-markers --reuse-db --nomigrations` | Register any new marker. Use `--create-db` after a model change in a reused local database Concurrency tests (row locks, `IntegrityError` races) use `@pytest.mark.django_db(transaction=True)` and real threads; inside the default per-test transaction they prove nothing <!-- red-team 2026-11-12 --> |

## 3. Data model (Plane API, PostgreSQL)

Plane API is the only writer of Run state (AD-1). All new models extend the existing `BaseModel`/`WorkspaceBaseModel` and live in `apps/api/plane/db/models/`.

| Model (file) | Owner phase | Key fields and constraints |
| --- | --- | --- |
| `AgentGithubConnection` (`agent_github.py`) | 1 | workspace 1:1, `github_user_id`, `github_login`, encrypted access and refresh tokens, `token_expires_at`, `connected_by`, `status` (`connected`/`disconnected`), `last_error` |
| `AgentGithubDeviceAuthorization` | 1 | workspace, encrypted `device_code`, `user_code`, `verification_uri`, `expires_at`, `interval`, `status` (`pending`/`completed`/`cancelled`/`expired`/`denied`), `kind` (`user`/`organization`) |
| `AgentGithubInstallation` | 1 | workspace, `installation_id`, `account_login`, `account_type`, `repository_selection`, `removed_at`; unique active (workspace, installation_id) |
| `AgentGithubRepository` | 1 | installation FK, `github_repository_id`, `full_name`, `owner_login`, `private`, `default_branch`, `clone_url`; index (workspace, owner_login, full_name) |
| `ProjectRepositoryBinding` | 1 | project 1:1, workspace, `github_repository_id`, `full_name`, `clone_url`, `base_ref`, installation FK (nullable, `SET_NULL`); unique (workspace, github_repository_id) where not deleted. Availability is derived from a live grant |
| `AgentGithubPolicy` | 1 | workspace 1:1, `open_as_draft` (default true), `mirror_conclusions` (default false), `branch_format` enum (`issue` default, `project_issue`) |
| `Agent` (`agent.py`) | 2 | workspace, `harness` enum (`claude_code`, `codex`, `grok`, `omp`) unique per workspace, `name`, `handle` unique per workspace case-insensitive, `instructions`, `mentionable`, `selected_model`, `bot_user` FK (`is_bot=True`, `bot_type="AGENT"`) |
| `AgentConnection` | 2 | agent 1:1, `state` (`not_connected`/`connecting`/`connected`/`failed`), `probe_generation`, `probe_requested_at`, `harness_version`, `location`, `models` JSON, `capabilities` JSON (versioned report), `missing_action`, `failure_hint`, `verified_at` |
| `AgentWorker` | 2 | `name`, SHA-256 `token_hash`, `last_seen_at`, `revoked_at`. Token is created by a management command and stored only on the Mini |
| `AgentRun` | 3 | workspace, project, issue, agent, requester, `trigger_comment` (unique with agent), `short_id`, `kind` (`qa`/`code`), `status` (`created`, `in_progress`, `awaiting`, `approval`, `completed`, `failed`, `stopped`; Stale is derived), repository snapshot, `model`, `instructions_snapshot`, `clone_path`, `worktree_path`, `active_workspace`, `branch_name` (unique, nullable), lease fields (`lease_generation`, `lease_worker`, `lease_expires_at`), `last_progress_at`, `next_event_seq`, stop and fail actor/time/reason, `conclusion_comment` FK |
| `AgentRunContextSnapshot` | 3 | run, `version`, `payload` JSON, `omitted_comment_count` |
| `AgentRunTurn` | 3 | run, `index`, `status`, `lease_generation`, `started_at`, `ended_at`, `driver_session_ref` |
| `AgentRunEvent` | 3 | run, `seq` unique per run, `source_key` unique per run, `turn`, `kind` (message, thought, tool_call, tool_result, plan, question, permission, error, pr, status, conclusion), `payload` JSON; index (run, seq) |
| `AgentRunMessage` | 4/5 | run, author, `text`, `state` (`queued`/`dispatching`/`accepted`/`cancelled`/`interrupted`), `position`, `send_now_requested_at`, `idempotency_key`, `question` FK (nullable) |
| `AgentRunQuestion` | 4 | run, turn, `kind` (`repository`/`harness`), `prompt`, `options` JSON, `answered_by`, `answer` |
| `AgentPermissionRequest` | 7 | run, turn, `lease_generation`, `action`, normalized `scope` JSON, `effect_hash`, `command`, `risk`, `decision` (`pending`/`allow_once`/`allow_run`/`deny`), `decided_by`/`decided_at`, `grant_source` FK (self), `consumed_at`, `result` JSON |
| `AgentCodeSlot` | 7 | `slot_index` (1..N, global), `run` (nullable), `container_id`, `acquired_at`; Run gains `code_enqueued_at` |
| `AgentRunPullRequest` | 7 | run 1:1, `number`, `url`, `title`, `draft`, `head_branch`, `head_sha`, `diff_summary`, `test_summary` |
| `AgentPrCommentMirror` | 7 | run, turn, `state` (`pending`/`posted`/`failed`), `github_comment_id`, `error` |

One migration per story that changes models. Name it `<next>_<domain>`, for example `<next>_agent_github_connection`; `makemigrations` assigns the number at implementation time. The first new number as of 2026-11-12 is `0126`. Phase files show domain names only.

## 4. API surfaces

- Member API (session auth, `plane/app/urls/agent.py`, views in `plane/app/views/agent/`): settings, GitHub, repository catalog, Runs, events, messages, questions, permissions. Use `allow_permission` (`plane/app/permissions/base.py:19`). Comment-permission checks reuse the guest rule from `comment.py:103-118`.
- Worker API (`plane/agent/worker_api/`, mounted at `api/agent-worker/v1/` in `plane/urls.py:18-25`): own `APIView` base with explicit `authentication_classes`, `permission_classes` and `throttle_classes = []` (not `BaseAPIView`, `plane/app/views/base.py:279-284`). The authentication class returns an authenticated principal as `request.user`, so the default `AnonRateThrottle` (`plane/settings/common.py:141`) never applies. Every mutation carries `run_id`, `lease_generation` and an `idempotency_key`. Plane rejects an older generation with HTTP 409.
- Domain services (`plane/agent/services/`): run creation, context snapshot, lease, event append, queue, branch name, GitHub client. Views stay thin.

## 5. Worker (`apps/agent-worker`, Python 3.12, uv)

Carried decision: the Worker is a Python package, as in the prior plan. It runs natively on the Mac Mini, not in Docker, because it needs the local CLIs, macOS sandbox and Docker CLI.

```
apps/agent-worker/
  pyproject.toml, uv.lock, ruff.toml, pytest.ini, README.md
  plane_agent_worker/
    __main__.py          # run | probe
    config.py            # localhost-only origin, token file, Run root outside the checkout
    plane_client.py      # no redirects, no proxy, idempotency keys, lease fencing
    loop.py              # poll, claim, renew, dispatch
    process_registry.py  # per-Run process group records, reconcile at start
    workspace.py         # Run-ID clone, remote check, Worktree (phase 7)
    sandbox_macos.py     # read-only OS boundary for Harness processes (+ .sb profile)
    prompt.py            # context envelope formatter
    mcp_server.py        # per-turn stdio MCP server with Plane tools
    conformance.py       # connection probe runner
    drivers/base.py, drivers/claude.py, drivers/codex.py, drivers/grok.py, drivers/omp.py
    code/                # phase 7: capacity, docker_sandbox, effects, journal, publish, git_ops
  tests/
    fakes/               # scripted fake Harness per protocol
    transcripts/         # recorded JSONL from opt-in native runs
```

New `.py` files need the `COPYRIGHT.txt` header (the CI check runs on all tracked `.py`).

## 6. Web layout

- Types: `packages/types/src/agent/` (export from the package index).
- Constants: `packages/constants/src/agent.ts` (status meta, branch formats, panel limits 380/540/960, stale threshold 5 min).
- Pure logic and presentational parts with vitest: `packages/blocks/src/agent-run/` (add `./agent-run` to `packages/blocks/package.json` exports; `tsdown.config.ts` already builds `src/*/index.ts`).
- Services: `apps/web/services/agent/*.service.ts` extending `APIService` (`apps/web/services/api.service.ts`).
- Stores: `apps/web/store/agent/` registered in `apps/web/store/root.store.ts`; hooks in `apps/web/hooks/store/`.
- Components: `apps/web/components/settings/integrations/`, `apps/web/components/agent-run/`, `apps/web/components/projects/create/repository-section.tsx`.
- i18n: new namespace `packages/i18n/src/locales/<lang>/agent.json` in every locale.
- Handoff tokens only. No literal colors and no copied prototype HTML (UX-DR17).

## 7. Test strategy and external dependencies

| External dependency | Real use | How tests run without it |
| --- | --- | --- |
| GitHub App (device flow, installations, PRs) | Phase 1, 7 | `plane/agent/github/client.py` is the only HTTP seam; contract tests patch it with `pytest-mock`. One opt-in live check per phase with operator credentials |
| Harness CLIs (Claude, Codex, Grok, Omp) | Phase 2-7 | Scripted fakes in `apps/agent-worker/tests/fakes/` replay committed JSONL transcripts. Native tests use marker `native` and run only on the Mini |
| Docker | Phase 7 | Unit tests mock the Docker CLI seam. Real container tests use marker `docker` |
| Git remote | Phase 3-7 | A local bare repository served through a test-only `file` transport switch in `config.py`. Production config rejects `file` |
| macOS sandbox | Phase 2-7 | Profile unit tests run on macOS only (`skipif` other OS); boundary tests use marker `native` |

Worker markers `native` and `docker` go in `apps/agent-worker/pytest.ini` with `--strict-markers`.
API contract tests follow `apps/api/plane/tests/TESTING_GUIDE.md` and live in `apps/api/plane/tests/contract/app/test_agent_*.py`.

Standard verification commands (each phase lists its own subset): Run each line from the repository root. <!-- red-team 2026-11-12 -->

```bash
# API
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app -k agent
docker compose -f docker-compose-test.yml run --rm api-tests pytest plane/tests/unit -k agent
docker compose -f docker-compose-test.yml run --rm api-tests python manage.py makemigrations --check --dry-run   # local manage.py defaults to production settings and does not load apps/api/.env
cd apps/api && uv run ruff check . && uv run ruff format --check .
# Worker
cd apps/agent-worker && uv run pytest -m "not native and not docker" && uv run ruff check .
# Web
pnpm --filter=@plane/blocks test
pnpm --filter=@plane/editor test
pnpm turbo run check:types --filter=web --filter=@plane/blocks --filter=@plane/types --filter=@plane/constants
pnpm check:lint && pnpm check:format
pnpm --filter=@plane/i18n check:sync
# Headers
addlicense -check -f COPYRIGHT.txt -ignore "**/migrations/**" $(git ls-files '*.py')
addlicense -check -f COPYRIGHT.txt -ignore "**/*.config.ts" -ignore "**/*.d.ts" $(git ls-files '*.ts' '*.tsx')
```

Browser acceptance: run `pnpm dev` with the API from `docker-compose-local.yml`, check each listed scene in Light and Dark at 375, 768 and 1280 px, with keyboard only, and record the result in `reports/` of this plan.

## 8. Delivery rules

- One phase is one PR to `preview`. One commit per story, in story order. Commit messages describe the change; they contain no story, phase or finding IDs.
- Branch phase N+1 from `preview` after phase N merges. Each PR regenerates `migrations_lockfile.txt`, so parallel migration branches conflict by design.
- Code comments, test names and migration names contain no plan IDs.
- Before a migration, back up the local database (`pg_dump`). Rollback: `uv run python manage.py migrate db <previous>` then revert the PR.

## 9. Carried user decisions (keep)

- AD-8 exception (member decision 2026-09-28): for file effects, Docker produces the bounded content and the trusted Worker publishes it on the Host through pinned no-follow descriptors after it rechecks the consumed grant and lease. Reason: bind-mount identity cannot be verified through inode equality on Docker Desktop (the prior path-access report was not restored; the evidence summary is in [prior phase-04 notes](../2026-09-28-plane-local-cli-agents-implementation/phase-04-code-jobs-and-draft-pr.md)).
- Long-term, scalable design: explicit Plane and Worker contracts, durable indexed Run state, idempotent effects, bounded resources, versioned Harness adapters, and load/concurrency/recovery evidence before scale claims.
- Send now sends to the active Run now; approval scopes are "Run-wide versus one action"; Codex mentions start Codex (user answers in the mockup inventory).
- No ACP (PRD, 2026-09-27).

## 10. Carried lessons (re-probe before adoption)

These came from prior implementation work, not from user decisions. Each phase re-verifies them. The signal shows when a lesson applies.

| Lesson | Source | Signal to watch | Response |
| --- | --- | --- | --- |
| Codex, Grok and Omp fail to start under a full read-only boundary (SQLite and runtime state writes) | [runtime decision](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-harness-runtime-decision.md) | Startup error `Operation not permitted`, `FS_PERMISSION_DENIED`, `SQLITE_READONLY` | Decision Q1 accepts a per-turn disposable runtime directory |
| Native Harness reads followed a hard link out of the Worktree | worker foundation report §Native runtime checks | A read probe through a hard link returns foreign content | Phase 3 adds the hard-link probe; the Worker-side read/list/search tools are adopted if the probe fails (decision Q7) |
| A Run read another Run's files through the shared Run root | worker foundation report §Run read isolation | Sandboxed `cat` of another Run path succeeds | Phase 3 profile denies Run-root reads outside the current Run |
| Stopped process must settle before Stop or the next Send now turn is recorded | [send-now native report](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-send-now-native-progress.md) | Two Harness processes in one CWD | Phase 5 waits for process exit or timeout, then reports an error |
| Stop must not create a replacement clone | [stopped clone resume report](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-stopped-clone-resume-progress.md) | Clone inode changes after resume | Phase 5 asserts clone identity on resume |
| Polling turned a terminal Run back to active | [Code resume report](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-code-resume-progress.md) | Status regresses after a late poll | Store ignores older projections by `seq` |
| Lost tool results when long output was split | [native tool results report](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-native-tool-results-progress.md) | Missing result chunks in timeline | Phase 3 chunks results with a call ID and part index |
| Edit during Save lost a settings draft | [instructions report](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-agent-instructions-acceptance.md) | Draft text lost after delayed Save | Phase 2 disables the fieldset during Save |
| Revoked repository at the queue head blocked capacity | [capacity report](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-28-capacity-concurrency-progress.md) | Waiting head never starts | Phase 7 filters grant validity in the waiting query |
| RabbitMQ health check created a root-owned cookie | capacity report §Test stack startup repair | `test-mq` unhealthy with `eacces` | Fix `docker-compose-test.yml` only if it reproduces |
| Network grants pin literal IPs; hostname/DNS is undecided | [network report](../2026-09-28-plane-local-cli-agents-implementation/reports/2026-09-29-network-boundary-progress.md) | A grant for a hostname resolves to a new IP | Phase 7 uses literal-IP pins; hostname approvals resolve and pin IPs at approval time (decision Q2) |
| Nested native buttons in sidebar, menus and breadcrumbs broke keyboard access | page control, menu, breadcrumb reports | Axe or keyboard check finds a button in a button | Each UI phase runs a nested-interactive check |
