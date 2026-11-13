# Question history display progress

## Scope and repair

Story 2.8 requires expanded elicitation history in the Run timeline.
The existing question event used the ordinary message layout.
The production browser regression failed because the design's warning card was absent.
Question events now use the approved warning surface, subtle border, rounded corners, and card spacing.
The existing question icon and timestamp remain visible outside the content card.
The card has an accessible region name and uses the existing safe Markdown renderer.
It does not label an old question as still awaiting an answer.

## Browser evidence

The [browser check](../../../apps/web/tests/agent-question-history.e2e.mjs) inserts one declared historical question into the isolated archive fixture.
It uses a stable source key and does not replace the Run's other history or change its status.
The production web and API then read that event.
The repaired check passes with expanded Markdown, retained Unicode, no script execution or JavaScript link destination, and one matching event after reload.
At 375 pixels, the document has no horizontal overflow.
The [narrow capture](./question-history-ui/question-375.png) was inspected.
The script-like text in that capture is deliberate hostile test input, rendered as text.
Its old start time, missing clone path, and pending queue are archive fixture data.
This capture is not proof of native execution, a current waiting question, or complete scene fidelity.
The browser reports zero page errors for this flow.
Targeted lint and formatting pass.
Web type generation and TypeScript pass.
Read-only review found no concrete defect in the card or the history check.

## Remaining work

Repository elicitation already uses the separate authorized repository chooser and its verified selection flow.
This change does not add unbound option buttons to historical questions.
Native question publication, durable answer routing, four-Harness question mapping, and complete elicitation scene acceptance still need evidence and implementation where absent.
Story 2.8 remains in progress, and the full goal remains active.
The [existing test environment](./2026-09-29-panel-peek-keyboard-progress.md#active-test-environment) remains in use for those checks.
