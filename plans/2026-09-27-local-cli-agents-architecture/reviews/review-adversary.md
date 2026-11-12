# Adversarial Review

Reviewed:

- `plans/2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md`
- `plans/2026-09-27-local-cli-agents-prd/prd.md`

## Pair 1: Permission grant identity

Severity: High.

Epic A can implement permission as a durable pending request.
It stores `permission_request_id`, `turn_id`, `lease_generation`, proposed command hash, action kind, scope, and risk text.
The member decision references that request ID.
`allow once` is consumed by exactly that request.
The sandbox receives a one-use grant token that names the request ID.

Epic B can implement permission as a Run-level grant table.
It stores `run_id`, `lease_generation`, `action`, `scope`, decision, actor, and time.
`allow once` means the next matching action in the current lease.
The Worker turns the container mount or network mode on for that matching action class.
It does not require a pending request ID.

Both obey the current ADs.
AD-1 only says Plane owns permission decisions and timeline events.
AD-8 only requires actor, time, action, scope, current lease, and current Run.
It does not say that a decision must bind to one pending permission prompt or one proposed command.
Driver prompts still map into Plane, and OS or Docker restrictions still stay active in both designs.

They are incompatible.
The UI epic can wait on a specific permission request ID while the Worker epic consumes a generic matching grant.
A stale or repeated driver prompt can use the wrong `allow once`.
The durable timeline cannot prove that the approved command is the command that ran.
The two data shapes also cannot share one audit or replay contract.

Minimal AD fix:

Add to AD-8:

Every permission prompt creates a durable Plane permission request with `permission_request_id`, `run_id`, `turn_id`, `lease_generation`, `action_kind`, normalized `scope`, proposed effect hash, and display risk.
Every decision references one request ID.
`allow once` is consumed only by that request.
`allow for Run` may authorize later requests only when the action kind and normalized scope are within the approved scope.
The Worker must pass a request-linked grant to the sandbox before the effect runs.

## Pair 2: Active Run workspace after Code escalation

Severity: High.

Epic A can implement local execution with a mutable active workspace.
It stores `run_clone_path`, optional `code_worktree_path`, branch name, and `active_workspace`.
Q&A launches in the fresh Run clone under a read-only boundary.
When the same Run becomes a Code job, the Worker creates the Worktree and sets `active_workspace` to the Worktree.
Later same-Run messages, resume, and stale retry launch the Harness from that Worktree.

Epic B can implement context and recovery with one immutable Run CWD.
It stores the fresh clone path in the Run context snapshot at pickup.
The prompt formatter and resume path always launch the Harness from that stored CWD.
The Code job stores its Worktree in a separate code-delivery record and uses it only for writes and pull request creation.
Later same-Run messages reconstruct from the transcript and context snapshot, then launch from the original clone.

Both obey the current ADs.
AD-2 requires the Run to store identity and repository binding IDs and to build a versioned context snapshot.
AD-6 says the Plane Run ID is the conversation identity and a Q&A-to-code change may replace the driver process.
AD-7 says each mention gets one fresh clone and Code work uses a Worktree and branch owned by that clone.
No AD defines the canonical active CWD after escalation or says that same-Run follow-ups must launch from the Worktree.

They are incompatible.
Epic A makes later messages read the changed Worktree state.
Epic B makes later messages read the unchanged clone state.
The PRD requires later messages in that Run to read the Worktree state.
Stale retry and Harness restart will also diverge because one resumes from the Worktree and one resumes from the clone.
Both designs can retain the clone and Worktree, but they do not agree on which path is the live workspace.

Minimal AD fix:

Add to AD-6 or AD-7:

A Run has an immutable `run_clone_path` and an optional `code_worktree_path`.
The Worker records `active_workspace_kind` as `clone` or `worktree`.
Q&A starts with `active_workspace_kind=clone`.
When a Run escalates to Code, the Worker creates the Worktree and sets `active_workspace_kind=worktree` before any write.
All later same-Run prompts, Harness resumes, stale retries, and pull request summaries use the active workspace.
The active workspace must never be the Plane deployment checkout or a shared Mirror.

