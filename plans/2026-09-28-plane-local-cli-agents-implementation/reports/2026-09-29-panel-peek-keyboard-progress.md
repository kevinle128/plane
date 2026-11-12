# Run panel and peek keyboard progress

## Reproduction and cause

The signed-in project list opens the real AGENT-1 work item in peek mode.
The Run panel is rendered through a portal outside that peek.
Clicking its composer triggered the peek's outside-click detector and removed both surfaces.
The browser regression failed on that exact lost panel.
After the click repair, Escape still closed both the Run panel and the owning peek.
The panel's document-level key listener and the peek key listener both consumed the same key.

The Stop confirmation exposed two more failures.
Pointer Cancel and Escape each removed the owning peek rather than only dismissing the modal.
The shared modal lacked the existing outside-click prevention marker, and the peek did not exclude key events from modal targets.

## Repair

The Run panel uses the existing outside-click prevention marker.
Its focused Escape handler stops propagation and closes only that panel.
The shared ModalCore applies the same marker to its Dialog root, including its backdrop.
The owning peek ignores already handled Escape events and events whose target belongs to a modal.
The outside-click hook's existing same-container check still controls normal peek dismissal.
No global keyboard manager or new dependency was added.

## Browser and quality evidence

The [browser check](../../../apps/web/tests/agent-panel-keyboard.e2e.mjs) uses the production web and API with the isolated archive fixture.
It submits no Stop command and starts no Worker.
It verifies keyboard opening, initial Close focus, pointer composer access, full multiline input, one-layer Escape, and focus return to the exact Open run button.
It verifies pointer Cancel and Escape in Stop confirmation while retaining the Run panel and peek.
The next Escape closes the panel; the following Escape closes peek and returns focus to the work-item list link.
Full-page opening and closing preserve the work-item page and restore the same trigger focus.
The [375 px capture](./panel-keyboard-ui/peek-375.png) was inspected and the document has no horizontal overflow.
Its history is the declared archive fixture, not proof of native execution or complete scene fidelity.

The project-list console also exposed a nested Button inside MobileLayoutSelection.
The DOM check failed with two nested native buttons from its two responsive instances.
The component now puts its glyphs inside the existing CustomMenu button and reuses the existing secondary Button styling.
The button has a descriptive accessible label and a focus outline.
The browser verifies no nested buttons, keyboard Board and List selection, menu closure, and focus return.
Actual API logs show the preferences PATCH and Board issue read returning 200.

The UI package build and type check, web type check, targeted OxLint, formatting, and thirteen Run helper tests pass.
Read-only review found no concrete defect in panel, peek, shared modal ownership handling, or the repaired mobile layout control.
The last lint check also repaired the layout item index key with its stable layout key.
The final browser and type checks pass.

## Remaining work

The later [fetch cancellation report](./2026-09-29-issue-fetch-cancellation-progress.md) resolves the rejection described below with debugger evidence and a passing browser regression.
The following observations record the state before that repair.

The project list still produces an unhandled Promise rejection whose reason is undefined.
An observational window listener confirmed that rejection during actual navigation from the work-item page to the project list.
It provides no error stack; its root cause still needs diagnosis.
The isolated archive also has no intake state, and the API reports 404 for that separate read.
This report does not infer that the 404 caused the rejection or claim a clean console.
Existing Vite configuration warnings remain visible.
Story 2.8 remains in progress for the remaining scenes, complete accessibility, default-open focus, dropdown coverage, and the unresolved rejection.

## Active test environment

This environment remains in use for the next project-list rejection diagnosis while the full goal is active.
Reuse it after checking its handles and ports; do not start duplicate servers.
All commands run from `/Users/dale/orca/workspaces/plane/main`.

| Resource | Command or owner | PID or handle | Port |
| --- | --- | --- | --- |
| Web | `VITE_API_BASE_URL=http://localhost:8009 pnpm --filter=web dev` | Harness 23721; pnpm 26281/26283; router 26328; listener 26339 | 3000 |
| API | `docker compose -p plane-timeline-ui -f docker-compose-test.yml -f /tmp/plane-send-now-ui.yml run --rm --service-ports api-tests python manage.py runserver 0.0.0.0:8009 --noreload` | Harness 75542; container `plane-timeline-ui-api-tests-run-9299a0330250` | 8009 |
| Dependencies | Compose project `plane-timeline-ui` | Owned `test-db`, `test-redis`, `test-mq`, `test-minio` containers | Internal |
| Browser | Agent Browser session `plane-panel-keyboard` | Owned Chromium session | None exposed for product use |

The final API and web HTTP checks return 200 and the API container is running.
The web log is `/tmp/plane-panel-keyboard-web.log`; the API log is `/tmp/plane-panel-keyboard-api.log`.
Stop these owned resources when the diagnosis task, goal, or session ends.
