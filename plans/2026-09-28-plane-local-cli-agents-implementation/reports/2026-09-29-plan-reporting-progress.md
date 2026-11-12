# Run plan reporting and disclosure

## Scope

Continue Story 2.10 with a real way for the restricted Harness to report its plan.
The native command disables built-in tools, so parsing TodoWrite alone does not provide a plan producer in this execution path.
Both Q&A and Code now expose `plane_report_plan` through their existing private MCP endpoint.
The tool records a complete bounded snapshot through the existing Plane event API.
It supplies the Run, turn, and lease from the Worker claim and accepts no replacement identity from the Harness.
It grants no effect access and does not enable native writes.

The schema permits at most 100 steps, bounded titles, done/doing/todo states, and an optional reported estimate.
The complete JSON payload must fit the existing event limit.
An empty step list clears the plan.
The operation UUID creates a stable event key so an identical delivery retry returns its stored receipt.
Pending Stop or steer and a cancelled session block new reports.

## Native and API evidence

Actual authenticated Claude reports two snapshots through the production Code MCP app and Host OS boundary.
The first contains done, doing, and todo steps without an estimate.
The second updates step states and includes the explicitly requested estimate.
The native check passes in 6.15 seconds with no permission request or grant consumption.
Its Plane client is controlled; it does not prove the complete native-to-HTTP event flow.
The native approved file-write regression also passes in 5.57 seconds with the updated tool inventory.

The shared Q&A and Code MCP checks reject extra identities, invalid states, oversized steps and payloads, invalid estimates, pending Stop, and cancelled sessions.
All 36 Worker checks pass in 9.89 seconds, with three explicit native opt-in skips.
These skips are separate from the two executed native checks above.

The real Plane event endpoint initially accepts a new plan for turn 99 while its Run is in turn 1.
The focused endpoint regression fails in 1.31 seconds.
The endpoint now rejects a new plan whose reported turn differs from the current Run turn.
Receipt lookup occurs before this check, so retrying an already stored event remains valid after the Run advances.
The contract checks cover this prior-turn receipt and reject a new event from the prior turn.
All 16 lease and Run-control API checks pass in 5.33 seconds.
The existing latest-plan, bounded-history query count, invalid payload, idempotency, and member-access checks remain in that gate.

## Production browser evidence

Use the isolated `plane-plan-ui` Compose stack, restored browser fixture database, current migrations through 0142, API port 8000, and web port 3000.
Authenticate through the real Plane password flow.
Plan state changes in this browser check are controlled database fixtures, not native Worker reports.

The existing view differs from the approved handoff: done labels have a strike-through, the todo circle has a solid border, and the native disclosure marker sits on the left.
The [before view](./plan-ui/before.png) records these differences.
The repaired plan uses the approved semantic colors, state circles, dashed todo border, normal done text, current-step meta, and right-aligned chevron.
The disclosure has a visible keyboard focus outline.
The spinner respects reduced motion.
Screen readers retain each step's state label.

At 375 pixels, the plan shows all three states, the progress count, and the reported estimate without horizontal document overflow.
The [reported-estimate view](./plan-ui/estimate-375.png) records these states.
When the latest snapshot omits its estimate, the header shows only the progress count.
The [latest view](./plan-ui/latest-375.png) records two done steps and one doing step without an estimate.
Enter collapses the plan and Space expands it.
Closing and reopening the Run keeps the chosen disclosure state.
Reloading also retains the collapsed choice under the member and Run key.
The [collapsed view after refresh](./plan-ui/collapsed-after-refresh.png) records this state.
Reopening after a newer snapshot retains the disclosure choice and shows the latest progress and estimate.
A Run with no reported plan has no empty plan section; see the [no-plan view](./plan-ui/no-plan-375.png).

## Fresh-page polling repair

The earlier stable callback repair passed the warm-cache test but stopped polling after a fresh page load.
The API advanced to sequence 80 while the panel retained sequence 79 and an older plan.
SWR invokes the interval callback with cached data, which can be undefined before the first response.
Its polling effect depends on callback identity; this behavior is confirmed by the [installed-version upstream source](https://github.com/vercel/swr/blob/v2.4.2/src/index/use-swr.ts#L687).
The stable callback now uses the initial Run when cached data is absent.
This starts polling on a fresh page without letting the elapsed clock reset the timer.
The Open run button also identifies its dialog with `aria-haspopup` and `aria-controls`.

The browser regression now reloads before opening the exact Run panel.
It checks that the clock ticks, then requires both capacity state changes to reach the same panel without remounting.
Removing the initial fallback reproduces a failure in 17.99 seconds, including reload and the 12-second observation limit.
The final regression passes in 9.25 seconds.

## Gates and review

All nine existing web helper and production PR rendering checks pass.
Web type generation and TypeScript pass.
Focused web lint and formatting pass without warnings or errors.
Touched Python lint and formatting pass.
The existing Vite path-plugin, package module-type, and browser-externalized Node module advisories remain in development logs.

**Summary:** The restricted Harness can now report bounded plans, Plane rejects new plans from the wrong turn, and the production view follows the handoff and saved disclosure.
**Critical issues:** The reproduced turn and fresh-page polling defects are repaired.
**Major issues:** The complete native-to-HTTP plan delivery check and all four Harness integrations remain required.
**Minor issues:** The current browser plan snapshots are controlled fixtures; they are not evidence of native Worker publication.
**Positive feedback:** The implementation reuses the existing event authority, idempotency, turn metadata, MCP transport, and member plan endpoint.
**Questions:** The pending AD-7 runtime decision remains separate and is not enabled.
**Verdict:** This first check kept Story 2.10 in progress pending native-to-HTTP verification.
The later [HTTP acceptance report](./2026-09-29-plan-http-acceptance.md) completes that check and records the criterion-by-criterion completion audit.

## Cleanup

The owned API and web processes exited after SIGINT.
The named browser session was closed.
The isolated Compose containers, volumes, and network were removed.
No listener remains on ports 3000, 8000, 8769, or 8811, and no container remains under the owned Compose project.
The temporary Compose override was removed.
The report and screenshots remain as acceptance evidence.
