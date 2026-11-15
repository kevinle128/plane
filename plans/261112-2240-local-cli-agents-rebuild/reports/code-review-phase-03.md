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

## Re-review of the fixes

Reviewer: code-reviewer (fresh context), 2026-11-15 (Asia/Saigon). Scope: `git diff 58d8ab3f7d..HEAD -- apps` (7138ccb5b7, ee7a891833, 5bdb118d73, ec5ea2f210, 5793652ecd and their tests). Not committed.

### Status of the findings

- F1 fixed. `runs.py` `_clone.fetch_token`: a 409 with `lease_superseded`/`run_finished` (`LEASE_CODES`; these are the only codes from `lease.check_lease`, `lease.py:65-67`) is still `LeaseLost`. Any other 409 (`provider_disconnected`, `provider_reconnect_required`) becomes `RunFailure(<code>)`, and the Worker posts a failed result. The `RunFailure` leaves `clone_repository` with no wrapping, because `fetch_token()` is called outside any try (`git_transport.py:271`). Tests: `test_refused_gitlab_credential_fails_the_run_with_the_provider_code`, `test_superseded_lease_on_the_gitlab_credential_posts_no_result`.
- F2 fixed. `drivers/claude.py:518-521` `except BaseException: session.kill(); raise`. `kill` runs the pidfile kill in the sandbox, then `killpg`, then `registry.release`. It runs inside `Sandboxes.use`, so it takes no sandbox lock. Test `test_lost_lease_during_the_turn_stops_claude_in_the_sandbox` checks the in-sandbox kill, that the registry record is gone, and that the PID is dead.
- F4 fixed. `SandboxLock` (`sandbox.py`): a turn holds the sandbox shared (`use`) for the version check plus the turn. `remove`/`_create`/`stop` run only in `exclusive()`, which waits for `users == 0` while it holds `check`. No deadlock: `enter` needs `check`, which the exclusive waiter holds, so the user count can only go down. `leave` needs no `check`. Inside a `use`, the turn only calls `ensure` on the probe sandbox, which has another name and another lock (`claude.py:545`), so no thread waits on its own shared hold and no lock cycle exists. `exclusive()` holds the Condition during the sbx call, but no thread can call `enter`/`leave` then (users == 0, `check` held). Starvation is bounded: new Runs on the same repository queue behind the waiter until the live turns end (turn limit), as the module docstring says.
- F5 fixed. `_post_result` retries a non-409 `PlaneClientError` 3 times (2/5/10 s), on both the success path and the failure path. Network errors are mapped to `PlaneClientError` (`plane_client.py:83-85`), so they are retried too. A retry cannot post twice: if an earlier try was applied, `apply_result` returns early for a finished Run (`conclusion.py:50-51`, before the lease check), which creates no second comment. The retries are bounded (about 17 s plus 4 client timeouts), and the lease renewer keeps running until `finally`.
- F6 fixed. `git_host_blocked` was added to `GIT_ERROR_CODES` and has a contract test.
- Q45 cleanup is correct for active Runs. `execute` adds the Run to `_active` before `layout.create()`. `remove_stale_folders` holds `_active_lock` for the whole scan. `touch()` and the discard are atomic under that lock. The cleanup runs on the loop thread before `_run_step`, so a claim cannot interleave with it. `run_folders` matches only UUID-named, non-symlink directories under `sandboxes/*/{clones,scratch}/`. It does not match `sandbox.json`, other scratch entries, or probe folders (`suite-<harness>-<ver>`). Tests in `test_run_cleanup.py` cover these cases.

### New finding

#### R1 (Important) Markdown answers lose all text in angle brackets outside code

- `apps/api/plane/utils/markdown.py:9` sets `create_markdown(escape=False, ...)`, so mistune passes raw HTML through. `conclusion.py:36` then sanitizes with nh3 (`content_validator.py:224-229`), which removes every unknown tag. Any prose like `Promise<void>`, `List<String>`, `Vec<u8>` or `<your-token>` is parsed as an HTML tag and removed with no trace.
- Verified on a copy (/tmp/p3rr, mistune 3.4.0 + nh3 0.2.18 + the branch's `content_validator.py`/`markdown.py`): `"returns Promise<void> and List<String>; set <your-token> then run"` -> `<p>returns Promise and List; set  then run</p>`. Code spans and code blocks are escaped correctly.
- Scenario: Claude explains a typed API or a config placeholder in prose. The comment shows a wrong answer (for example "set then run"). Only the event payload keeps the raw text.
- Fix: `escape=True`. You must also change the two `"alert(1)" not in html` assertions in `test_agent_conclusion.py:65,101`: escaped script text then stays as visible text. It was checked on the copy: Markdown still renders, and `Promise&lt;void&gt;` is kept as text. Raw HTML from the agent (including `<mention-component>`) then shows as text and is not rendered. Add a test with angle-bracket prose.

### Mention elements in conclusion comments

- A raw `<mention-component entity_name="user_mention" entity_identifier="<uuid>">` in the agent's answer is kept. `escape=False` passes it through, and nh3 allows the tag with `id`, `entity_identifier` and `entity_name` (`content_validator.py:74,136`). Verified on the copy. It renders as a mention chip.
- It does not send a notification. `apply_result` creates the comment with `IssueComment.objects.create` (`conclusion.py:59-65`) and calls no `issue_activity.delay`. Notifications only come from `issue_activity` -> `notification_task.py:256` (`extract_comment_mentions`, `:133-137`), and email only from the logs that task writes (`email_notification_task.py:133`). Plane has no signal on comments or descriptions: the only `@receiver` is `db/models/user.py:299`, there is no `.connect(` signal registration, and `api/apps.py` `ready()` imports only the OpenAPI auth. If an admin later edits the bot comment (`app/views/issue/comment.py:154`), only mentions that are not in the old HTML count as new (`get_new_comment_mentions`). The agent's mentions are in the old HTML, so they do not notify.
- An `agent_mention` in an answer does not start a Run. `create_runs_for_comment` is called only from the comment create view (`app/views/issue/comment.py:127`).
- R1's fix (`escape=True`) also stops the chip from rendering.

### Checks run

- Worker: `uvx --from uv==0.12.21 uv run pytest -q -m "not native"`. Exit 0. 275 tests passed by the progress-dot count; this run prints no summary line. One "Exception occurred during processing of request" log line comes from a test HTTP server and is not a failure. An earlier foreground run was killed (exit 137) when the session ended. That was not a test failure.
- Markdown/sanitizer experiments on a copy at /tmp/p3rr (code block, user/agent mention, javascript: links, img onerror, iframe/svg, table, unclosed tags, angle-bracket prose).
- API suite not run in this re-review (the test container mounts ./apps/api).

### Verdict

F1, F2, F4, F5 and F6 are fixed and covered by tests. Q45 cleanup never removes the folders of an active Run or any non-Run data. The sandbox lock has no deadlock, and its waits are bounded by the turn limit. Before the PR, fix R1 (`escape=True`, a test with angle-bracket prose, and the two changed assertions). After that, the branch is ready.
