# Command executor progress and review

## Summary

Add bounded command execution inside the existing Code Docker boundary as part of story 3.1.
This is an internal primitive; the product command tool is not complete.

## Behavior

- Validate exact argv and an integer timeout from 1 to 600 seconds.
- Run in the assigned Worktree with no network and a minimal environment.
- Capture at most 8192 bytes while counting discarded output.
- Independently bound the host Docker client pipe to 65536 bytes.
- Recheck authority before launch and retain a request-linked execution record.
- Stop the container after each command and after cancellation, including detached descendants.
- Keep the record after lost acknowledgement and reject replay.

## Review

Intent: execute approved project commands without expanding the Docker boundary or replaying uncertain work.
Verdict: Comment; API grant binding, MCP routing, and historical reconciliation are still required before product use.

Critical issues: no remaining issue found within this internal primitive's checked scope.
The review identified a possible supervisor-pipe bypass through same-UID file descriptors.
The host Docker pipe now has an independent limit, with a native two-million-byte output check.

Major issues: complete exact permission binding and retained command reconciliation before enabling Agent access.
The current MCP allowlist has no command tool, so this partial implementation is not exposed.

Minor issues: none found after targeted lint and format checks.
The executor reuses the existing container identity, effect records, and settlement checks.
The tests use real Docker for output, timeout, detached children, authority rejection, cancellation, and acknowledgement loss.
There is no new dependency or unverified Harness capability.
No new user decision is required for this primitive.

## Remaining acceptance work

Bind the exact argv, timeout, Worktree, Run, turn, and lease to a dedicated permission action.
Consume it through the current Plane API and serialize execution with the existing Run effect lock.
Persist a command result before acknowledgement and reconcile uncertain outcomes without replay.
Expose a bounded MCP command tool only after those contracts pass native and database checks.
Then prove the complete Claude-to-Plane command and test flow over HTTP.

## Verification

The initial two new Docker checks passed in 4.484 seconds.
After authority and Stop checks, the suite ran 21 tests in 27.042 seconds with five native Claude checks skipped.
After the host pipe limit and malformed-input checks, the final suite ran 22 tests in 29.614 seconds: 17 passed and five native Claude checks skipped.
All five new tests executed and passed.
Targeted Ruff lint and formatting checks passed.
The fixtures stopped and removed their Code containers; no owned listener remained.

## Exact permission contract

Plane now accepts a strict `process.execute` scope with exact ordered argv and timeout.
Its effect must contain the same values and the exact visible command, with no added fields.
The Worker proposal uses the same canonical representation and hash.
Run grants cover only identical commands, timeout, and Worktree.
One-use consumption retains the existing lease, Stop, capacity, repository, and member authority checks.
Plane blocks another command after consumption until its matching result event is confirmed.
The shared effect gate preserves the existing commit and push rules.
The API contract tests passed twice with 36 checks, including malformed scope/effect, pending permission, changed consumption, one-use behavior, inherited Run grant, changed command/timeout, and missing result.
The Worker foundation suite passed seven checks, including the shared command hash and changed-effect hashes.
The final API suite, with an independent matching-hash check, passed 37 checks in 15.91 seconds.
The command is still absent from the MCP allowlist.
Durable command identity, historical reconciliation, consumption binding in the executor, and the full HTTP flow remain required.

## Durable executor binding

The internal executor now holds the Run effect lock, verifies the exact command proposal, checks retained Worktree identity without recreating it, and requires the current Code slot.
The Docker primitive validates its command hash before container launch.
It stores exact `command_prepared` identity before the consumption callback.
The callback consumes once and rechecks current authority before any command starts.
After the container stops, the primitive stores validated output as `command_completed` before posting the Plane result.
Confirmed event UUID and sequence are required before record clearance.
Changed caller input cannot replace the copied argv after grant validation.

Real Docker checks prove normal delivery, uncertain consumption, revoked authority after consumption, and lost result acknowledgement.
Unknown consumption retains a prepared record with no file effect.
Lost result acknowledgement retains the exact completed output and Worktree effect.
Both cases block another execution before a second consume.
A native child-process check exits with `os._exit` before and after result persistence and proves both records survive executor death, with no abandoned temporary files.
The combined Docker, registry, and foundation suites ran 40 tests in 32.589 seconds: 35 passed and five native Claude checks skipped.
The final three focused checks passed in 3.970 seconds, including invalid-hash rejection before container creation and copied argv under callback mutation.
Targeted lint, format, local documentation links, and diff checks passed.
No owned container or broker listener remained after verification.
Historical reporting, stale-slot reconciliation, MCP routing, and the complete HTTP command flow remain required.

## Historical reporting and slot recovery

The command reconciliation endpoint now validates exact original permission, lease, hash, command, and bounded result identity.
It stores one completed or unknown observation under the Run lock.
Unknown observations close uncertain consumption and require a later accepted user reply before another command.
The original request remains closed even if Plane did not consume it.
Historical facts can be reported after expiry, Stop, or removal of the approving member without authorizing another effect or releasing capacity.
Completed observations must match any existing normal result.

The Worker stops the prior Host, Git processes, and verified container before reporting.
It holds the Run effect lock, checks retained Worktree and command identity, confirms the receipt, and checks the record and container again before clearance and slot release.
A malformed receipt preserves both the record and capacity.
Native Docker recovery checks preserve later source edits and the staged index.
The first 41 API checks passed in 16.93 seconds.
The expanded permission and lease suites passed 57 checks in 23.03 seconds and, after strict completion validation, 57 checks in 22.65 seconds.
They cover consumption/report races, one-use closure, explicit retry, live lease identity, expired lease, Stop, and removed member access.
The focused native recovery check passed in 2.202 seconds.
The combined native suites passed 37 checks with five native Claude checks skipped in 35.332 seconds before the hard-link fix.

Review found an actual hard-link escape in arbitrary command writes.
The real Docker reproduction failed because the command was not rejected.
Command execution now rejects shared hard links and special files before container creation and again before execution.
The file-write executor keeps its existing atomic replacement behavior.
MCP routing, real paired HTTP command delivery/recovery, and full product checks remain required.
After the hard-link fix, the final Docker, registry, and foundation suites ran 43 tests in 34.377 seconds: 38 passed and five native Claude checks skipped.
The new hard-link rejection and all command recovery checks executed and passed.
Targeted lint, formatting, local documentation links, and diff checks passed.

## Code MCP and normal HTTP delivery

The Code broker now exposes `plane_run_command` with a strict operation UUID, bounded argv, and integer timeout.
The Claude allowlist and trusted prompt include this tool; Q&A excludes it.
One session operation can wait or execute at a time.
Denied permission starts no container and consumes no grant.
The tool reports actual command failure, timeout, and output truncation.

The focused broker, Docker, and driver checks ran 28 tests in 10.518 seconds: 26 passed and two optional native Claude checks were skipped.
The new native Claude command check passed in 7.009 seconds with Sonnet under the read-only Host profile.
The paired normal HTTP command mode passed with one API check in 44.13 seconds and one native check in 54.560 seconds.
It verifies Q&A, the same-turn Code handoff, separate file-write and command approvals, exact persisted command output before commit, the local Run-branch commit, and Stop at the next pending write.
The polling Worker, Claude, MCP, Docker, Git, member decisions, grant consumption, and Django endpoints are real.
The Git fixture remains local and this mode does not prove live GitHub delivery.
Both handles exited successfully, and the owned test stack was removed.
Paired HTTP command restart recovery, all four Harnesses, network and path grants, and full product checks remain required.

## Paired HTTP command acknowledgement loss

The new fixture kills the actual polling Worker while Plane holds the command result response after persistence.
It expires the lease through the production task and starts a new polling Worker.
The historical observer confirms the original completed result before clearing the retained record and releasing capacity.
The Run remains stale, with no new claim, command approval, or commit.
Later human source edits, the index bytes, and the Run and default-branch HEAD remain unchanged.
The paired acknowledgement-loss mode passed with one API check in 34.56 seconds and one native check in 44.443 seconds.
The fixture now also has a delivery-loss mode that holds the result before Plane stores it.
That mode includes a Worktree execution counter to detect command replay.
The delivery-loss mode passed with one API check in 37.95 seconds and one native check in 38.041 seconds.
The counter remains exactly one after recovery; later human source edits, index bytes, and both branch HEADs remain unchanged.
Plane records one completed historical result without a normal result event, new claim, or commit.

The existing commit acknowledgement-loss mode also passed after the shared restart helper change: one API check in 35.95 seconds and one native check in 36.164 seconds.
All paired handles exited successfully.
Their private credential fixtures and the owned test stack were removed.

## Full Worker regression gate

The full Worker suite ran 116 tests in 160.183 seconds with the installed Docker image and authenticated Claude Sonnet.
115 passed; the standalone paired HTTP check skipped because it requires its separate fixture server.
Its normal command, both command restart modes, and existing commit restart regression had already passed separately.
All optional native Claude checks ran in the full suite.
Final Worker and HTTP-fixture lint, Worker formatting, local documentation links, and diff checks passed.
The final resource check found only the three unrelated pre-existing containers and no owned API or broker listener.
No whole story is marked done; the goal remains active with network/path enforcement and the other audit gaps outstanding.
