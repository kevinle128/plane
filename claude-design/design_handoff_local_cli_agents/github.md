repo: kevinle128/plane
branch: main

## Last sync

date: 2026-09-22T04:08:28Z

### Updated in this project

- Read the `spec-plane-local-cli-agents` BMAD spec (SPEC.md + 6 companions) as the feature contract.
- Recreated the Plane work item detail screen (shell, header, activity feed, properties sidebar) from source.
- Added mockups for the @Claude / @Codex Agent Run card, session panel, elicitation, code job, failure states and repo-map settings.
- Styling uses the bound PlanePropel design system (`@plane/propel`) loaded from `_ds/`.
- Added the Agents settings screen (list, Model / Permissions / Repositories / Runner tabs, Add agent dialog), placed under workspace settings → Features per `packages/constants/src/settings/workspace.ts`.
- Added a Git repository step to project creation: GitHub device-flow connect, repo + branch picker, or a pasted SSH remote, with the clone path on the Mini.
- Swapped hand-drawn glyphs for real @plane/propel icons (sidebar nav, activity rails, properties, bots).
- Settings shell rebuilt from settings/workspace/sidebar/* and settings/content-wrapper.tsx; GitHub supports several installations (personal + organisations).
- Added a workspace Integrations page (Linear-style card grid) with GitHub device-flow connect; each agent harness is a card there that opens its own config (name, instructions, harness, model).
- Comment composer toolbar rebuilt from packages/editor TOOLBAR_ITEMS.lite and lite-text/toolbar.tsx.
- Added HITL permission requests, task list with progress, queued messages, and Stop-to-steer.

## Screen map

| Project screen | Repo files |
|---|---|
| Agent Runs.dc.html — app shell / sidebar | apps/web/core/components/workspace/sidebar/sidebar-item.tsx, quick-actions.tsx, projects-list-item.tsx, helper.tsx |
| Agent Runs.dc.html — header / breadcrumbs | apps/web/core/components/core/app-header.tsx, apps/web/core/components/common/breadcrumb-link.tsx |
| Agent Runs.dc.html — comment composer toolbar | apps/web/core/components/editor/lite-text/toolbar.tsx, packages/editor/src/constants/common.ts |
| Agent Runs.dc.html — widget buttons, activity sort/filter, subscribe | apps/web/core/components/issues/issue-detail-widgets/action-buttons.tsx, widget-button.tsx, issue-activity/sort-root.tsx, issue-activity/activity-filter.tsx, issue-detail/subscription.tsx |
| Agent Runs.dc.html — work item body | apps/web/core/components/issues/issue-detail/main-content.tsx, root.tsx, identifier-text.tsx |
| Agent Runs.dc.html — properties sidebar | apps/web/core/components/issues/issue-detail/sidebar.tsx |
| Agent Runs.dc.html — activity feed / comments | issue-activity/root.tsx, activity-comment-root.tsx, activity/actions/helpers/activity-block.tsx, comments/comment-block.tsx, comments/card/display.tsx |
| Agent Runs.dc.html — mention picker | packages/editor/src/extensions/mentions/mentions-list-dropdown.tsx, apps/web/core/hooks/editor/use-editor-mention.tsx, apps/web/core/components/editor/embeds/mentions/user.tsx |
| Agent Runs.dc.html — Agent Run card, panel, states | _bmad-output/specs/spec-plane-local-cli-agents/{SPEC,agent-run-ui,job-kinds,runner,failure-modes}.md |
| Agent Runs.dc.html — New project modal | apps/web/core/components/project/create-project-modal.tsx, projects/create/root.tsx, projects/create/attributes.tsx, project/create/common-attributes.tsx, project/create/header.tsx, project/create/project-create-buttons.tsx |
| Agent Runs.dc.html — settings shell | apps/web/core/components/settings/workspace/sidebar/{root,header,item-categories,item-icon}.tsx, settings/sidebar/item.tsx, settings/{content-wrapper,heading,page-header}.tsx, packages/constants/src/settings/workspace.ts |
| Agent Runs.dc.html — repo map settings | _bmad-output/specs/spec-plane-local-cli-agents/{runner,job-kinds}.md |
