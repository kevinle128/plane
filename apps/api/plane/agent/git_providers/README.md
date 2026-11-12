# Git providers for local CLI agents

A workspace connects GitHub, a self-hosted GitLab, or both. Every provider request goes through
`http.py` (`pinned_fetch`: one DNS resolution, pinned IP, no redirect, no proxy, 1 MiB body cap).
Tokens are stored encrypted and are never returned by the API or written to logs.

## GitHub App (instance operator)

1. Register a GitHub App and turn on **Enable Device Flow**. Without it, the connect action returns
   `device_flow_disabled`.
2. Give the App the repository permissions that agents need (contents, pull requests).
3. Enter the App client ID, client secret and slug in the instance admin (Authentication → GitHub →
   "GitHub App for local agents"). When a value is empty there, Plane reads the environment variable
   of the same name: `GITHUB_APP_CLIENT_ID`, `GITHUB_APP_CLIENT_SECRET`, `GITHUB_APP_SLUG`. These keys
   are separate from the GitHub login keys.

A workspace admin then connects GitHub from Workspace settings → Integrations → GitHub, installs the
App on an organisation with "Connect organisation", refreshes the list, and attaches the
installations that the workspace may use. Sync never attaches an installation.

## Self-hosted GitLab (workspace admin)

- GitLab 15.5 or later.
- A Group Access Token with role Developer or higher and scopes `api` and `write_repository`.
  A personal token is accepted with a warning: pushes and merge requests then appear as that person.
- The https base URL (a path is allowed), the group full path and, when the certificate is not
  publicly trusted, the CA bundle (PEM, 256 KB at most). The bundle applies to that GitLab only.
- Disconnect does not revoke the token. Revoke it in GitLab: group Settings → Access tokens.

## Private networks (instance operator)

A GitLab URL that resolves to a private, loopback or link-local address is refused with
`gitlab_url_not_allowed_or_unresolved`. To allow one, set the operator allowlists. They use the same
format as `WEBHOOK_ALLOWED_HOSTS` and `WEBHOOK_ALLOWED_IPS`:

```bash
AGENT_GIT_ALLOWED_HOSTS="gitlab.internal.example"
AGENT_GIT_ALLOWED_IPS="10.20.0.0/16"
```

A workspace admin cannot change these values. The Plane host itself and the domains in
`WEBHOOK_DISALLOWED_DOMAINS` are always refused.
