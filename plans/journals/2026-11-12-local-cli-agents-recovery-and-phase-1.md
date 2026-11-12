---
title: "Local CLI agents: recovery and phase 1"
date: 2026-11-12
---

# Local CLI agents: recovery and phase 1

## What happened

The first implementation (Codex, 2026-09-27..29, 23/43 stories) was never committed and its worktree was deleted, so the code was lost. The spec, PRD, architecture, epics, plan and the full Claude Design handoff were recovered from the Codex SQLite history and the deleted worktree's leftover git index. The work restarted on the fork kevinle128/plane from current preview, with self-hosted GitLab added to scope.

## Phase 1 result

13 stories (GitHub 1.1-1.8, GitLab G1-G5), test-first, one commit per story, pushed after each commit. Reviews: backend + frontend (0 Critical, 6 Important), PR-level (1 Critical), two re-reviews. CI 14/14 green. PR #3 (code) and PR #4 (docs) are open and not merged.

## Lessons

- Commit and push after every story. Uncommitted agent work in a worktree is one deletion away from loss.
- A "30 s budget" checked between reads is not a deadline: chunked size lines, trailers, headers and TCP connect all wait inside library calls. An absolute deadline must shut down the socket and cut the connect wait per address. Prove it with a real socket server and a mutation run.
- Long background runs on macOS need `caffeinate -s` on AC power; `-i` does not stop maintenance sleep.
- The fork's CI runs no API or Vitest suites; local container results must be labelled as local in PR bodies.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
