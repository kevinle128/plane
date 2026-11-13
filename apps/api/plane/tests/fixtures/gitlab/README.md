# GitLab API fixtures

These JSON bodies are **shaped from the GitLab API documentation** (v15.5.0-ee and master) and the
fields read on git.oceanlabs.dev (18.10.3-ee) on 2026-11-12. They were not recorded in this session:
the only available token is a personal token with scope `api`, and the session could not read it.

Re-record them from a GitLab instance with a Group Access Token before the Phase 7 live write check,
and scrub tokens, e-mail addresses and `last_used_ips` before committing.

`version_insufficient_scope.json` is the 403 body GitLab returns for a token without `api`,
`read_api`, `read_user`, `ai_features` or `ai_workflows`. Record it with a `write_repository`-only token.

`group_projects_page2.json` contains one project on another host (`other.example.net`); the catalog
must skip it.
