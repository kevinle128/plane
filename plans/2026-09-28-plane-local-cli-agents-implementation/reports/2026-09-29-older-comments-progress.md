# Older comment retrieval progress

## Scope and result

Story 2.12 remains in progress.
The Worker now has leased endpoints for earlier comments from its Run work item.
The endpoints reuse the member comment ordering, cursor, and visibility rules.
Each request checks the requester, current lease, and pending Stop.
The service token owner does not need project membership and does not supply the comment read authority.

## Bounds

Each page contains at most five comments with 1024-character excerpts.
Each detail request contains at most 4096 characters with a character offset and next offset.
Database substring expressions bound the loaded content.
The existing member endpoints retain their current contract.

## Verification

The valid Worker request first returned 404 because no Worker route existed.
The final lease and Run creation contract suites passed all 31 checks in 8.44 seconds.
The new check covers a separate service token owner, requester revocation, another issue, private panel content, Unicode chunks, invalid bounds, malformed request bodies, stale generation, and pending Stop.
Ruff passed for all four changed Python files.

## Remaining acceptance

The shared MCP tools and Plane client now connect these endpoints for Q&A and Code.
The initial prompt names both tools and retains the omission count and cursor.
The MCP checks reject agent-selected Run, workspace, lease, malformed UUIDs, Boolean numbers, and requests beyond the page or chunk bounds.
The tools preserve Unicode text and stop on a pending control command.
Nine focused Worker checks passed in 1.510 seconds.
A native Claude broker check passed in 5.320 seconds and fetched an omitted comment followed by its remaining text.
That native check uses a controlled client response and does not prove the complete API-to-Worker flow.
The full Code tool and Claude driver suites passed 28 checks in 9.981 seconds, with four opt-in native checks skipped.
The new native retrieval check was run separately with the authenticated local Claude model.
The first broad run found one outdated Code tool-list assertion; the assertion now includes the two required comment tools.
Final Ruff checks passed for all seven changed Worker Python files.
All owned MCP servers and native processes stopped after the checks.
The later [HTTP acceptance report](./2026-09-29-older-comments-http-acceptance.md) completes polling Worker retrieval through the Plane API, stable pagination, and context isolation.
