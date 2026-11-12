# Branch format acceptance

## Result

Story 1.8 meets its four acceptance criteria.
The production policy, branch reservation, and Git Worktree implementation required no change.
The tests now cover both formats through policy changes and two Runs on the same issue.

## Browser evidence

The [production browser check](../../../apps/web/tests/agent-github-branch-policy.e2e.mjs) opens the actual GitHub settings page with an administrator session.
It uses a declared connection record in the isolated `plane` database to make the existing policy controls visible.
It does not authenticate with GitHub or send a GitHub request.
The workspace starts without a saved policy.
The native selector defaults to `agent/<issue-identifier>-<run-short-id>` and presents exactly the two approved formats.
Both choices save through the actual API and remain selected after full browser reload.
The other policy fields retain their defaults.
The selector has the accessible name Branch format and takes keyboard focus.
Light and Dark use different semantic field surfaces.
The 375 px page has no horizontal document overflow or page errors.
The inspected desktop and narrow captures show the policy rows and native selector.
The existing workspace Run branch values remain unchanged during these setting changes.
The check removes only its own declared connection and policy records and restores the original disconnected state.

## API and actual Git evidence

The [worktree API contracts](../../../apps/api/plane/tests/contract/app/test_agent_worker_worktree.py) now run the reservation, registration, and recovery flow for both branch formats.
After the workspace policy changes to the other format, preparation retries, registration retries, and later claims retain the original branch and base.
The separate same-issue check creates two Run records with the same issue, Agent, and repository binding.
Each Run claims and reserves its own branch through the actual Worker endpoints.
The suffixes differ, and both exact branch names follow the selected format.
The [policy contract](../../../apps/api/plane/tests/contract/app/test_agent_github_policy.py) checks default reads, saved policy, invalid format rejection, and administrator-only changes.
The [branch utility check](../../../apps/api/plane/tests/unit/test_agent_branch_name.py) checks exact names and invalid identifiers.
The [native Worktree check](../../../apps/agent-worker/tests/test_worker_foundation.py) now creates actual Git Worktrees for both flat and project-prefixed Agent branches.
It keeps local edits and added files through repeated calls and commits, preserves the original clone content, and rejects changed branch, changed base, detached branch, or linked Worktree identity.

## Acceptance matrix

| Criterion | Direct evidence |
| --- | --- |
| New selector uses the default format | Actual production browser without a saved policy; policy API default contract. |
| Both formats can be selected and survive refresh | Actual native selector options, real API saves, database reads, and full page reload for each format. |
| Separate Runs on one issue have distinct names in either format | Parametrized real Worker claim and preparation endpoints with two Run records on the same issue. |
| Existing branch remains after workspace format changes | Both parametrized preparation, registration, and later claim flows retain the stored branch; actual Git Worktrees retain branch identity and edits. |

## Validation

- Policy, Worktree, and branch utility gate: 10 checks pass in 3.67 seconds.
- Actual Git Worktree check: one test with two format subtests passes in 1.017 seconds.
- Production browser gate passes without page errors.
- Ruff lint and format, OxLint, and oxfmt checks pass for the changed test files.
- Read-only quality review found no concrete defect or acceptance gap.

The local logs are `/tmp/plane-branch-policy-contract.log`, `/tmp/plane-branch-worktree-both-formats.log`, and `/tmp/plane-branch-policy-browser.log`.
The inspected captures are `/tmp/plane-branch-policy.light.png` and `/tmp/plane-branch-policy.375.png`; the Dark desktop capture is `/tmp/plane-branch-policy.dark.png`.
This report does not establish real GitHub authentication, installation, or publication.
Those requirements remain in their owning stories.
