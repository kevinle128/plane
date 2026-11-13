# GitHub pull-request policy acceptance

## Outcome

Stories 1.6 and 1.7 meet all six acceptance criteria in the accepted epic breakdown.
The checks use the production browser, Django endpoints, database, Worker claim, and delivery policy consumers.
GitHub HTTP responses are controlled in the delivery tests; no live GitHub publication is claimed.

## Acceptance evidence

| Story | Criterion | Evidence |
| --- | --- | --- |
| 1.6 | Draft is on by default | First-time browser switch and stored policy both report true. |
| 1.6 | Save, reload, and delivery agree | Keyboard toggles save false and true; full reload and database agree; API PATCH, Worker claim, and PR request use the same saved value in both modes. |
| 1.6 | Non-admin cannot change | Member view retains a disabled checked switch; member PATCH returns 403 and the stored value remains unchanged. |
| 1.7 | Mirroring is off by default | First-time browser switch and stored policy both report false. |
| 1.7 | Save, reload, and delivery agree | Keyboard toggles save true and false; full reload and database agree; actual API PATCH controls whether the conclusion transaction queues a mirror. |
| 1.7 | Non-admin cannot change | Member view retains a disabled unchecked switch; member PATCH returns 403 and the stored value remains unchanged. |

The [browser check](../../../apps/web/tests/agent-github-branch-policy.e2e.mjs) also verifies both branch choices, unchanged historical Run branches, Light and Dark themes, keyboard operation, and a 375 px layout without horizontal overflow.
Saved screenshots show [Light](./github-policy-ui/light.png), [Dark](./github-policy-ui/dark.png), [375 px](./github-policy-ui/375.png), and the [read-only member view](./github-policy-ui/read-only.png).

## Reproduced defects and repairs

The member browser flow first failed because the workspace settings parent layout rejected the GitHub detail route before the child could show its read-only controls.
The route exception now permits only members on the exact GitHub detail path; other settings permissions and administrator-only PATCH remain in force.

The read-only screenshot showed identical track colors for checked and unchecked switches.
The computed-style assertion reproduced this defect with both colors equal to `oklch(0.9821 0 0)`.
The shared Switch now retains the accent track at reduced opacity when checked and disabled.
Its semantic state, disabled behavior, thumb position, and callbacks remain unchanged.
The final browser check passes with distinct track colors.

The browser fixture also exposed archived unique rows left by its previous soft-delete cleanup.
Production Disconnect already uses hard deletion.
The fixture now removes only its owned declared connection and policy with hard deletion and restores the original administrator role in `finally`.
Final database checks confirm that both fixture records are absent and the member role is restored to 20.

## Verification

- Policy API contract: 1 passed in 1.30 seconds.
- PR and conclusion consumers: 33 passed in 16.58 seconds.
- Final production browser: defaults, keyboard saves, reload, member read-only controls, branch retention, themes, and 375 px checks passed.
- Web and Propel TypeScript checks passed.
- Propel build passed and produced its generated output through the build command.
- Ruff lint and format, OxLint, and oxfmt checks passed for the affected files.
- Read-only review found no remaining source defect after the final browser check.

The API tests use actual saved settings through PATCH instead of direct policy creation for these acceptance cases.
The PR test verifies the selected draft value in the actual claim and outgoing creation body under a separate approved grant.
The mirror tests verify off/no queue and enabled delivery, with retained durable delivery and recovery coverage.

## Audit scope correction

The earlier audit required live GitHub publication for Stories 1.6 and 1.7.
That requirement exceeded these stories' three governing criteria each.
The audit now records these policy stories as done based on settings and consumer evidence.
Live GitHub authorization, PR publication, and comment delivery remain required in their owning stories, including 1.1, 3.1, and 3.9.
The full implementation goal remains active.
