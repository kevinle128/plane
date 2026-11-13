# Tool result browser acceptance

## Scope

This check covers the tool-result portion of Story 2.8.
The [native HTTP report](./2026-09-29-native-tool-results-progress.md) separately proves actual polling Worker and CLI delivery.
This browser check uses the production web and API with declared history in an isolated database.
It does not substitute fixture events for native delivery proof.
Story 2.8 remains in progress for its remaining scenes and accessibility criteria.

## Browser evidence

The [browser check](../../../apps/web/tests/agent-tool-results.e2e.mjs) uses a signed-in member and the existing isolated AGENT-1 Run.
It creates 100 fixture events with a long native-format result whose first part lies outside the latest 50-event page.
The source contains 17,001 Unicode characters and a JavaScript literal `\u0000` escape.
The result is split into 8,000-character parts, with a queued member message between parts.

The complete check passes with Light and Dark selected through the actual Preferences menu and saved profile API.
It verifies:

- The latest page labels incomplete result details.
- Loading earlier activity reconstructs the exact source, including Unicode, newline, and escape characters.
- Every continuation row is absent from the rendered logical timeline, with one result row and the full native record retained.
- The interleaved queued message remains visible and no empty Working group appears.
- Each Working group has one action; result parts do not increase the action count.
- The failed result has its actual error text, an explicit Action failed label, and a danger icon that matches the error text token.
- Enter opens Full result record, Tab reaches its named scroll region, and PageDown scrolls the full source.
- Completion retains the exact result.
- The 375 px page has no horizontal overflow.
- Closing, reopening, and full reload return the same Run; its partial page remains honest until earlier activity is loaded.

The DOM content and parsed full record are compared exactly in Node.
Embedding the large escape-containing expected string in a browser `eval` expression gave a false comparison despite exact retrieved content.
The check now waits for complete detail and then compares the actual DOM text outside that transport.

## Reproduced presentation defect

The failed result initially used a neutral TriangleAlert icon while its error text used the danger token.
The actual Dark browser check failed on that computed-style mismatch.
The shared timeline row now labels native error results Action failed and applies the existing danger token to their icon.
This does not change the overall Run status: a completed Run can include a failed tool call.
The narrow error screenshot records the [before](./tool-results-ui/narrow-error-dark-before.png) and [after](./tool-results-ui/narrow-error-dark.png) states.

## Visual and quality checks

The [Light](./tool-results-ui/narrow-light.png) and [Dark](./tool-results-ui/narrow-dark.png) captures were inspected at 375 px.
The result label, fixed header and composer, semantic borders, readable content, and keyboard focus outline remain visible.
Web type checks, targeted OxLint, formatting, and read-only review pass.
The browser reported no uncaught page errors during the result checks.
This is not a claim that every earlier console warning or every design scene is resolved.

The owned browser session `plane-tool-results`, web server on port 3000, and isolated `plane-timeline-ui` API stack on port 8009 were stopped after verification.
The test stack volumes were removed and neither port retained a listener.

## Remaining work

Complete the full panel accessibility and scene audit, including non-file Markdown results, elicitation, error recovery hints, requester identity, motion, and other applicable handoff details.
Keep the other story-specific acceptance gaps in the [43-story audit](./2026-09-28-story-acceptance-audit.md).
