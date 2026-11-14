# Code review: Phase 3 (Claude Q&A Runs in Docker Sandboxes)

Reviewer: code-reviewer (fresh context), 2026-11-14 (Asia/Saigon)
Branch: feat/local-cli-agents-phase-3 @ 58d8ab3f7d

## Findings

### F1 (Important) GitLab credential refusal is read as a lost lease; the Run hangs

- `apps/api/plane/agent/services/lease.py:168` and `gitlab_connection.usable_token` -> `git_connection.status_error` / `mark_reconnect_required` raise `ProviderError(..., http_status=409)` (`provider_disconnected`, `provider_reconnect_required`, expired token).
- `apps/agent-worker/plane_agent_worker/plane_client.py:80` maps every 409 on a non-probe path to `Conflict`; `runs.py:272-276` turns it into `LeaseLost`; `execute` then posts nothing.
- Scenario: GitLab connection disconnected / token expired / decrypt fails after the Run was created. Worker gets 409 `provider_reconnect_required`, stops silently. Run stays `in_progress` until the lease ends, then shows Stale forever (no Phase 3 recovery). No failure code, no conclusion comment, no `worker_last_error`.
- Fix: return a non-409 status (e.g. 422/424) for credential refusals from the git-credential endpoint, or make the Worker treat only `lease_superseded`/`run_finished` codes as `LeaseLost` and fail the Run with the provider code otherwise. Add a contract test + a Worker test for this path.
  - Verified (copy at /tmp/aw-exp, `tests/test_review_experiments.py::test_provider_409_on_git_credential_posts_no_result`): `git_credential` -> `Conflict(409, "provider_reconnect_required")` -> `results == []`.

### F2 (Important) A 409 on an event post mid-turn leaves Claude running in the sandbox

- `apps/agent-worker/plane_agent_worker/drivers/claude.py:495-517`: `on_message` (-> `EventSink.add` -> `LeaseLost`) raises inside the read loop; only `ProbeTimeout` kills the session; `finally` only copies `stderr_tail`. No `session.kill()`/`close()`, the registry record stays, the in-VM process keeps running (and spending gateway tokens) until it ends by itself; nothing reads the deadline any more, so the 30 min limit does not apply.
- Verified (copy, `test_conflict_on_turn_event_leaves_claude_running`): after `execute` returns, `.processes/run-<id>-0.json` remains and no in-sandbox `kill` was run; the fake Claude process (PID 79469) was still alive after pytest exited and had to be killed by hand.
- In Phase 3 a 409 on events needs a superseded lease (no stop/recovery yet), so it is latent, but Phase 5 stop/recovery will hit it every time; any other exception from the mapper/sink hits it now.
- Fix: in `run_turn`, `except BaseException: session.kill(); raise` (or kill in `finally` when `outcome.result is None and not outcome.ended`). Test: Conflict from `post_events` during the turn -> pidfile kill call + no registry record.

### F3 (Important) Clones and per-Run scratch are never removed

- `apps/agent-worker/plane_agent_worker/runs.py:170` removes only `layout.host_dir` (`<run_root>/<run_id>`); `sandboxes/<key>/clones/<run_id>/clone` and `sandboxes/<key>/scratch/<run_id>` stay forever.
- Contract `architecture-contracts.md` §12 Cleanup: "a Run's scratch sub-folder and clone are removed with the Run folder". README (`apps/agent-worker/README.md:191-198`) instead says they stay and asks for manual `rm -rf`. The README contradicts §12; disk on the Worker host grows by one checkout per Run without bound (every mention = one full working tree).
- Verified (copy, `test_clone_and_scratch_survive_the_run`): after a completed Run `clone` and `run_scratch` exist, `host_dir` does not.
- Fix: remove `layout.clone.parent` and `layout.run_scratch` in the same `finally` (Phase 4 later turns can re-clone, as 2.7 asks for a fresh clone anyway), or get an explicit user decision to amend §12 and add a bounded cleanup.

### F4 (Important) A second Run of the same repository can stop or delete the sandbox under a live turn

- `apps/agent-worker/plane_agent_worker/sandbox.py:243-258` (`_ensure`: `known != wanted` -> `remove` + create) and `:266-270` (`health`: exit 1 -> `sbx stop`). The per-name lock serializes `ensure` calls only; it does not know that another Run's `sbx exec claude` is live in that VM. `MAX_RUNS = 4` (`loop.py:35`) and one sandbox per (workspace, repo) make overlap normal.
- Triggers: (a) `rules()` re-reads `env.ANTHROPIC_BASE_URL` from host settings on every ensure, and `skill_mounts` re-reads skill links, so any such host edit changes `wanted`; (b) any host tool that rewrites `~/.claude/settings.json` by write+rename makes the single-file mount stale (`reports/sbx-verification.md:39`), and the next Run's health check runs `sbx stop`.
- Scenario: Run A is answering; operator/Claude on the host updates settings; Run B on the same repo is claimed -> `sbx rm --force plane-qa-<key>` (or `sbx stop`) -> A's turn dies, A fails as `harness_exited`.
- Verified (copy, `test_second_run_recreates_sandbox_under_a_live_turn`): while A's process record exists, B issues `['rm', '--force', 'plane-qa-de2d17966f19e61e']`.
- Fix: make the existing per-name lock a shared/exclusive lock: a turn holds it shared for its whole `sbx exec`; `stop`, `rm` and create need it exclusive (a new Run waits, bounded by its deadline). Test with the fake: concurrent A/B with a changed gateway -> no `rm`/`stop` while A is live.

### F5 (Important) A transient error on the success result throws away the answer

- `apps/agent-worker/plane_agent_worker/runs.py:330-337`: `post_result` for a completed turn has no retry; a non-409 `PlaneClientError` (5xx, connection reset, Plane restart) propagates to `execute`'s `except Exception` (`:161-166`), which logs "internal error" and posts `failed` / `worker_error`. `plane_client.py` has no retry.
- Scenario: Plane restarts or a proxy returns 502 while Claude finishes a 10-minute answer -> the answer text is lost, the Run shows "failed: The Worker stopped this Run after an internal error". If both posts fail the Run stays in progress/stale.
- `apply_result` is idempotent for a finished Run (`conclusion.py:46-47`), so retrying is safe.
- Fix: bounded retry (e.g. 3-5 tries with backoff, inside the turn deadline) for `post_result` on `PlaneClientError` that is not a `Conflict`, in both success and failure paths. Test: first `post_result` raises `PlaneClientError(502)`, second succeeds -> one completed result with the answer.

### F6 (Minor) `git_host_blocked` clone report is rejected by Plane

- `apps/api/plane/agent/worker_api/serializers.py` `GIT_ERROR_CODES` lacks `git_host_blocked`, which `git_transport.py:145,254` raises. The clone report gets 400 and is only logged; the Run still fails with the right code (result `failure_code` is free text), but `worker_last_error` is not set. Fix: add the code to the tuple; one contract test.

### F7 (Minor) Created Runs of an Agent disconnected after creation wait forever

- `lease.py:89-97` `claim_run` skips Runs whose Agent is no longer `connected`; nothing fails them. The card shows the Run as queued with no end. Fix later (Phase 5 recovery) or fail `created` Runs on Disconnect; note it in the Phase 5 plan.

### F8 (Minor) Deleting the trigger comment soft-deletes the Run asynchronously while it runs

- `AgentRun.trigger_comment` is CASCADE; `soft_delete_related_objects` soft-deletes the Run, turns and events. The Worker then gets 404 (not 409) on renew/events/result, logs, and keeps the turn until it ends or the 30 min limit. Bounded; no spec rule says delete stops the Run. Note only; no test covers it.

### Test gaps (would hide the bugs above)

- No Worker test for a non-lease 409 from `git-credential` (F1); no API test that asserts the status code the Worker can tell apart from `lease_superseded`.
- No Worker test where `post_events` raises `Conflict` during the turn and asserts the in-sandbox kill (F2).
- No test that the clone/scratch are gone after a Run (F3) - the contract says they are.
- No concurrent-Run test with a changed `wanted` or a stale settings health check while another turn is live (F4).
- No test for a transient `post_result` failure on a completed turn (F5).

## Checks run

- Worker: `uvx --from uv==0.12.21 uv run pytest -m "not native"` -> 257 passed, 4 deselected.
- Blocks: `vitest run` -> agent-run 96/96; full run 481/484 on the first run, the 3 failures were `src/select` timeouts (not in the diff), `src/select` re-run 99/99 and a second full run had no FAIL.
- Editor `tippy.test.ts` 5/5. `pnpm --filter=@plane/i18n sync:check` in sync (4,223 keys).
- API (isolated compose project `plane-p3-review`, then `down -v`): `makemigrations --check --dry-run` -> No changes detected; phase tests (run creation, events, event pages, lease, conclusion, git-credential, context, harness probe, mention parsing, email mention filter) -> 161 passed.
- Experiments on a copy at /tmp/aw-exp (`tests/test_review_experiments.py`): F1, F2, F3, F4 reproduced.

## Checked, no finding

- Run creation: comment + Runs in one `transaction.atomic`; `AgentUnavailable` rolls both back; the existing guest comment rule runs first; Agent lookup is scoped to the issue workspace; repository problems give a failed Run, not a 500.
- Email and in-app notifications parse only `user_mention`.
- Worker auth: every Run endpoint checks lease generation and Worker; result is idempotent under the row lock; claim uses `skip_locked`. One global Worker serving every workspace is accepted by Q17.
- Timeline paging: seq cursor with `limit+1` probe, validated ints, run scoped to slug/project/issue, guest visibility rule; web store stops on `has_more=false` or a cursor that does not move, merges by event ID.
- Conclusion comment: bot user via `impersonate`, HTML-escaped, one per Run; web refetches comments when a `conclusion_comment_id` is unknown.
- Git transport: token only on an inherited pipe; helper answers only `get` for https + exact `netloc` (non-443 port: `test_plane_token_clone_succeeds_with_ca_bundle` clones with the token from a local HTTPS server on a random port; helper matching in `test_git_transport.py:294-310`); `credential.helper=` reset; no redirects; resolve + pin; CA scoped to the clone URL base; token redacted from detail. GitHub (`host`) and GitLab tokens stay on the host; sandbox client env is an allowlist.
- `StreamSession.kill` uses `killpg` with `start_new_session=True` (`process_registry.py:91`) plus the in-sandbox pidfile kill.
- Migration 0132 matches the model (constraints, indexes, FKs); lockfile updated.

## Verdict

Not ready to merge as is: F1-F5 are real defects (a routine GitLab token expiry leaves a Run hanging; answers can be lost on a transient error; concurrent Runs on one repo can kill each other; Worker disk grows per Run; a lease loss mid-turn leaks the Claude process). All fixes are small and local. F3 needs a user decision (follow §12 cleanup, or amend §12).
