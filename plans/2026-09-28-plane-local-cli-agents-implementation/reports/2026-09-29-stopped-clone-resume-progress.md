# Stopped Run clone verification progress

## Reproduction

Use the existing paired HTTP acceptance fixture with `follow_up_context` and `stopped_clone_missing`.
The actual polling Worker runs authenticated native Claude through the production repository tools and Host boundary.
The member completes Q&A turn 1, starts another native Harness process, requests Stop through the real HTTP API, and waits for Stopped with no retained Harness record.
Move the actual Git clone out of its assigned path and submit another member reply on the same Run.
A local bare Git remote supplies fixture transport only; it executes real Git clone operations and does not claim GitHub access.
Before the fix, the Worker creates a replacement clone and runs the reply.
The native check fails with `Resume created a replacement Run clone` in 21.714 seconds.
The API side also reports the failed native check.

## Repair and evidence

The shared repository preparation function now accepts Plane's retained clone path.
A registered path must equal the assigned Run path and pass the existing directory, symbolic-link, Git root, origin, and clean-state checks.
A missing registered clone fails before Git clone or Harness launch.
Initial unregistered clone creation keeps its existing behavior.
The production turn controller supplies the retained path on every claimed turn.

The same native HTTP check passes in 16.449 seconds.
The API fixture passes in 32.45 seconds.
The failure result retains the Run ID, registered clone path, previous event prefix, and original moved clone contents.
No replacement clone or Harness record exists.
The API verifies the acknowledged Stop, retained completed turn 1, absence of a result for interrupted turn 2, and failed preparation for turn 3.

Focused native clone and Worker foundation checks pass: seven tests in 1.285 seconds.
Four Worker control checks pass in 0.986 seconds after the live broker stops.
Three Code turn checks pass in 0.532 seconds.
The first concurrent control run collided with the live integration broker's fixed port; rerun it after that owned process exits.
Ruff lint and formatting pass for all six affected Python files.

## Story status and next work

Keep Story 2.18 in progress.
This first pass reports the preparation failure but does not yet provide same-Run Retry.
The later [repository recovery report](./2026-09-29-stopped-recovery-progress.md) adds the durable recoverable result and native original-clone recovery.
Also complete the production browser reply and history checks after Stop.
Do not treat a newly created clone as recovery of the original Run clone.
Four-Harness execution remains in the driver stories.

## Review

The read-only reviewer reports no concrete defect in the scoped repair.
The review verifies missing and different retained paths before clone or Harness launch, existing symbolic-link and origin checks, unchanged fresh-clone behavior, and explicit fixture transport limits.
Five focused clone and Worker control checks pass again after review in 1.049 seconds.
The full Story 2.18 acceptance criteria are not yet met.

## Cleanup

The native and API test processes exit successfully.
Remove the owned Compose stack and network, private fixture directory, and override file.
No owned listener remains on ports 8009 or 8769.
No token or member session is stored in the report or checkout.
