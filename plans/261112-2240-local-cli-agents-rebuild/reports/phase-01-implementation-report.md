# Phase 1 implementation report

Branch `feat/local-cli-agents` (worktree `plane-worktrees/local-cli-agents`). One commit per story, pushed after each commit.

## Baseline (before any change)

- `docker compose -f docker-compose-test.yml run --rm --build api-tests pytest plane/tests/contract/app/test_project_app.py plane/tests/unit/bg_tasks/test_url_security.py plane/tests/unit/bg_tasks/test_ssrf_advisories.py plane/tests/unit/bg_tasks/test_work_item_link_task.py` -> 122 passed.
- `ruff format --check plane` already reports 53 files that need formatting on `preview` (for example `plane/utils/url_security.py`). Format checks in this phase cover the new and changed agent files only. `ruff check plane` is clean.

## Per-story evidence

### 1.1 Connect a GitHub account with device flow — `75218dd7f9`

- Test first: `pytest plane/tests/contract/app/test_agent_github_device_flow.py` -> collection error `ModuleNotFoundError: No module named 'plane.agent'` (expected, no code yet). Blocks: `vitest src/agent-run` -> `Cannot find module './device-flow'`.
- First green run found one real defect: a GitHub `interval` of `0` was replaced by `5` (`or 5`). Fixed in the service.
- Green: device flow 30 passed; with `test_project_app.py` 55 passed. `makemigrations --check --dry-run` -> No changes detected. `pnpm --filter=@plane/blocks test` -> 393 passed. `turbo check:types` (web, admin, blocks, types, constants) -> 13/13 and 11/11 tasks successful. oxfmt/oxlint on changed files clean. `pnpm --filter=@plane/i18n check:sync` -> in sync.

### 1.2 Connect a GitHub organization

- Test first: `pytest test_agent_github_installations.py test_agent_git_catalog.py` -> 2 collection errors (`plane.bgtasks.agent_git_catalog_task` missing).
- First green run: 1 failure. The attach test asserted the enqueue, but `transaction.on_commit` does not fire inside the per-test transaction; the test now uses `django_capture_on_commit_callbacks(execute=True)`.
- Green: `pytest plane/tests/contract/app -k agent` -> 51 passed. `makemigrations --check` clean (`0127_agent_git_accounts`). `ruff check plane` clean. Web typecheck 10/10 tasks, oxlint/oxfmt clean, i18n in sync.

## Deviations from the plan

1. Migrations: the plan names four migrations. The models are split by story: `0126_agent_git_connection` (connection, device authorization) in 1.1; accounts and repositories in 1.2; binding in 1.5; policy in 1.6.
2. Test fixtures are registered through `plane/tests/conftest.py` (same pattern as `conftest_external`), because importing pytest fixtures into each test module triggers ruff F811.
3. The admin GitHub page had a lint warning (`promise/always-return`) that the pre-commit hook rejects for any touched file. It was rewritten as an equivalent `try/catch/finally`.
4. Locales: the `translate` skill is not installed in this runtime. Every non-English `agent.json` carries the English text for the new keys, so `check:sync` passes; the strings still need translation.
5. "The Celery task arguments contain no token" check (1.1 list) moves to 1.2, where the catalog task is created (`test_attach_enqueues_catalog_with_ids_only_and_lists_repositories`).
6. Removed (detached) installations are hidden on the GitHub detail page (1.3 AC "disappears"). The mockup has no control to attach a removed installation again; the API allows it (`POST github/accounts/<id>/attach/`). This is a product gap for the user to decide.
