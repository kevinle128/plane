---
phase: 3
title: "Local Worker and four Harness drivers"
status: in-progress
priority: P1
dependencies: [2]
---

# Phase 3: Local Worker and four Harness drivers

## Overview

Deliver local Q&A execution for Claude Code, Codex CLI, Grok CLI, and Omp.

## Requirements

- Mark a Harness Connected only after authentication, model, follow-up, progress, interruption, permission, and recovery probes pass.
- Give each mention a fresh clone outside the Plane checkout and a read-only OS boundary.
- Deliver ordered queued messages and immediate steering through a verified native path or cancel-then-next-turn.
- Preserve the Plane Run ID and transcript across CLI process changes.
- Keep driver behavior behind a versioned capability contract and bound Worker concurrency and memory use.

## Architecture and affected files

- Add one Worker process with one driver per Harness and shared Plane API and event contracts.
- Reuse repository and Run contracts from phases 1 and 2.
- Keep credentials on the Mini and report safe errors to Plane.

## Implementation Steps

1. Probe installed CLI versions and current official protocol documentation for each Harness.
2. Implement claim, lease renewal, clone, preflight, event mapping, ordered delivery, stop, and recovery.
3. Implement four drivers and persist verified capabilities and model reports.
4. Exercise each driver against a real CLI, including denied writes, interrupted turns, and process restart.

## Success Criteria

- [ ] Epic 2 stories 2.1–2.26 pass where applicable to each Harness.
- [ ] Q&A cannot write in or outside its Run clone.
- [ ] A failed probe leaves the Harness in Connection failed with the missing behavior named.

## Risk and rollback

Gate Connected state on observed conformance, not a static feature flag.
On lease loss, reconcile or stop the old process before another owner runs a turn.

## Current execution decision

Real native startup checks found runtime write requirements in Codex, Grok, and Omp.
The [runtime isolation proposal](./reports/2026-09-28-harness-runtime-decision.md) needs a user decision because an exception changes AD-7.
No exception is enabled while that decision is pending.
Other implementation work can continue.
