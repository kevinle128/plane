# Stopped banner progress

## Reproduction and repair

The production panel showed only “Stopped. Reply to continue in the same Run.” after a recorded Stop.
The [design handoff](../../../claude-design/design_handoff_local_cli_agents/README.md) requires the member and time in this banner.

Member Run list and detail responses now include a nullable `stop` summary.
The summary selects the latest acknowledged Stop command and returns its actor ID, current display name, and exact acknowledgement time.
One correlated subquery uses the existing Run/state/sequence index.
It adds no per-Run request or unbounded transcript scan.
A newer pending Stop cannot replace the acknowledged summary.
Active and resumed Runs return null, even when an older Stop is retained.
The banner uses local time, a semantic `time` element, and a full date/time title.
Missing summaries retain the legacy explanation.

## Verification

The actual browser reproduction showed the missing member and time before the repair.
The complete [Stop browser check](../../../apps/web/tests/agent-stop.e2e.mjs) passes after the repair with actual web and API, a declared HTTP acknowledgement client, and a retained native Git clone.
It covers keyboard Cancel with unchanged state, confirmed Stop, pending reload, acknowledgement, exact actor/time, retained clone/history, and stopped reload.
The banner timestamp equals the stored command acknowledgement time.
The [rendered stopped panel](./stop-ui/stopped-after-reload.png) shows the member, time and enabled same-Run composer.

Two focused API checks pass in 2.24 seconds.
The summary contract check has 100 later events, two acknowledged Stop commands with different actors, and a newer pending command.
It verifies the latest acknowledged actor/time in both list and detail, then verifies null after resume.
The full lease/control and Run creation regression suites pass: 39 tests in 11.93 seconds.
Web type checking passes.
Focused Ruff and JavaScript lint report no errors; JavaScript lint reports no warnings.
Formatting passes.
The read-only review finds no concrete defect in selection, pagination independence, bounded queries or compatibility fallback.

## Fixture and remaining scope

A first private fixture name included an underscore outside the existing test argument pattern; rename only that fixture.
The archived database also retained soft-deleted rows that still occupy unique event and command keys.
Reset only those rows in the disposable database with SQL before running the complete check.
No production delete behavior changes.

Story 2.8 remains in progress for all remaining scenes, complete accessibility and long transcript coverage, dropdown focus and flows, the known browser error, and narrow title clipping.
No other story status changes.
Stop the owned browser, web and API process, remove the isolated Compose stack, and remove private token and Git fixture data after verification.
