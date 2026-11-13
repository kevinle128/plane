# Reality Review: Architecture Spine

## Verdict

PARTIAL.

The spine preserves the accepted product constraints for no ACP, no remote execution in v1, and one fresh clone per mention.

The spine is not fully reality-checked for the four Harness driver contract.
Claude Code, Codex CLI, Grok CLI, and Omp exist on this Mac, but the spine claims one common driver surface before it proves that all four can supply model discovery, event streams, cancellation, permission responses, midturn input, and native resume.

The Plane ASGI claim is supported for the API runtime.
The GitHub owner claim is only partly supported by current Plane CE code.
The sandbox claim is a design rule, not an implemented or fully specified enforcement plan.

## Evidence

- `plans/2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md:73` says each Harness driver implements connect and capability check, model discovery, start or resume, send, event stream, cancel, permission response, and shutdown where supported.
- `plans/2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md:77` names four v1 drivers: Claude Code, Codex CLI, Grok CLI, and Omp.
- `plans/2026-09-27-local-cli-agents-prd/prd.md:274` requires each Harness to support conversation, progress, permission, cancellation, and recovery through its own verified control path.
- `claude-design/design_handoff_local_cli_agents/README.md:219` says the design does not define how the worker reaches each Harness, including CLI or ACP.
- `plans/2026-09-27-local-cli-agents-prd/prd.md:286` says ACP is not part of this architecture direction.
- `plans/2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md:179` defers driver command flags and parser details to connection probes.
- `command -v claude codex grok omp` found local binaries at `/Users/dale/.bun/bin/claude`, `/Users/dale/.local/bin/codex`, `/Users/dale/.grok/bin/grok`, and `/Users/dale/.bun/bin/omp`.
- `claude --help` shows `--print`, `--output-format stream-json`, `--input-format stream-json`, `--resume`, `--permission-mode`, and `--permission-prompts`.
- Official Claude Code CLI docs also list streaming JSON output, streaming JSON input, resume, and permission prompt handling in non-interactive mode: https://code.claude.com/docs/en/cli-usage.
- `codex --help` and `codex exec --help` show interactive and non-interactive modes, `exec resume`, JSONL output, sandbox modes, approval controls, queue, and app-server commands.
- Official OpenAI Codex CLI docs describe local CLI use, permissions, `codex exec`, and session resume: https://learn.chatgpt.com/docs/codex/cli.
- Official Codex app-server docs show approval flows for commands, file changes, MCP elicitations, and permission requests: https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md.
- `grok --help` shows a Grok Build TUI, headless output formats, `--resume`, `--permission-mode`, `--sandbox`, `models`, `sessions`, and `worktree`.
- Official xAI docs verify Grok Build as an agentic coding model and show `grok-code-fast-1` as an alias for `grok-build-0.1`: https://docs.x.ai/developers/models/grok-build-0.1.
- Official xAI retirement docs say `grok-code-fast-1` was retired on May 15, 2026 and redirects to `grok-build-0.1`: https://docs.x.ai/developers/migration/may-15-retirement.
- `omp --help` shows non-interactive mode, JSON/RPC modes, continue/resume, model flags, approval mode, tools, and an ACP command.
- Official Omp docs describe a terminal coding agent, local saved sessions, resume, RPC mode, ACP docs, and approval controls: https://omp.sh/docs.
- `apps/api/bin/docker-entrypoint-api.sh:38` runs `gunicorn` with `uvicorn.workers.UvicornWorker` and `plane.asgi:application`.
- `apps/api/plane/settings/common.py:195` and `apps/api/plane/settings/common.py:196` set both WSGI and ASGI application paths.
- `apps/api/plane/asgi.py:18` exposes an ASGI `ProtocolTypeRouter` for HTTP.
- `apps/api/docs/django-5.2-migration-plan.md:53` says `apps/api` is Django, DRF, Celery, and Channels with ASGI HTTP only.
- `apps/api/plane/db/models/integration/github.py:14` defines `GithubRepository` with `repository_id`, `owner`, and `url`.
- `apps/api/plane/db/models/integration/github.py:32` defines `GithubRepositorySync` as project-scoped through `ProjectBaseModel`, with a one-to-one repository link and `unique_together = ["project", "repository"]`.
- `apps/web/core/services/project/project.service.ts:143` posts repository sync data to a project-scoped GitHub repository sync endpoint.
- `apps/web/core/components/project/integration-card.tsx:59` sends `name`, `owner`, `repository_id`, and `url` for a selected GitHub repository.
- `rg "github-repository-sync|github-repositories|WorkspaceIntegration|GithubRepository" apps/api/plane -S` found the GitHub models but did not find matching CE API view code for those route names.
- `rg "pull.?request|PullRequest|pull_request|create.*pr|draft.*pr" apps/api apps/web packages -S` did not find an implemented Plane CE pull-request creation owner, aside from translation and design text noise.
- `plans/2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md:102` says the worker clones the bound remote into a Run-ID path outside the Plane deployment checkout.
- `plans/2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md:103` says Q&A uses a read-only OS boundary.
- `plans/2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md:104` says code work uses a Worktree and bounded Docker sandbox.
- `plans/2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md:115` says OS and Docker restrictions remain active even when a driver has its own approval mode.
- `docker --version` returned Docker version 29.3.0, so Docker is available on the machine.
- `_bmad-output/specs/spec-plane-local-cli-agents/runner.md:17` says v1 ships Docker only for code writes, while Q&A uses an OS sandbox.
- `_bmad-output/specs/spec-plane-local-cli-agents/SPEC.md:61` names Seatbelt and Codex workspace-write as Q&A OS sandbox examples.
- `plans/2026-09-27-local-cli-agents-prd/prd.md:16` and `plans/2026-09-27-local-cli-agents-prd/prd.md:291` require a fresh Run clone per mention.
- `plans/2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md:102` matches that fresh clone rule.
- `plans/2026-09-27-local-cli-agents-architecture/ARCHITECTURE-SPINE.md:180` keeps remote execution deferred.

## Findings

### F1: Four-driver contract is not proven

The spine says all four drivers have a common interaction contract.
The evidence supports that the CLIs exist and each has some useful control surface.
It does not prove all required controls across all four Harnesses.

Claude Code and Codex have the strongest proof.
Claude has official streaming JSON, streaming input, resume, and permission prompt support.
Codex has local CLI support, JSONL exec output, sandbox modes, resume, queue, and app-server approval APIs.

Grok and Omp have local help and some official product docs.
That evidence does not prove the exact Plane driver needs for model discovery, native midturn input, permission response mapping, event identity, and cancellation semantics.
Grok also uses `grok-code-fast-1` only as an alias after its May 15, 2026 retirement, so any spine or epic that treats that as the primary current model name will be stale.

Recommended change: keep AD-4, but mark each driver capability as probed or unknown per Harness.
Do not state or imply that four complete native transports are already verified.

### F2: Plane API ASGI is verified, with one code hygiene caveat

The production API entrypoint runs `plane.asgi:application` through Gunicorn with Uvicorn workers.
The settings also define `ASGI_APPLICATION`.
The ASGI statement is supported.

The ASGI file has a known hygiene issue: it calls `get_asgi_application()` before setting `DJANGO_SETTINGS_MODULE`, then calls it again.
The existing migration plan already calls this a pre-existing latent bug.
This does not disprove that production serves ASGI, but it should not be copied into new architecture text as a clean pattern.

### F3: GitHub repository binding exists, but AD-9 overstates current CE ownership

Current Plane code supports GitHub repository identity and project repository sync data.
That supports part of AD-9.

The current CE tree did not show the matching API view for `github-repository-sync` or a pull-request creation path.
The spine says pull request creation uses the Plane integration and records draft PR identity on the Run.
That is architecture for the new feature, not a verified current capability.

Recommended change: say Plane API must become the owner for Agent repository binding and draft PR records.
Avoid wording that suggests CE already owns draft PR creation for this feature.

### F4: Sandbox is directionally aligned, but enforcement is not fully specified

Docker is installed.
The product sources require Docker for code writes and an OS sandbox for Q&A.
The spine correctly keeps Plane permission records separate from driver prompts and says OS and Docker limits remain active.

The unverified part is the OS boundary for Q&A across all four Harnesses.
The source spec names Seatbelt and Codex workspace-write, but that only directly fits macOS and Codex.
The spine does not say how Claude Code, Grok, and Omp get a read-only OS boundary without ACP.
It also does not specify Docker mount mode, network policy, credential exposure, or path allow-list rules for the code sandbox.

Recommended change: add an implementation note that Q&A sandbox strategy is per Harness and per OS.
Add acceptance tests for read-only clone writes, path escape attempts, and network escalation before calling AD-8 verified.

### F5: Fresh clone, no ACP, and no remote execution are preserved

The spine matches the accepted constraints.
Each mention gets a fresh Run clone.
ACP is not named as the architecture direction.
Remote execution is explicitly deferred.

No change is needed for those constraints.

## Gaps

- No probe output proves `model discovery` for Claude Code, Codex CLI, Grok CLI, and Omp as one consistent driver API.
- No probe output proves `native midturn input` for all four Harnesses.
- No probe output proves `permission response` mapping for Grok CLI and Omp.
- No probe output proves event stream schemas and stable event IDs for Grok CLI and Omp.
- No local code exists yet for Agent Run tables, event logs, leases, Worker API commands, or sandbox launch policy.
- No local code was found for draft PR creation in Plane CE.
- No E2E or smoke test was run because this review was read-only and the feature is still architecture.

## Risks

- If AD-4 remains worded as verified, implementation can expose controls that only work for Claude or Codex.
- If `grok-code-fast-1` is copied from mock data, model selection can show a stale primary slug after the May 15, 2026 xAI migration.
- If AD-9 assumes current CE already owns draft PR creation, epics can miss new backend work.
- If AD-8 stays high-level, the Worker can accidentally trust driver approval modes instead of hard OS and Docker limits.

