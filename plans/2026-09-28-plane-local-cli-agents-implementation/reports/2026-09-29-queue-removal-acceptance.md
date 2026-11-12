# Queue removal acceptance

## Native HTTP boundary

Extend the existing paired native HTTP check with `queue_remove`.
Use the actual polling Worker, authenticated Claude, production private MCP app, Host OS boundary, member API, and isolated database.
The initial Run and local repository are fixtures.
No browser mention, GitHub delivery, other Harness execution, or Code effect is claimed.

Hold the initial turn's result before persistence and submit two member messages while the Run is active.
Cancel the first queued message through the member API.
A fresh pending queue read returns only the second message with waiting count 1.
Release the initial result so the Worker reaches the safe delivery boundary.
It dispatches the second message, and native Claude acknowledges the request through its output.

Hold the Worker's acceptance HTTP request before Plane persists acceptance.
The message remains dispatching.
A member removal attempt returns HTTP 409 with `The message is dispatching.`.
Release acceptance and complete the native turn.
A new removal attempt returns HTTP 409 with `The message is accepted.`.
Fresh pending queue reads return an empty list and waiting count 0.

The database verifies the first message is cancelled, has a cancellation timestamp, and has no acceptance timestamp or turn assignment.
It has one retained cancellation audit event and no dispatch or acceptance event.
Only the second message has one dispatch event, one acceptance event, and a turn-2 answer with its `QUEUE_2` marker.
The answer does not contain the withdrawn `QUEUE_1` marker.
No permission request is created, and source content stays unchanged.

The native side passes in 31.31 seconds.
The API side passes in 21.15 seconds.
Focused Ruff lint and formatting pass for both changed fixture files.

## Browser refresh

Use the actual web app on localhost port 3000 and Django API on localhost port 8000 with a separate restored browser fixture.
The browser fixture has no running Worker.
Submit `Withdraw this direction before delivery.` through the active Run composer.
Focus its numbered remove action and activate it with Enter.
Reload the complete page and reopen the same Run.

The Queue shows only the two earlier messages and waiting count 2.
The withdrawn message is absent from the pending list.
The timeline retains its queued observation and the new `Queued message removed` audit event.
PostgreSQL verifies the new message at sequence 4 is cancelled while the earlier two pending messages remain queued.
The [375 px refresh image](./queue-ui/removed-after-refresh-375.png) was inspected and shows the retained audit and correct queue without horizontal overflow.
The earlier [Queue UI check](./2026-09-29-queue-ui-progress.md) also proves dispatching rows display `Sending · not yet accepted` and disable removal.

The first fixture restore was attempted before PostgreSQL was ready.
A subsequent restore overlapped migration and failed on existing tables.
Stop that failed migration, reset only the owned isolated test schema, restore successfully, and run migrations before browser testing.
The completed browser check uses the successful restore and migration.
No product database or unrelated process is changed.

## Story 2.16 completion audit

| Acceptance criterion | Direct evidence |
| --- | --- |
| Removing a queued message cancels it and the Worker never delivers it | Real member cancellation, actual native drain, and persisted absence of dispatch and acceptance for the withdrawn message |
| Removal after dispatch or acceptance shows actual state | Held native acceptance boundary and HTTP 409 responses with exact current state; production dispatching UI names the state and disables removal |
| Refresh excludes cancellation from waiting count and retains audit | Full production browser reload and reopened panel, database state, retained timeline audit, and inspected image above |

All three criteria have direct evidence.

## Review

**Summary:** Withdrawal before delivery is durable, and later removal attempts preserve and report dispatch or acceptance.
**Critical issues:** None found in the delivered cancellation flow.
**Major issues:** The remaining 39 stories and complete four-Harness goal require their own evidence.
**Minor issues:** Native and browser checks use separate isolated fixtures.
**Positive feedback:** The check tests both sides of the dispatch boundary through existing production endpoints.
**Questions:** AD-7 and DNS decisions remain pending and are not assumed.
**Verdict:** Mark Story 2.16 done and keep the complete goal active.

## Cleanup

The native Worker and paired API fixture exit successfully.
Stop the owned browser, web process, and browser API process.
Remove both isolated Compose projects and networks.
Remove the private HTTP fixture directory and temporary overrides.
No owned listener remains on ports 3000, 8000, 8009, 8769, or 8811.
No credentials or sessions are stored in the report or checkout.
