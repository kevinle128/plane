# Repository binding and pull request policy progress

## State

Phase 1 remains in progress.
Stories 1.5 through 1.8 have API and web implementation, but they do not yet have browser fidelity checks or Run delivery integration.
Do not mark these stories done in sprint status yet.

## Implemented

- Project creation can bind one GitHub repository identity, base ref, and installation to a project.
- The API checks the active workspace grant and verifies the selected repository on its GitHub result page before saving.
- A workspace and repository uniqueness constraint prevents a second active binding.
- The project API returns the saved repository and reports whether its installation remains granted.
- The project form shows a search box, owner filter, installation groups, unavailable repositories, a no-repository choice, and a missing-connection state.
- Plane now keeps an indexed repository catalog per granted installation.
- A Celery task refreshes one GitHub page at a time and only publishes a snapshot after its final page succeeds.
- The picker searches the catalog through a cursor API and loads one page of results per request.
- An interrupted refresh keeps the prior complete snapshot, and the next refresh can resume its saved page.
- The GitHub policy stores draft pull request, conclusion mirroring, and branch format settings independently of the connection.
- Workspace members can read the policy, while only workspace administrators can change it.
- The branch name helper makes both supported formats from an issue identifier, project identifier, and Run ID.

## Verification

- `pytest` for GitHub authorization, policy, repository binding, and branch names: 12 passed.
- Project API regression tests: 25 passed with the GitHub tests, for 35 passed total before policy changes.
- The repository migration ran with Django migrations enabled and 3 binding tests passed.
- `makemigrations --check --dry-run` reported no changes after the policy model was added.
- Web TypeScript and focused OxLint checks passed.
- The web production build and focused format checks passed.
- The catalog migration ran with Django migrations enabled and 13 focused tests passed.
- After the review fixes, 39 catalog, GitHub, branch, and project regression tests passed.
- Ruff lint and format checks, web TypeScript, and the web production build passed after the final edits.
- A 50,000-row PostgreSQL probe used the trigram GIN index for a substring search and reported 1.855 ms execution time on the local test stack.
- This probe measures one database query; it does not prove end-to-end latency or large-workspace throughput.

## Remaining work and risks

- Check the project picker and GitHub settings in the browser at supported widths and themes.
- Complete live GitHub App setup and test authorization, grant changes, repository selection, and disconnect against GitHub.
- Connect policy reads to Run creation and pull request delivery.
- Persist a Run branch at creation and add a database uniqueness check before claiming branch uniqueness across concurrent Runs.
- Run end-to-end catalog refresh and search checks with real GitHub grants, concurrent users, and larger installation counts.
- Test Celery broker loss and process restart during a multi-page refresh in the deployed stack.
- Refresh sprint status through its generator once the missing `sprint_plan.py` tool is restored.
- The generated sprint status still lists these stories as backlog; its current labels do not reflect implementation progress.
- A repository can move to another GitHub result page between selection and project creation; the API rejects that selection and asks the user to refresh it.
