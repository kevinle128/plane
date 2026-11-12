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

### 1.3 Remove one GitHub installation

- Test first: 5 new removal tests failed with 404 (no `DELETE <provider>/accounts/<id>/` route).
- Green: `test_agent_github_installations.py` 19 passed; `pytest plane/tests/contract/app -k agent` 56 passed. Web typecheck 10/10, i18n in sync.
- The two binding checks of this story (binding kept with `available=false`; detach, then sync keeps the binding unavailable) need the binding model from 1.5. They are in `test_agent_repository_binding.py` with the 1.5 commit.

### 1.4 Disconnect the workspace GitHub account

- Test first: `test_agent_github_disconnect.py` -> 9 failed, 2 passed (the two passing cases, "no connection gives 404" and "GitLab row unchanged", pass trivially while the route is missing; they guard behavior after the route exists).
- Green: disconnect 11 passed; `pytest plane/tests/contract/app -k agent` 67 passed. Web typecheck 10/10, oxlint clean, i18n in sync.
- AC 2 for new Launches and pending change-request delivery needs Runs; it stays open for Phases 3 and 7 as the plan states. The "bindings kept" check is in the 1.5 binding tests.

### 1.5 Bind one repository while creating a project

- Tests Before 1: a new explicit case `test_create_project_without_repository_keeps_the_response_shape` passed on the unchanged view (`test_project_app.py` 26 passed). Its first version compared against `ProjectListSerializer(project)` and failed because the view adds queryset annotations; the case now pins the serializer's declared field set.
- Test first: `test_agent_repository_binding.py` -> collection error (`ProjectRepositoryBinding` missing). Blocks `repository-list.test.ts` -> `Cannot find module './repository-list'`.
- Green: binding 25 passed (including the threaded race `test_concurrent_binds_give_one_201_and_one_409_and_no_orphan_project`, `django_db(transaction=True)`); `pytest plane/tests/contract/app -k 'agent or project_app'` 119 passed; `makemigrations --check` clean (`0128_project_repository_binding`); blocks agent-run 13 passed; web and blocks typecheck 11/11; oxlint/oxfmt clean; i18n in sync.
- The 1.3 and 1.4 binding checks are in `TestBindingAvailability` (removed installation and disconnect keep the binding with `available=false`).
- Refactor: `ProjectViewSet.create` now saves project, members, states and binding in one `transaction.atomic` block; a bind `IntegrityError` rolls back the project and returns 409. `model_activity.delay` stays after the block.

### 1.6 Set the draft pull-request default

- Test first: `test_agent_git_policy.py` -> collection error (`change_request_policy` missing).
- Green: policy 6 passed; `pytest plane/tests/contract/app -k agent` 98 passed; `makemigrations --check` clean (`0129_agent_git_policy`); web typecheck 10/10; i18n in sync.

### 1.7 Set conclusion mirroring to pull requests

- Test first: 3 new cases; `test_admin_change_persists_and_the_delivery_policy_reads_it` failed (the API ignored `mirror_conclusions`). The default and member-403 cases already held because the model and the permission exist since 1.6.
- Green: policy 9 passed; `ruff check plane` clean; web typecheck 10/10; i18n in sync.

## Deviations from the plan

1. Migrations follow the four names of the plan, one per story that adds models: `0126_agent_git_connection` (connection, device authorization) in 1.1, `0127_agent_git_accounts` in 1.2, `0128_project_repository_binding` in 1.5, `0129_agent_git_policy` in 1.6. The policy model has all three fields from 1.6; 1.7 and 1.8 expose `mirror_conclusions` and `branch_format` in the API and UI without a new migration.
2. Test fixtures are registered through `plane/tests/conftest.py` (same pattern as `conftest_external`), because importing pytest fixtures into each test module triggers ruff F811.
3. The admin GitHub page had a lint warning (`promise/always-return`) that the pre-commit hook rejects for any touched file. It was rewritten as an equivalent `try/catch/finally`.
4. Locales: the `translate` skill is not installed in this runtime. Every non-English `agent.json` carries the English text for the new keys, so `check:sync` passes; the strings still need translation.
5. "The Celery task arguments contain no token" check (1.1 list) moves to 1.2, where the catalog task is created (`test_attach_enqueues_catalog_with_ids_only_and_lists_repositories`).
6. `base_ref` validation lives in `plane/agent/services/branch_name.py` (`is_valid_ref_name`), next to the branch-name helper that 1.8 adds.
7. Removed (detached) installations are hidden on the GitHub detail page (1.3 AC "disappears"). The mockup has no control to attach a removed installation again; the API allows it (`POST github/accounts/<id>/attach/`). This is a product gap for the user to decide.
