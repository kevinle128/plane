# Work-item fetch cancellation progress

## Reproduction and cause

The production browser check reproduced three unhandled rejections with an undefined reason during project layout changes.
The earlier async stack pointed to the preferences fetch that caused the layout to render.
Both preferences requests returned 200.
Debugger exception tracing then identified the actual rejection as a canceled issues request.
ProjectIssues.clear aborts the previous request when a new fetch starts.
The service removes the Axios cancellation object when it throws response data that does not exist.
The store then clears the newest request's loader and throws that undefined value.
The separate fixture intake-state 404 is not the cause of this rejection.

## Repair and checks

The project, project-view, cycle, module, archive, workspace, and profile stores each retain the AbortSignal used by their first-page request.
An aborted request returns without changing the current loader or processing an old response.
The cancellation guard ends before synchronous response processing, because that processing can clear the controller itself.
Current service errors and response-processing errors still propagate.
No service response contract, dependency, or shared state abstraction changed.

The [production-method checks](../../../apps/web/tests/issue-fetch-cancellation.test.mjs) compile each actual fetch method with the existing TypeScript compiler.
Controlled service responses check canceled rejection, late success, newest data, retained loading, current failure, and failure after controller cleanup.
All seven checks pass.
The controller-cleanup case failed in all seven methods before the final repair.
These controlled responses are unit evidence, not native Worker evidence.

The [browser check](../../../apps/web/tests/agent-panel-keyboard.e2e.mjs) now requires zero page errors after reload, Board/List selection, peek, Stop cancellation, and full-page panel navigation.
The original run failed with three undefined errors.
The repaired run passes using the production web and API with the isolated archive fixture.
It sends no Stop command and starts no Worker.
Targeted lint has zero warnings or errors, and formatting passes.
The final web type check passes.
The thirteen Run helper checks also pass.
Read-only review found no remaining concrete defect in the cancellation repair.
Existing Vite configuration warnings remain separate from the repaired browser rejection.

## Scope and test resources

Story 2.8 remains in progress for complete design scenes, accessibility, elicitation, and dropdown-flow coverage.
No story or epic status changed from this repair.
The [active test environment](./2026-09-29-panel-peek-keyboard-progress.md#active-test-environment) remains in use for those checks.
The owned browser now exposes diagnostic CDP port 9226 on localhost, with Chromium PID 25753 and daemon PID 25683.
Temporary diagnostic clients have a sixty-second limit and have finished.
Reuse the existing web, API, and browser after checking their live handles.
