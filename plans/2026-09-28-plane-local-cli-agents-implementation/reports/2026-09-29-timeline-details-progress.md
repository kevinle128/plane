# Timeline action detail progress

## Scope and reproduced defect

This work covers long action input, Markdown result presentation, requester identity, and motion within Story 2.8.
The production web and isolated API showed four steps for two calls because one input was stored in three parts.
The browser check failed on that exact count before the repair.
The Worker now adds a zero-based part index to long native tool input.
The shared timeline groups input by event kind, turn, and native call identity in one pass.
It keeps one invocation and its full parameters, with honest incomplete detail when a cursor or stream omits parts.
Results cannot mix with the input of the same call.

## Presentation

The collapsed action shows its target path or command.
Expanded input retains all parameters and has a named keyboard-accessible scroll region.
Text results use the existing safe Markdown renderer.
Structured records, decoded file contents, native errors, mixed non-text content, and incomplete results retain code formatting.
Full result record keeps the complete native audit JSON.
The initial request uses the actual requester name and the existing avatar component.
Live card, panel, and tail animation respect reduced motion.
The active tail includes the design's lightning glyph.

## Direct evidence

The [browser check](../../../apps/web/tests/agent-timeline-details.e2e.mjs) runs against the production web and API with declared audit events in a disposable database.
It does not claim native execution of these fixture actions.
The [earlier native delivery report](./2026-09-29-native-tool-results-progress.md) separately records native CLI and actual polling Worker delivery.

The browser check passes for two steps, one 17,001-character Unicode input, exact parsed parameters, target path, Markdown heading and emphasis, no executed raw script or JavaScript link, actual requester identity, reduced-motion CSS, the active tail glyph, and keyboard access to Action details.
Completion retains the input.
Closing, reloading, reopening, and loading earlier activity reconstruct the same input and Markdown result.
The [375 px capture](./timeline-details-ui/narrow.png) was inspected and has no horizontal document overflow.
The inserted unsafe HTML is displayed as text and does not run.
The browser reported no uncaught page errors during this check.

Thirteen helper tests and seven Claude driver tests pass.
Targeted OxLint, Ruff, formatting, and the web type check pass.
The type command reports existing Vite configuration warnings; this report does not claim those warnings are resolved.

Read-only review found no concrete defect in this scope.
The owned browser, web server, API server, and isolated dependency containers were stopped after final verification.
Ports 3000 and 8009 have no remaining listener.

## Remaining work

Story 2.8 remains in progress for the remaining design scenes, elicitation and recovery hints, full accessibility, dropdown flows, default-open focus, and the earlier unresolved browser error.
The [43-story audit](./2026-09-28-story-acceptance-audit.md) remains the whole-goal acceptance record.
