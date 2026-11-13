# Code resume acceptance

## Verified behavior

Story 3.8 meets all three acceptance criteria.
The private paired fixture input is `{"model":"sonnet","code_resume":"normal"}`.
The actual polling Worker, native Claude, Code MCP, Django API, Git, and Docker complete an active Code Stop and a subsequent member reply in the same Run.
The old native process exits before a new native Harness starts.
The new turn receives a fresh Code slot after the waiting job releases it.
The original clone and Worktree retain their paths and inode identities.
An actual Host `lsof` check confirms that the new Harness uses the original Worktree as its current directory.
The actual Worker context response contains earlier turns, accepted member messages, and the previous network permission decision.
The new conclusion refers to the retained human file edit and the prior permission decision.
The file remains unchanged while the new write permission is pending.
A separate member Allow once decision permits the actual Docker write.
The Run completes turn three with the same branch, branch HEAD, retained history, and declared existing PR.
The PR fixture proves retention, not live GitHub publication.
All Code slots are released at completion.

## Validation

The final native check passes in 74.953 seconds.
The paired API check passes in 75.33 seconds.
Ruff passes for both changed fixture files.
The earlier native check also passed; its paired API failure was an obsolete final assertion that still expected Stopped after successful resume.
The final check uses the corrected mode-specific assertion.
No production change was required for the normal native resume check.
The completed private fixture was removed after its success marker was verified.

Logs are `/tmp/plane-code-resume-normal-green-native.log` and `/tmp/plane-code-resume-normal-green-api.log`.
Source checks are in [the native Worker fixture](../../../apps/agent-worker/tests/test_live_api.py) and [the paired API fixture](../../../apps/api/plane/tests/contract/app/test_agent_worker_http.py).

## Invalid repository identity and grant

The actual missing-Worktree mode passes in 74.128 seconds on the native side and 74.32 seconds on the API side.
It moves the original Worktree away from its registered path.
The Run records a recoverable failure without recreating the directory, starting a Harness, or reserving another Code slot.
The retained directory keeps its inode and source content.

The final changed-remote mode passes in 58.879 seconds on the native side and 87.24 seconds on the API side, including the browser hold.
It changes the actual Git origin to another repository before the member reply.
The Worker refuses that identity without a native Harness or Code slot.
The clone, Worktree, branch, declared PR, and unaccepted member message remain retained.

The revoked-grant mode passes in 74.071 seconds on the native side and 138.42 seconds on the API side, including the browser hold.
The fixture removes the actual installation grant before resume pickup.
The production claim records repository unavailability and leaves the message queued without a Harness or Code slot.

## Browser error checks and repairs

The production browser uses the actual native fixture Run and its stored member session.
The changed-remote browser check first fails because Code recovery only mentions restoring the clone.
The shared recovery component now also names the original Worktree and remote for Code Runs.
Q&A recovery keeps its existing clone instructions.
The final browser check passes with the corrected message, full reload, keyboard Retry, pending Retry after another reload, and no horizontal overflow at 375 px.

The revoked-grant browser check first fails because the retained Run still presents a repository selector.
The API already rejects rebinding after a clone exists.
The repository component now uses the existing clone identity to show an explicit access error and the existing GitHub access link.
It stops repository candidate queries and removes the unusable selector for retained Runs.
Fresh Runs retain their original selector.
The final browser check passes with the explicit original-grant instructions, disabled composer, reload, and 375 px layout.
No GitHub authorization or grant restoration is claimed by these checks.

The [remote narrow image](./code-resume-ui/remote-375.png) and [grant narrow image](./code-resume-ui/grant-375.png) were inspected.
The corresponding 1280 px images are retained in the same directory.
The runnable browser check is [agent-code-resume.e2e.mjs](../../../apps/web/tests/agent-code-resume.e2e.mjs).
An earlier browser attempt reached Retry but blocked on an already open panel after reload and exceeded the API hold.
The corrected test closes the panel before reload and handles an existing panel before opening it.
The final paired run, not that interrupted attempt, supplies the passing remote evidence.

Ruff, focused OxLint with zero warnings, formatting, and web type checking pass.
Read-only review found no concrete fixture or UI regression and confirmed that hooks stay unconditional and fresh repository selection remains intact.
Final logs are `/tmp/plane-code-resume-worktree-native.log`, `/tmp/plane-code-resume-worktree-api.log`, `/tmp/plane-code-resume-remote-green-native.log`, `/tmp/plane-code-resume-remote-green-api.log`, `/tmp/plane-code-resume-remote-final-browser.log`, `/tmp/plane-code-resume-grant-native.log`, `/tmp/plane-code-resume-grant-api.log`, and `/tmp/plane-code-resume-grant-browser-green.log`.
All native fixture processes exit, completed private fixtures are removed, and the owned browser session is restored.

## Actual stopped panel reply and polling repair

The normal browser mode pauses the native fixture after actual active-command Stop and waiting-job slot transfer.
The browser opens that exact stopped Code Run, fills its reply composer, and sends the task with keyboard Enter.
The native fixture obtains the actual member message by its exact body instead of a synthetic client key.
The API verifies that message against the private browser task and confirms one accepted event in turn three.
All existing native checks for a new Harness, retained Worktree inode, actual `lsof` CWD, fresh slot, original branch and HEAD, prior context, separate write approval, and actual Docker content remain in force.

The first panel reply completes natively in 124.243 seconds, but the open panel remains at Waiting for pickup.
The browser is visible during this failure.
The stable SWR interval callback returned zero for the initial Stopped Run and did not restart the stopped polling timer after the reply changed Run state.
The shared panel now passes a numeric interval and updates it from current Run state through the existing React state and effect pattern.
Active Runs restart polling; terminal Runs stop polling unless conclusion mirroring is pending.
The first paired API run passes in 228.50 seconds after the repaired panel updates and reloads.

A fresh full run then passes without any source change or HMR during execution.
The native Worker passes in 71.252 seconds and the API passes in 75.92 seconds.
The browser sends the actual stopped reply, observes completion through polling, retains the previous decision strings and PR, closes and reloads the same panel, and confirms exactly one Run card and no horizontal overflow at 375 px.
The [normal narrow image](./code-resume-ui/normal-375.png) was inspected.
The [browser result](./code-resume-ui/normal-browser-check.json) records the successful reply, reload, and narrow checks.
Final fresh-run logs are `/tmp/plane-code-resume-normal-final-native.log`, `/tmp/plane-code-resume-normal-final-api.log`, and `/tmp/plane-code-resume-normal-final-ui.log`.
Ruff, focused OxLint with zero warnings, formatting, and web type checking pass after the polling repair.
Read-only final review finds no concrete Story 3.8 criterion gap.

## Completion audit

| Criterion | Evidence |
| --- | --- |
| Panel reply starts a new same-Run turn in the retained Worktree after a Code slot | Actual stopped browser reply, native turn three, fresh slot, retained clone/Worktree inode and paths, and actual Harness `lsof` CWD. |
| Old Harness exit preserves durable conversation and branch identity | Old PID/start identity is absent, new PID differs, actual delivered context has prior turns/messages/decisions, and Git branch and HEAD remain equal. |
| Unverified Worktree, remote, or grant shows recovery error without another launch | Actual missing-directory and changed-origin recoverable failures, revoked-installation claim failure, no new Harness or slot, retained queued message and PR, and browser recovery/access errors after reload. |

Mark only Story 3.8 done.
Other Harness execution, live GitHub grant restoration and publication, and sustained Mini capacity acceptance remain in their owning stories.
