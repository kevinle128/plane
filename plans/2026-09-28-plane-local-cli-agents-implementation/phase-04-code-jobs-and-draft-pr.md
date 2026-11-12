---
phase: 4
title: "Safe Code jobs and draft pull requests"
status: in-progress
priority: P1
dependencies: [1, 2, 3]
---

# Phase 4: Safe Code jobs and draft pull requests

## Overview

Deliver Epic 3 stories 3.1–3.9 without losing the Run conversation or Worktree.

## Requirements

- Escalate an existing Run to a unique branch and Worktree and use it as the active CWD for later turns.
- Require request-bound grants for writes, path and network escalation, push, and PR creation.
- Enforce bounded Docker capacity with durable waiting and accurate slot recovery.
- Keep slot acquisition atomic and fair under concurrent claims and Worker restarts.
- Keep draft PR creation, conclusion mirroring, stop, resume, and failure recovery auditable.

## Architecture and affected files

- Extend the Run, Worker, GitHub, and panel contracts from earlier phases.
- Keep only the Worktree writable in Docker and exclude Plane checkout and default-branch push credentials.
- Store PR identity on the Plane Run and make retries idempotent.

The [permission API contract](../../docs/local-cli-agent-permissions.md) defines request identity, scope matching, decisions, and one-use effect consumption.
The [Code capacity contract](../../docs/local-cli-agent-capacity.md) defines the shared pool, durable waiting order, reservations, and reported reconciliation.
The [Docker boundary contract](../../docs/local-cli-agent-docker.md) defines read-only creation, exact granted file writes, identity inspection, and uncertain operation records.

## Implementation Steps

1. Back up the test database and implement Code state, capacity slots, and grants.
2. Implement Worktree retention, OS and Docker boundaries, grant enforcement, and recovery.
3. Implement push and PR creation through the Plane-owned GitHub integration and optional conclusion mirroring.
4. Verify protected effects, capacity, stale recovery, stop/resume, PR failure, and permission UI end to end.

## Success Criteria

- [ ] Stories 3.1–3.9 pass every listed Given/When/Then case.
- [ ] Denied, pending, mismatched, and stale grants cannot cause protected effects.
- [ ] Docker never exceeds the configured Code slot limit.
- [ ] A human can review a draft PR; the Agent cannot merge or push to the default branch.

## Risk and rollback

Do not replay a side effect after uncertain delivery without a new user command.
Retain Worktrees, event history, and branch identity after Stop or PR failure.
Reconcile actual containers before releasing stale slots.

## Current execution state

The [network boundary report](./reports/2026-09-29-network-boundary-progress.md) records native IPv4 and IPv6 endpoint filter checks.
The primitive passes approved TCP, denied destination and port, UDP denial, zero Agent capabilities, and changed-scope rejection checks.
Plane now hashes pinned destination IPs and requires a new decision for new IP addresses; all 77 permission contract tests pass.
The command-bound network proposal now requires a separate current process grant, and the full permission gate passes 82 tests.
The Worker has bounded system DNS resolution and the matching canonical proposal hash.
The command journal now retains both grants and private Docker resource identities before launch, with forward-only network phases.
The internal controller passes native creation, authority denial, ownership, filter, replay rejection, cleanup, and foreign-resource preservation checks.
The broader Worker gate passes 43 checks with two explicit native Claude opt-in skips.
Plane historical command reconciliation now retains the linked network identity, hash, pinned scope, and database-derived consumption state.
The full permission API gate passes 87 tests, including unknown, completed, unconsumed, and concurrent network-consumption histories.
Worker recovery now settles pre-command network preparation and gates exact journal clearance on a confirmed receipt and verified resource absence.
The focused native recovery gate passes two checks; the broader Worker gate passes 45 checks with two explicit native Claude opt-in skips.
The command launcher now uses the exact retained controller namespace, records the command container ID before start, and rejects replay or changed namespace identity.
Native recovery checks pass for pre-launch preparation, started command containers, denied start, and a completed bounded command.
The internal supervisor now consumes both exact grants, rechecks their status and the slot before launch, and publishes matching network facts after verified cleanup.
Native checks pass for actual approved loopback TCP, denied ports, zero capabilities, Deny, loss of either consumption receipt, lost result receipt, and Stop during the command.
The broader Worker gate passes 82 checks with 12 explicit native opt-in skips.
Paired HTTP network execution and receipt-loss recovery now pass with actual Django, member decisions, PlaneClient, Docker, and the bounded supervisor.
Both loss modes retain capacity until a new observer identity confirms historical settlement after controlled lease expiry.
Paired executor process death now passes at network consumption, completed result receipt, and active command execution.
The Worker recovery function stops verified resources, confirms historical acknowledgement, then clears the journal and releases capacity.
Code MCP now requests exact command approval followed by a separate pinned literal-IP network grant before calling the retained executor.
Native MCP pending, Deny, Allow once, destination validation, blocked port, consumption order, and cleanup checks pass.
Native Claude also passes command and network `Allow for Run` decisions through the same MCP route and actual Docker execution.
The MCP and Claude checks use a controlled permission client.
Paired HTTP MCP Allow once now passes through the private Code MCP server, actual Plane permission requests, member decisions, Docker execution, and result receipt before capacity release.
Pending command and network decisions cause no journal preparation, command creation, or Worktree output.
Paired HTTP MCP Deny and pending-network Stop now pass without consumption, command launch, or command result publication.
The Stop check verifies network authority rejection and MCP cancellation, while the durable Stop command remains pending.
Paired HTTP MCP consumption and result receipt-loss recovery now pass after controlled lease expiry with a new observer identity, no command replay, and preservation of later human output edits.
Historical acknowledgement precedes journal clearance and capacity release.
Polling Worker death and restart now pass with native Claude before and after Plane stores the completed network-command result.
The restarted Worker confirms exact historical command and network facts before journal clearance and capacity release, without command replay or changes to later human edits, index bytes, or branch HEAD.
Polling Worker death during active network-command execution now passes with native Claude, retained preparation, an unknown historical result, no replay, unchanged human edits, and settled Docker client groups.
Active network-command Stop now passes with native Claude and the full polling Worker, including historical unknown reporting before capacity release and Stop acknowledgement.
The shared Code completion and restart settlement route fixes the retained-journal Stop block without replay or early capacity release.
Polling Worker death after stored network consumption and before Docker network creation now passes with native Claude, no command launch or replay, and unknown historical settlement before capacity release.
The remaining namespace preparation boundaries, Harnesses, hostname permission flow, and visual product checks remain required.
Paired HTTP Code MCP now verifies `Allow for Run` inheritance for the same literal destination, separate pending decisions for changed port and IP, and no command consumption or output after those decisions are denied.
The inherited network permission retains a fresh exact command binding and its original grant link.
The network journal now records immutable Docker bridge and controller IDs before controller start, rejects rebinding and missing IDs at configuration, and preserves them through cleanup.
The native ownership check rejects a same-name, same-label replacement bridge without deleting it.
The broader Worker gate again passes 45 checks with two explicit native Claude opt-in skips.
Production permission, effect journal, recovery, Stop, and MCP integration remain required for Story 3.4.

### Remaining network execution work

1. Verify the connected literal-IP Code MCP executor through paired HTTP, including retained preparation, exact grant identities, pinned scope, trusted image, and namespace IDs before grant consumption or Docker launch.
2. Extend the verified literal-IP Allow once, Allow for Run, Deny, and changed-scope checks to hostname snapshots, revoked authority, required Harnesses, and the visual approval path.
3. Prove private namespace identity, immutable filter installation, and non-root command start through required native Harnesses.
4. Supply the approved DNS snapshot to the command's hostname lookup without opening unapproved DNS traffic; preserve the normal command's environment and resource limits.
5. Extend the verified consumption, completed-result, and active-command polling Worker recovery to namespace creation and configuration before command start.
6. Verify historical reporting without command replay for those remaining polling Worker boundaries and required Harnesses.
7. Connect the complete flow to Code MCP and prove approval, denial, changed scope, Stop, lost receipt, and process death through native and paired HTTP checks.

The existing Code container identity and network mode are immutable after creation.
Replacing a stopped container must verify its ownership and retained state first.
Guardian and bridge resources must have durable identities so recovery can inspect them without deleting unrelated Docker resources.
Additional controller memory must remain bounded per occupied Code slot.
DNS preparation must have its own prior authority; the internal helper rejects hostname lookup without an exact-host authority callback.
The member's DNS approval-flow decision remains pending, and no Host DNS exception is assumed.

### Other current effects

AD-8 now records the accepted additional-file write boundary: Docker produces bounded content and the trusted Worker publishes through pinned Host descriptors.
Exact write proposals and historical result reporting pass the shared permission and lease checks.
The exact additional-file executor now produces bounded content in Docker, persists publication identities and results, and exposes the matching Code MCP tool.
Native Claude Allow/Deny and receipt-gated recovery preserve later target edits without replay.
Paired HTTP normal write and both result-loss restart checks now pass without target replay, with historical acknowledgement before capacity release.
Complete path product flows and four-Harness conformance remain required.
The [path boundary report](./reports/2026-09-28-path-access-progress.md#additional-file-write-contract) records this evidence and the remaining publication and recovery work.
Plane now provides grant-bound PR creation and read-only reconciliation, with durable attempt and result events.
Run list and detail expose the confirmed PR identity without increasing the list query count.
The [permission contract](../../docs/local-cli-agent-permissions.md#pull-request-delivery) describes the effect and explicit retry rules.
The polling Code broker now has a PR tool for a verified committed and pushed branch, with its own matching grant.
The Activity card and timeline now render confirmed PR delivery with recorded state and a checked repository URL.
The PR component passed browser checks at 375, 380, 540, and 960 pixels in light and dark themes, with direct comparison to the Code job + PR reference.
Full-page and real-delivery browser checks remain required.
Protected push and conclusion mirroring remain required.
The Worker now captures an exact raw-content commit snapshot without staging or creating Git objects.
The internal Git primitive now creates a commit from the exact snapshot and advances only the Run branch with an expected-HEAD check.
It preserves clean Run-owned submodule Git links and rejects dirty or foreign submodules.
The commit wrapper now persists its candidate before branch publication and retains a published result until its result callback confirms acknowledgement.
Native executor death before or after the ref update and lost result acknowledgement preserve the record and block replay.
The commit wrapper now registers and cancels all Git commands within its execution context, with a separate process record that does not replace the commit candidate.
Worker startup, Run pickup, and stale slot recovery reconcile recorded Git process groups before further execution or inspection.
Stale-slot recovery now reconciles retained candidates, confirms the Plane receipt, and settles the index before releasing capacity.
Plane now accepts a strict `git.commit` proposal for the exact Run branch, parent HEAD, snapshot hash, subject, and changed-file count.
The permission contract rejects malformed or changed commit data before consumption and retains the current slot, lease, Stop, and one-use rules.
The per-turn `plane_commit` MCP tool now requests an exact snapshot grant and invokes the internal executor.
The internal Worker executor now consumes the exact commit grant under the Run lock, rechecks current permission before publication, and requires a confirmed Plane event receipt before removing its candidate record.
Native Git checks with a controlled Plane client cover changed approval, denial, stale slot, malformed consumption, Stop, revocation, identity configuration, and lost acknowledgement.
The internal Worker observer now verifies retained candidate identity and branch state without changing Git objects, refs, index, or source files.
Plane now records a consumed permission's matching historical commit observation with one durable receipt under repeated or concurrent reports.
This report neither releases the slot nor permits commit replay.
The internal index settlement method now repairs a published candidate's parent index with native index exclusion and durable lock ownership.
It preserves later source edits, rejects different staged changes, and resumes after executor death before or after index replacement.
An already settled index remains unchanged.
Stale-slot recovery now stops the verified old container, reports the exact candidate to Plane, validates the receipt, settles the index, clears the matching record, and inspects the container again before release.
An unpublished candidate requires a later accepted user reply before another commit request or consumption.
The paired HTTP check now proves separate file-write and commit approvals through the actual polling Worker, Claude, Docker, MCP, and Django APIs.
It verifies one confirmed commit result, the configured Human identity, unchanged default branch, record clearance after acknowledgement, and Stop at the next pending permission.
The paired restart modes exercise Worker death before or after Plane stores the published commit result.
They check that a new Worker reports the exact retained candidate before record clearance and capacity release, with no new claim or commit.
Prepared candidate and index settlement death remain covered by separate native checks.
Recovery across the complete Code-to-GitHub flow, protected push, real GitHub delivery, all four Harnesses, and complete browser checks remain required.
Real GitHub E2E evidence is still required.
Plane now requires an exact push proposal with the local commit and expected remote branch HEAD, including explicit absence for a new branch.
The Worker has a matching internal proposal builder and a shared canonical hash check.
The API rejects generic commands and changed identity before consumption.
The internal Git primitive now verifies exact local and remote HEADs, permits only forward publication to the Run ref, and uses an explicit remote ref lease.
It retains prepared and verified published candidates until its trusted result callback confirms acknowledgement.
Native Git checks cover remote races, denial, Stop, changed push URL and default branch, helper exclusion, lost acknowledgement, and executor death.
The internal push executor now binds exact grant consumption, current permission checks, and confirmed result receipts to the native transfer.
Public proposal capture now holds the Run effect lock and rejects retained effects.
Plane blocks new push requests and consumption until the prior consumed push has matching result history.
An unpublished historical result requires a later accepted user reply before retry.
Native executor and separate database API checks pass; paired HTTP push delivery and live GitHub delivery remain required.
The internal read-only push observer now validates retained candidate and repository identity and reports the exact remote ref without changing source, index, refs, or the candidate record.
Native checks include later staged and source edits, unpublished new and existing remote refs, transfer before published-state persistence, remote conflicts and rollback, Stop, malformed identity, and observation after executor death.
Plane now accepts exact historical push observations with one receipt under identical repeated or concurrent reports.
The API checks the exact grant and rejects a changed observation or conflict with a recorded result.
Publication requires consumption; an approved unused grant can report only an unpublished result.
Stale-slot push recovery now stops the verified container, confirms the receipt and a second matching observation, clears only the matching record, and inspects the container again before release.
It preserves later staged and source edits and reports `push_unsettled` when a pending pickup retry cannot settle the candidate.
The Worker now atomically retains the complete push candidate before requesting grant consumption.
An uncertain consume response retains that candidate and blocks replay.
Historical reporting closes the original permission, requires a later accepted user reply for another push, and records whether Plane actually consumed it.
The per-turn `plane_push` MCP tool now requests the exact push grant and invokes the retained executor after approval.
Its input cannot select repository, branch, commits, commands, credentials, or force options.
The Claude Code allowlist and trusted prompt include this tool; the Q&A route excludes it.
Native checks cover schema, approval, denial, Stop, changed remote identity, uncertain receipt, and actual Claude invocation.
Older uncertainty without a retained candidate and live GitHub checks remain required.
The normal paired HTTP push mode now passes with the actual polling Worker, authenticated Claude, MCP, Docker, native Git, and Django endpoints.
It verifies separate write, commit, and push approvals, exact result receipts, no remote ref before push approval, unchanged local and remote default branches, and Stop at the next pending file write.
The fixture uses private local Git transport and does not prove live GitHub publication.
The paired published push restart modes now pass before and after Plane stores the result.
They kill the actual Worker, expire its lease through the production task, and start a new polling Worker.
They verify exact historical acknowledgement before candidate clearance and capacity release, unchanged local and remote commits and default branches, and no new claim or protected effect.
The paired HTTP PR modes now pass for both saved Draft policy values.
They verify separate write, commit, push, and PR approvals through the actual polling Worker, Claude, MCP, Docker, Git, and Django endpoints.
The controlled GitHub boundary checks the consumed PR grant, exact pushed SHA, one creation request, durable PR identity, human-merge note, and conclusion URL.
No PR creation event exists before approval, and Stop blocks the next pending write.
These modes use controlled external GitHub responses and private local Git transport; live GitHub authentication and publication remain required.
Conclusion mirroring now stores a durable per-turn target and pending state in the conclusion transaction.
Celery processes it after commit, with a partial queue index and a minute scan to recover missed submissions or stalled tasks.
Only the first attempt can POST; uncertain delivery uses durable bounded read-only pagination.
The integration validates current authority and records exact comment identity or a readable failure without changing the work-item conclusion.
The panel keeps polling until all mirrors settle and refreshes after the final mirror event.
The final 19 database checks pass, including rollback and an indexed queue scan over 2,121 turns with a batch limit of 100.
The native HTTP mirror mode and its paired Django check pass with controlled task dispatch and external GitHub responses.
Schema drift, migration forward and rollback, web tests, typecheck, lint, and formatting checks pass.
Actual Celery deployment, live GitHub delivery, and full browser evidence remain required.
The paired HTTP mode now also passes with a real AMQP publisher and embedded Celery solo consumer against the isolated RabbitMQ service.
It validates private queue routing, consumer host, successful task execution, and disabled direct and eager execution.
The combined 19 mirror checks and this HTTP mode pass on the new test image, which installs dependencies at build time and needs no package download at startup.
Separate process pools, deployed Beat recovery, live GitHub delivery, and full browser evidence remain required.
The internal Docker command primitive now bounds argv, timeout, captured output, and the host Docker pipe.
It stops the verified container after each command and on Stop, including detached descendants.
It retains uncertain execution until result acknowledgement and rejects a replacement command while the record remains.
Exact command permission, MCP routing, and historical reconciliation remain required before exposing it to Agents.
Plane and Worker now have matching exact command proposals and hashes.
Command Run grants match only identical argv, timeout, and Worktree, and Plane blocks a later command while the last consumed command has no confirmed result.
Executor consumption binding, durable command reconciliation, and MCP routing remain required.
The command executor now consumes the exact grant under the Run effect lock after durable preparation, rechecks current authority, and persists settled output before result acknowledgement.
Native Docker checks cover normal execution, uncertain consumption, revoked authority, and lost receipt; abrupt executor death preserves both prepared and completed records.
Historical reporting, stale-slot reconciliation, and MCP routing remain required before Agent access.
Command historical reporting and stale-slot reconciliation now preserve completed output or explicit uncertainty without replay.
Plane closes the original request and requires a later accepted user reply after an unknown result.
The Worker retains its record and slot until the exact receipt and stopped-container checks pass.
Commands also reject shared hard links before consumption and again before execution.
MCP routing and the complete HTTP flow remain required.

The Code broker and Claude allowlist now expose bounded command execution with exact permission waiting.
Native Claude and paired HTTP checks pass for file write, approved test command, result acknowledgement, commit, and Stop.
Paired HTTP command restart recovery and the other remaining acceptance checks are still required.
The paired HTTP command restart modes now pass before and after Plane stores the result.
A new polling Worker confirms historical completion before capacity release, without command replay or changes to later human edits, index, or branch HEAD.

The [additional path report](./reports/2026-09-28-path-access-progress.md) records the descriptor boundary and the rejected direct-bind assumption on Docker Desktop.
Four real descriptor checks pass for exact operation flags, canonical scope, protected roots, links, path replacement, and bounded inspection.
Path permission consumption, scoped file publication, durable recovery, and Agent/HTTP routing remain required.

Plane and Worker now share the exact bounded external-file read contract.
The internal executor persists preparation before consumption and output before acknowledgement; native checks prove no read after lost consumption or revoked authority and retained output after lost receipt.
Historical read reporting and native restart settlement now pass with the external file deleted and later Worktree source/index edits preserved.
Plane closes the original request, rejects changed observations, and requires a later accepted user reply after an unknown result.
A missing receipt retains the read record and Docker capacity.
The shared observer passes the expanded 63 permission and lease checks, and the native recovery suite passes.
An actual native Claude external Read attempt returned no fixture content without a Plane grant; this check does not prove the full host or network boundary.
Code MCP routing now accepts only an operation UUID, exact file, offset, and bounded count and waits for the existing Plane permission contract.
Native broker checks cover strict arguments, pending decisions, Deny, Stop, binary bytes, and lost receipts.
Native Claude checks verify the approved tool read and the blocked unapproved native Read attempt.
Normal additional-file reads and both result delivery/receipt loss restart modes now pass across Django, the polling Worker, native Claude, and MCP.
The external source is deleted before read recovery, and later source edits, index bytes, and branch HEAD remain unchanged.
Plane records one historical result before another Worker clears the record and returns capacity.
The native hard-link probe exposed an unapproved Worktree read that restricted CLI mode did not block.
The shared OS boundary now blocks direct Run-file data reads and symbolic-link access.
Shared repository read, list, and search tools preserve Q&A and Code access through current Plane authority and pinned descriptors, with bounded results and explicit continuation.
Native direct, symbolic-link, and hard-link attack probes and the approved repository-tool flow pass.
The complete read conformance audit, additional-path writes, and complete permission product checks remain required.
