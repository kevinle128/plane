# Older comment HTTP acceptance

## Scope and environment

Run the actual polling Worker, authenticated native Claude, private MCP server, and Django HTTP API against an isolated fixture stack.
The fixture creates a Run with its current request and builds its context through the production `build_run_context` function.
Its work item has three earlier comments.
The newest earlier comment contains 128001 Unicode characters before a final marker.
It exceeds the comment budget, so all three earlier comments are omitted from the initial context.
The fixture also creates comments on another issue and another workspace, plus a private panel message on another Run of the same issue.
The repository and local clone are isolated fixtures.
No GitHub publication or other Harness acceptance is claimed.

## Direct evidence

The initial context reports exactly three omitted comments and supplies the older-history cursor.
The native Agent uses the shared tool to request one comment per page until `next_cursor` is null.
The API captures the actual responses and verifies all three IDs in newest-first order, with author IDs and creation times.
The Agent reads the newest comment at character offset 128001 and obtains its final marker.
Its stored conclusion includes the markers from both smaller comments and the large comment's remaining text, plus the repository content.
The Agent requests each forbidden ID through the detail tool.
All three requests return 404.
The captured responses contain neither the forbidden comment content nor the other Run's private panel text.
The Run remains Q&A, completes turn 1, and creates no effect permissions.
The source file remains unchanged.

## Checks and limits

The native side passes in 43.644 seconds.
The API side passes in 33.36 seconds.
Focused Ruff checks pass for both changed fixture files.
The earlier 31 API contracts cover stale leases, pending Stop, requester revocation with a separate service token owner, bounded chunks, Unicode text, and malformed inputs.
The earlier Worker checks cover strict MCP schemas and fixed Run and lease routing for both Q&A and Code.
The prompt check retains identity, the current request, exact omission count, cursor, and tool names.
Other Harness execution remains in its own driver stories.

## Story 2.12 completion audit

| Acceptance criterion | Direct evidence |
| --- | --- |
| Context limits retain identity, current request, essential content, exact omission count, and authorized retrieval path | Production context builder with an oversized comment, prompt assertions, and native retrieval using the supplied cursor |
| Returned pages contain only authorized Run work-item comments with stable IDs, authors, times, and order | Actual three-page HTTP response assertions, current requester checks, and native stored conclusion |
| Other issues, workspaces, and private Run panel content are excluded | Native requests for all three forbidden IDs return 404, with forbidden content absent from captured responses |

## Cleanup

The native and API processes exit successfully.
The owned isolated Compose stack and network are removed.
Private fixture credentials and temporary configuration are removed after review.
No credential is stored in this report or the checkout.

## Review

**Summary:** Actual native retrieval through the polling Worker and Plane API meets all three Story 2.12 criteria.
**Critical issues:** None found.
**Major issues:** The remaining 37 stories require their own acceptance evidence.
**Minor issues:** Initial Run and repository setup are isolated fixtures.
**Positive feedback:** The implementation reuses the current member visibility, stable cursor, and private Run MCP contracts with bounded database reads.
**Questions:** AD-7 and DNS decisions remain pending and are not assumed.
**Verdict:** Mark Story 2.12 done and keep the complete goal active.

The separate read-only code review found no concrete defect in lease checks, requester visibility, issue scope, ordering, Unicode offsets, bounds, or MCP routing.
Workspace removal and self-leave deactivate project memberships before workspace membership, so the shared active-project-member check covers those supported paths.
