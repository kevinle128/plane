---
phase: 1
title: "GitHub connection and project repository"
status: in-progress
priority: P1
dependencies: []
---

# Phase 1: GitHub connection and project repository

## Overview

Deliver Epic 1 stories 1.1–1.8 as a usable Plane-owned GitHub setup flow.

## Requirements

- Implement device authentication, organization installation, removal, and workspace disconnect.
- Bind one authorized repository when a project is created.
- Persist draft PR, conclusion mirroring, and both Run-unique branch formats.
- Follow every Epic 1 acceptance criterion and the handoff settings and project screens.

## Architecture and affected files

- Inspect `apps/api/plane/db/models/integration/github.py`, project serializers, and project creation API before extending contracts.
- Inspect the web integrations page and `apps/web/core/components/project/create-project-modal.tsx` before editing.
- Give Plane API ownership of Agent GitHub identity and project binding; existing CE repository sync does not create Agent PRs.
- Keep credentials out of prompts, browser storage, and Worker logs.

## Implementation Steps

1. Capture baseline API and browser behavior and define the persistent connection, installation, settings, and binding contract.
2. Back up the test database before schema changes and add migrations, endpoints, and focused API tests.
3. Implement the settings and project picker with Plane UI and accessible error states.
4. Verify device flow, organization access, disconnect, defaults, and branch-format persistence end to end.
5. Replace the GitHub page scan with an indexed repository catalog before claiming support for large installations.
6. Verify catalog refresh, grant removal, stale selections, and search load under realistic repository counts.

## Success Criteria

- [ ] Stories 1.1–1.8 pass their listed Given/When/Then cases.
- [ ] Existing GitHub sync and project creation tests still pass.
- [ ] Settings and picker match the handoff at supported viewport widths.

## Risk and rollback

Keep new Agent GitHub records separate from CE sync records until ownership and permissions are proven.
If GitHub authorization fails, retain prior workspace state and show a recoverable error.
Reverse migrations only after a database backup and an explicit data-retention decision.
