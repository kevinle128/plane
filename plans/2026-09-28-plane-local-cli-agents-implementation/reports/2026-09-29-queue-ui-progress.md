# Queue UI acceptance progress

## Scope and environment

Check the production Queue component and composer against Story 2.14 and the approved composer design.
Use Chromium with the actual web app on localhost port 3000 and the actual Django API on localhost port 8000.
The owned Compose project is `plane-queue-ui`.
Restore the existing browser control fixture into its isolated PostgreSQL database and apply current migrations.
The initial Run, messages, and pending Send now command are fixtures.
No Worker or native Harness runs in this browser check.

## Reproduction and repair

The [before image](./queue-ui/before.png) shows the Queue header without the design chevron and with a taller row than the Plan header.
The measured header height is 37.55 px.
The header also lacks the explicit visible focus treatment used by Plan.
Reuse the Plan header classes, native details disclosure, semantic tokens, and right-aligned chevron.
Use the design minimum row height and add visible keyboard focus to Send now.
Keep existing API pagination, durable ordering, action idempotency, and member-specific disclosure storage.

## Browser evidence

The active composer exposes `Queue a message for Claude…` and `Queue message`.
Enter submits `Keep the queue order after reload.` through the real member API.
The panel reports `Message queued in this Run.` and appends the message at visible position 3.
PostgreSQL stores it at sequence 4 with state `queued`; the earlier cancelled message keeps sequence 1 in history.
No Harness acceptance is claimed.

Enter collapses the Queue and Space expands it.
Keyboard activation shows a solid focus outline on the disclosure.
The saved disclosure value is `false` after collapse.
Closing and reopening the panel keeps the Queue collapsed with three durable messages.
A full page reload and another panel open keep the same state.

Keyboard activation of `Remove queued message 3` removes the new message from the pending list.
Keyboard activation of `Send message 2 now` changes its row to `Send now pending`.
It does not change the row to accepted.
The accessible tree names the pending message list, numbered actions, count, and pending statuses.

The [375 px image](./queue-ui/queue-375.png) shows the count, chevron, numbered rows, composer, Send, and Stop within the viewport.
The page and panel both measure 375 px with no horizontal overflow.
The repaired header measures 33.55 px, above the design minimum of 30 px.
The images were inspected.

An isolated database state change from in-progress to awaiting reaches the same open panel through polling.
The input changes to `Reply to Claude…` and the send action changes to `Send reply`.
A separate fixture change to a dispatching message shows `Sending · not yet accepted` and disables its removal.
The [dispatching image](./queue-ui/dispatching-375.png) preserves the layout at 375 px.
These two state changes test rendering and polling; they are not evidence of native delivery.

## Checks

- All 16 Worker lease, ordered message, pending queue pagination, acceptance fencing, and Run control API contract tests pass in 5.42 seconds.
- All four Worker control checks pass in 0.98 seconds, including output-before-acceptance and recovered accepted-message handling.
- All nine existing web Run and pull request checks pass.
- Web type checking passes.
- Focused Queue lint and formatting pass after formatting the changed component.

## Remaining acceptance work

Keep Story 2.14 in progress.
This is the verdict of this first browser check; the later [native HTTP acceptance](./2026-09-29-queue-http-acceptance.md) completes Story 2.14.
The browser submission, composer mode, disclosure persistence, and keyboard checks now have direct evidence.
A complete native polling Worker check must still prove multiple queued messages drain in Plane order and accepted messages are not delivered twice across restart.
The current Worker control check uses a controlled subprocess and client; it does not replace that native HTTP check.
Story 2.15 still needs steering and fallback evidence for each Harness.
Story 2.16 still needs the removal race against real delivery.

## Review

**Summary:** The Queue matches the approved disclosure structure and supports durable keyboard actions through the real API.
**Critical issues:** None found in the changed display and focus behavior.
**Major issues:** Complete native queue delivery and restart evidence remain required.
**Minor issues:** Browser Run execution states are controlled fixtures.
**Positive feedback:** The repair uses existing Plan styles and native disclosure behavior without a new abstraction.
**Questions:** AD-7 and DNS decisions remain pending and are not assumed.
**Verdict:** Retain Story 2.14 in progress and continue native queue acceptance.

## Cleanup

Close the owned browser and stop both owned web and API processes.
Remove the isolated Compose containers and network.
Ports 3000 and 8000 have no remaining listener.
No test credentials or sessions are stored in the report or checkout.
