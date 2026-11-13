# Breadcrumb and reaction progress

## Scope and reproduction

This is partial acceptance work for Story 2.8.
The fresh isolated AGENT-1 page has two remaining nested native buttons.
The breadcrumb title navigation button is inside the project selection trigger.
The emoji picker trigger wraps the entire group of native reaction buttons.
The same grouped-label pattern also exists in comment controls and two Space callers.
The test uses the actual Plane API, archived database fixture, and normal email/password sign-in.

## Repair

The breadcrumb title and project selector are sibling controls.
The title retains its navigation callback and has an accessible name.
The selector has its own name, native tab stop, and separate options.
A last breadcrumb keeps its title inside the selector as display content.
The disabled navigation contract is retained.

CustomSearchSelect now reuses the existing ComboDropDown contract.
Headless UI owns open state, and a layout mirror controls conditional popup content.
The old render-time open callback and separate local toggle are removed.
Callbacks run on transitions through effect events.
The registered trigger closes single selections, and defaultOpen uses the shared native activation behavior.
No additional dropdown state abstraction is added.

EmojiReactionPicker accepts an optional native render element through the existing Popover contract.
All six web and Space production callers now keep reaction groups outside the picker trigger.
Only the add-reaction control opens the picker.
Native reaction buttons expose pressed state and toggle their own reaction.
Empty reaction groups do not consume layout space.
Disabled controls, signed-out routing, and iframe add-button restrictions remain in their owning callers.
The selected native-button stories use the same render contract.
The reviewer verifies that the installed Base UI render merge preserves the element content when label is null.
Reaction lists use stable emoji keys, and the repeated-selection story uses native UUIDs for distinct selection records.
The issue reaction arrays are computed during observer render so user and reaction dependencies remain observable.

## Verification

Run `node apps/web/tests/agent-menu-controls.e2e.mjs <signed-in-isolated-session>`.
The final full run passes native action menu keys, real relation and link dialogs, activity filtering, breadcrumb Enter/Space/ArrowDown, Escape focus, and actual project navigation.
The real work-item page has zero nested native buttons before and after adding a reaction.
Native emoji selection creates a real API reaction.
The pressed reaction survives full browser reload.
Enter on the reaction removes it without opening the picker, and another reload confirms removal.
The test restores the isolated fixture's reaction state.
The 375 px overlay geometry and focus checks and all three Strict Mode submenu keys pass again.

The reaction check initially fails because its generic dialog selector includes the retained success notification.
The picker is already collapsed and the actual reaction has pressed state during that failure.
The check now requires removal of the specific Popover dialog, collapsed trigger ARIA, and persisted reaction state together.
It does not extend the timeout or replace the API response.

The public component fixture initially falls through to the workspace route because its filename starts with a dot.
The actual API request for that filename as a workspace proves the wrong page loaded.
The public filename now has no leading dot, and a bounded native HTTP check verifies the exact fixture HTML before browser navigation.
Cleanup restores the desktop viewport and removes fixture files even on failure.
The separate page-controls check now sets its required desktop viewport explicitly.
This avoids counting both responsive property controls after a preceding narrow check.

The page-controls regression run passes state keyboard and ARIA checks, query Escape, close Escape, Tab, priority persistence, calendars, and default-open date filters.
UI and Propel builds pass.
UI, Propel, web, and Space type checks pass.
Scoped lint and formatting pass with zero warnings and errors across 14 files.
Nine Run UI and pull-request tests pass, with the separate opt-in live polling test skipped and excluded from the pass count.
The read-only review finds no concrete regression, including the Space caller adaptation.
The final complete browser rerun finishes after review.

The [375 px screenshot](./menu-controls-ui/separate-reaction-375.png) shows the separate reaction control and retained page width.
The long title still clips to one line at this width and needs its own acceptance repair.

## Remaining acceptance

No story is marked done by this report.
Nine of 43 stories remain complete.
All applicable design scenes, full panel accessibility, all 11 property dropdown flows, default-open focus after replacing another popup, and long transcripts remain unproved.
The undefined browser error and the narrow title clipping also remain open.
The actual browser proof covers the web work item.
Space has source review and type evidence but no live reaction-flow claim in this report.

## Cleanup

The owned reactions-ui browser and web listener are stopped.
The owned one-off API container and plane-controls-ui Compose services and network are removed.
No owned listener remains on ports 3000 or 8009.
The temporary override and screenshot are removed after retaining the screenshot with this report.
The archived fixture dump remains available.
