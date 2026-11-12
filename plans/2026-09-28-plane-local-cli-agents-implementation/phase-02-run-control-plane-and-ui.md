---
phase: 2
title: "Durable Run control plane and work-item UI"
status: in-progress
priority: P1
dependencies: [1]
---

# Phase 2: Durable Run control plane and work-item UI

## Overview

Build the Plane-owned Run, context, event, queue, permission, and UI contracts used by Epics 2 and 3.

## Requirements

- Create one Run with each saved Agent mention and retain its trigger comment, requester, issue, project, and repository identity.
- Persist authorized context, ordered events, leases, commands, queue states, and permission decisions.
- Enforce authorization, idempotency, lease fencing, and trust boundaries.
- Index tenant and Run cursor reads and use paginated event access so history remains usable as Run counts grow.
- Implement the mention picker, activity card, resizable panel, timeline, plan, queue, composer, and recovery states.

## Architecture and affected files

- Inspect `apps/api/plane/app/views/issue/comment.py`, issue activity models, permissions, and serializers before changing comment writes.
- Inspect `apps/web/core/components/comments/`, editor mention hooks, issue activity components, and MobX store patterns.
- Plane API and PostgreSQL remain the only Run state writers; Worker observations use authenticated commands.

## Implementation Steps

1. Reproduce the current mention and comment path in a browser and API test.
2. Back up the test database, then add the Run schema, atomic mention trigger, context snapshot, lease, command, event, and grant APIs.
3. Add browser services and stores, then the activity card and panel.
4. Verify authorization, queue order, stop/resume, stale recovery, event cursor, and keyboard paths.

## Success Criteria

- [ ] Epic 2 shared Run and UI criteria pass with real API persistence.
- [ ] Refresh and Worker restart retain complete history without duplicate events or comments.
- [ ] Concurrent claims, long timelines, and queue operations remain correct under load.
- [ ] Visual comparison covers each applicable design scene.

## Risk and rollback

Keep comment and Run creation in one transaction to prevent orphaned Runs.
Reject stale lease generations rather than reconciling state in the browser.
Retain comments and Run records when a Worker fails.
