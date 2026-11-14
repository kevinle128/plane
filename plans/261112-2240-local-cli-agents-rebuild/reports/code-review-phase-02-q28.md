# Code review: Phase 2, Q28/Q29/Q30 (run Claude as installed; HOME check)

Date: 2026-11-14 (Asia/Saigon). Scope: `f08b6e3cde`, `04a40a3301`, `apps/agent-worker` only.
Decisions applied: Q28, Q29, Q30 in `plan.md`. No hardening beyond them is proposed.

## Verification

- `uv run pytest -q -m "not native"`: 110 passed, 1 deselected, exit 0. The "Exception occurred during
  processing of request" line is a server-side trace from a test HTTP server; it fails no test.
- Session flags: `--safe-mode`, `--restricted`, `--strict-mcp-config`, `--setting-sources` removed
  (`drivers/claude.py:95-103`); test asserts they are absent.
- Write protection: bare-name `Edit`/`Write`/`NotebookEdit` deny (`claude_boundary.py:44,86`), sandbox
  `enabled`, `failIfUnavailable`, `allowUnsandboxedCommands: false`, `denyWrite: [cwd]`
  (`claude_boundary.py:75-82`). Scalar keys come from the `--settings` file, which ranks above user
  settings, so a user `enabled: false` or `allowUnsandboxedCommands: true` has no effect.
- Allowing the Bash prompt in the permission turn (`claude.py:641`) is safe: with
  `allowUnsandboxedCommands: false` the command still runs in the sandbox, and
  `bash_write_problem` (`claude.py:746-758`) still fails when the file exists or the result is not a
  sandbox denial. Only the probe uses `allow_tools`; no Run code path answers prompts yet.
- File-tool check now reads the `init` tool list (`claude.py:355-356, 736-743`). The recorder drops
  `tools` from a copy (`conformance.py:411`), not from the message the driver parses. The native result
  (Write removed although `--tools Bash,Write`) is recorded in `phase-02-implementation-report.md:162`.
- Secret reads: `denyRead` and `Read(...)` deny rules unchanged; asserted in
  `test_every_session_runs_with_the_worker_boundary_settings`.
- Scrub: `FIXED_ENV` (`claude.py:131`) applied after the allowlist; covered by two tests.
- Cache: `SUITE_VERSION = 2` (`claude.py:71`), so v1 records are not used; fingerprint now includes the
  environment and is pinned for v2 (`test_suite_cache.py:20`).
- HOME check (`config.py:135-143`) runs first in `load_config`; tests cover missing, empty, relative and
  absent directory.

## Critical

None.

## Important

1. Secret-read protection is not proven by the probe, but Q29 says the "user settings cannot widen
   the boundary" check covers it. `test_user_settings_cannot_widen_the_boundary`
   (`tests/test_claude_probe.py:211`) sets user `denyRead: []`. The fake ignores reads
   (`tests/fakes/fake_claude.py:168-176` models only tool removal and `denyWrite`), and no suite check
   reads a denied path (`drivers/base.py:22-30`). So the test passes no matter how the CLI treats
   user read settings. Narrow failure scenario: a user `sandbox.filesystem.allowRead` entry (the known gap
   in `claude_boundary.py:34`), or a CLI change that affects read rules but not write rules. The suite
   still passes, the version is cached as verified, and a Bash command inside the sandbox can read
   `~/.ssh` or the Worker token file. A CLI where the user `sandbox.filesystem` object replaces the
   Worker one is already caught: `denyWrite` is in the same object, so the real Bash write in the
   permission check would succeed and fail the suite. The `Read(...)` permission deny rules still
   protect the Read tool; the gap is Bash reads in the sandbox only.
   Two valid options under the decisions: (a) add a Bash read of one denied path to the permission
   check and require a sandbox denial (the native test
   `test_real_claude_probe_passes_and_a_second_probe_uses_the_cached_suite`, `test_claude_probe.py:447`,
   then exercises it on the real CLI), and make the fake honor `denyRead` so a fake test can fail; or
   (b) narrow the test name and the Q29 sentence so they claim only the write rules.

## Informational (no action required by the decisions)

- `claude_boundary.py:34-36` lists `allowRead` and `excludedCommands` as not closed. A user
  `sandbox.filesystem.allowWrite` entry outside the working directory also merges and lets Bash write
  there. This is a docs-accuracy note on the same accepted Q28 trade-off, not a hardening request.
- `_check_home` strips HOME but `harness_env` passes it unstripped; a HOME with trailing whitespace
  passes the check and then fails in Claude. Unlikely in practice.
- Removing `prompts_for_write` leaves the deny branch of `read_turn` (`claude.py:378-379`) without a test.
  It does not break either protection in the probe.
- A cached pass is keyed on (Harness, CLI version, suite version); under Q28 user settings can change
  without a new version. Accepted consequence of Q28.
- `permission_prompt` is now True on every real probe (Claude Code asks before the sandbox-denied write).
  The API and web only store and type it (`harness_probe.py:41`, `packages/types/src/agent/agent.ts:40`);
  nothing gates on it, so Connect is not affected.

## Verdict

Approve with one Important item. Connect, the write protection, the probe logic and the cache logic are
correct for Q28/Q29/Q30. Fix the secret-read proof gap (or narrow the claim) before the PR.
