# Agent name and handle acceptance

## Scope and environment

Check Stories 2.2 and 2.3 with the production web app, Chromium, and actual Django API on an isolated restored fixture database.
The fixture Agent is disconnected.
Its mention suggestion remains disabled with the Not connected reason.
No Harness connection or model verification is claimed from this fixture.
The API mention check uses an explicitly connected isolated test Agent to check saved comment and Run identity.

## Browser evidence and card repair

Save the Claude Agent name as Release Guide and its handle as ReleaseGuide through the production settings page.
Reload the page and verify both saved values.
An empty name receives a useful inline validation error.
Reload again and verify that the previous saved name remains.
Trying the existing Codex handle receives an inline collision error.
Reload again and verify that ReleaseGuide remains saved.
An actual database read also confirms that Claude retains ReleaseGuide and Codex retains Codex.

The first Integrations check shows the provider title Claude Code after the name was changed.
This reproduces the rename display defect in the actual product.
Change the card title to use the saved Agent name.
Keep the Harness provider title in the accessible label, alongside the saved name and connection state.
After a full reload, the actual card shows Release Guide and its label includes Release Guide (Claude Code).
An initial test selector missed the router's trailing slash; the corrected check uses the actual rendered link target.
The [375 px card image](./identity-ui/renamed-card-375.png) was inspected.
Page width equals the 375 px viewport width.

Type @ReleaseGuide in the work-item comment editor.
The actual mention picker shows Release Guide, @ReleaseGuide, and Not connected.
It correctly remains disabled for this disconnected fixture.
Open the original Run using its existing stable panel ID.
The panel still shows its six historical activities and queued messages after the name and handle change.

## API identity and history evidence

The extended production mention check saves the original @Claude comment and Run.
It changes the name and handle through the administrator settings endpoint and reads them back.
Saving a new @ReleaseGuide mention creates another Run for exactly the same Agent ID.
The new trigger context contains the new handle text.
The original Run ID, original comment HTML, Run context, and complete event rows remain unchanged.
The existing settings check rejects a case-insensitive handle collision and verifies that the other Agent's handle remains unchanged.

All 18 Run creation and Harness settings API checks pass in 5.82 seconds.
Web type checking, focused OxLint and Oxfmt checks pass.
All nine existing Run UI and pull-request checks pass.

## Sidebar repair found during the browser check

The work-item page exposes an invalid nested button in the extended sidebar drag handle.
Use the existing single DragHandle pattern from project list items, with its original drag ref and placement classes.
Give that native button its existing translated drag label.
Move the favorite folder drag handle beside its disclosure button and remove its extra button wrapper.
This applies the same native control rule to the other nested drag-handle caller.
Two shadowed variable warnings in the touched folder file are also repaired without changing the drag payload.
After a fresh work-item page load, all six labeled drag buttons have no button ancestor.
The remaining cases are menu and combobox controls outside the drag handles and still need separate repair and checks.
No complete favorite-folder reorder acceptance is claimed.

## Story completion audit

| Story criterion | Direct evidence |
| --- | --- |
| 2.2: New name remains in Integrations and future suggestions | Actual settings Save and refresh, repaired card text and accessible label, and the actual work-item mention picker |
| 2.2: Invalid name has an error and preserves the saved name | Actual empty-name inline error and full reload of the prior saved value |
| 2.2: Existing Run identity and history survive rename | Original stable panel reopening plus API old Run, comment, context, and event equality |
| 2.3: New unused handle reaches suggestions and saved comments | Actual settings and mention picker plus a production new-mention API request that retains the Agent ID |
| 2.3: Collision is rejected and both handles remain | Actual Codex collision inline error and refresh, with case-insensitive API collision and unchanged other-Agent assertions |
| 2.3: Old handle Run retains Agent identity and conversation | Original stable panel activities and unchanged API Run identity, context, comment HTML, and event rows |

## Review

**Summary:** The actual settings, Integrations card, mention picker, stable Run panel, and API history checks cover all six criteria.
**Critical issues:** None found for the name and handle paths.
**Major issues:** Other menu and combobox nested-button cases still need repair and complete UI checks within the active goal.
**Minor issues:** The disconnected browser fixture does not prove Harness connection, and folder reordering is not claimed.
**Positive feedback:** Saved names are displayed without changing stable Agent references or rewriting historical data.
**Questions:** None required for these two stories.
**Verdict:** Mark Stories 2.2 and 2.3 done and keep the complete goal active.

The separate code review found no concrete defect or missing acceptance evidence in these two stories.
It confirmed that the reviewed sidebar changes preserve drag refs and remove the nested drag buttons.

## Cleanup

The owned browser, web process, and API process are stopped.
The isolated Compose stack and temporary override are removed.
No listener remains on the owned test ports 3000 and 8009.
No credential or member session is stored in this report or the checkout.
