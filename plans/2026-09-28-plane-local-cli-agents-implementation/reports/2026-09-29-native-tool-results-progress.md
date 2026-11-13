# Native tool result progress

## Reproduction and repair

The actual authenticated Claude CLI returned three `tool_result` blocks from repository list, read, and search tools.
The driver emitted zero result events, so the native test failed with `0 != 3`.
The driver now emits an additive `tool_result` event and retains the complete typed native block as ordered `result_json` parts of at most 8,000 characters.
Invocation and result payloads retain the native `tool_use_id`.
Each result also retains its error flag and part index.
The Plane event endpoint accepts the new kind under its existing lease, size, and idempotency checks.
Recovery context includes committed tool results.
The panel renders result parts in the Working group without adding an action step.

## Evidence

- Seven driver tests pass, including complete long Unicode content, typed content, error results, and exclusion of user prompt text.
- The actual native repository tool test passes with three exact calls, native call IDs, three retained results, and exact reconstructed native blocks.
- The native test uses real Git, the production Host read boundary, the production MCP broker, and authenticated Claude.
  Its Plane permission client is a declared fixture; this is not proof of native-to-API delivery.
- The 25 API lease contract tests pass in an isolated Docker stack.
  The result case verifies stored payload equality, idempotent replay, conflicting replay, incorrect Worker identity, expired lease, and revoked Worker token.
- Eleven timeline helper tests pass, including grouping a result with its action, complete multi-part content, typed native blocks, missing and repeated parts, and isolation between turns.
- Web type checks, targeted OxLint, Worker Ruff checks, and formatting pass.
- Review reproduced rejection of ordinary source text with a literal `\u0000` escape.
  The API now distinguishes an escaped backslash from JSON's actual NUL escape.
  The API result test retains the literal source text and checks nested actual NUL after zero to three backslash prefixes.
- One intermediate native rerun had fewer calls than the requested three.
  The test now reports actual tool names on a count mismatch, and the subsequent native run passed.
  This observation does not prove the cause or remove the remaining native reliability work.
- The owned API test stack and native broker were stopped after verification.
- Final read-only review passed.
  The reviewer verified 240 key, nested-value, and backslash-prefix cases for the escape repair without a mismatch.

## Native HTTP and presentation follow-up

The new `tool_results` mode passes both the API fixture test and native polling Worker test.
It executes four actual Claude MCP calls in order: list, read, search, and read an absent file.
The long source contains 4,000 Unicode characters, 12,000 ASCII characters, and a literal source `\u0000` escape.
The member endpoint returns enough result parts to reconstruct the exact source and the native unavailable-file error.
Invocation IDs match the retained native result blocks.
A second member history read after the Harness process registry clears returns the exact same events.
No Code handoff or permission grant is used.
GitHub registration and repository authorization are declared fixture data; the Worker, native CLI, MCP reader, HTTP event writes, database, and member reads remain real.

The first integration test exposed a test-only assumption that native `content` must be a list.
The observed native records use strings; the test now supports the actual string form and the typed-list form.
The repeated paired checks pass.

Presentation now groups parts once by call identity and turn, decodes source content, and retains the complete native block under Full result record.
Missing or repeated parts remain visible with an incomplete-result label.
Review found a queued member message between chunks could produce an empty Working group.
Grouping now skips subordinate result parts before constructing groups, and the focused interleaving test passes.
Final read-only re-review passed without a new concrete regression.

## Remaining acceptance

Story 2.8 remains in progress.
The [browser result report](./2026-09-29-tool-result-browser-acceptance.md) now verifies completion, reload, cursor boundaries, exact decoded content, full records, keyboard detail and scroll, and Light and Dark presentation.
Complete the remaining result formats, full panel accessibility, and other design scenes before marking the story done.
