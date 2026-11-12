# Stopped Run resume acceptance

## Scope and criteria

Complete the three Story 2.18 criteria in the [epic breakdown](../../2026-09-28-plane-local-cli-agents-epics/epics.md).
The [native recovery report](./2026-09-29-stopped-recovery-progress.md) proves actual polling Worker and Claude context reconstruction, clone verification failure without replacement or Harness launch, fenced Retry, and restored original clone completion.
The [browser check](../../../apps/web/tests/agent-stopped-resume.e2e.mjs) closes the production panel acceptance with the actual web app and isolated API.
Its Worker is a declared HTTP fixture, not a native Harness execution claim.

| Criterion | Direct evidence |
| --- | --- |
| Reply after Stop starts a new turn on the same Run and retains clone/history | Keyboard Send reply, same Run ID, turn 2, registered clone path, and exact retained event prefix; actual native Stop/reply recovery in the linked report |
| Resume after the old process exits uses durable same-Run context | Actual polling Worker and new Claude process complete turn 4 with current issue, comments, earlier answer and denied decision; clone inode and HEAD remain unchanged |
| An unverifiable clone produces a recoverable error without another CWD | Actual native missing-clone check prevents another clone or Harness; browser reload shows repair instructions and keyboard Retry; restored original clone completes the queued request |

## Reproduction and repair

The first browser run fails with `Pending repository recovery must remain visible`.
Retry moves a recoverable failed Run to Created, while the panel only mounts recovery controls for Stale or Failed.
Keep recovery controls mounted while Retry is pending.
Show an explicit waiting message without asserting that Created is Stale or that a heartbeat is missing.
Keep Last progress and Mark failed limited to Stale.
Disable repeated Retry until the Worker claims the Run.

## Verification

The durable browser check passes before and after read-only review.
It verifies recoverable error persistence, a disabled failed composer, no Mark failed action, keyboard Retry, pending state before Worker pickup, and persistence after a full reload.
It restores the moved native Git clone and uses actual Worker claim, reconciliation, repository verification, context, queue dispatch/acceptance, and result endpoints.
The final panel retains the pre-Stop progress, failed result and new conclusion after a full reload and panel reopen.
The historical event prefix, clone inode, HEAD and contents remain unchanged.

The existing Stop browser check also passes on this isolated stack.
Web type checking passes.
Focused lint has zero errors and warnings; formatting passes for the two production components and browser check.
Read-only review finds no concrete defect in the incremental Created and Stale recovery paths.
The [completed panel capture](./stopped-resume-ui/completed-after-reload.png) records the rendered retained history.
This does not claim full design-scene acceptance or a clean browser console for Story 2.8.

The fixture reset initially retained soft-deleted rows and caused an invalid-payload response; remove those rows only in the disposable fixture database before rerunning.
The macOS fixture initially used a noncanonical `/var` path; use its resolved `/private/var` path to match the repository contract.
Neither fixture correction weakens a production check.

## Cleanup

Stop the owned web and API processes and remove the isolated Compose stack after verification.
Remove the private Worker token and clone fixture directory.
Keep no authentication material in the checkout or report.
