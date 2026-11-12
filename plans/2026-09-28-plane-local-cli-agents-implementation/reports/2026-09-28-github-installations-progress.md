# GitHub installations progress

Stories 1.1–1.4 are in progress.
Plane now stores installation grants by workspace, validates organization additions against the connected user's GitHub App token, removes one grant at a time, and supports workspace disconnect with token revocation.
An initial installation-list failure stays visible and has a retry action.

## Evidence

- Seven focused API tests pass in the isolated Docker Compose stack.
- The web typecheck, targeted lint, and targeted format checks pass.
- The migration model check reports no changes after the new installation table and connection error field.
- A test database schema rebuild was required because this repository reuses its pytest database and disables migrations during tests.

## Remaining work

- The repository picker must filter repositories by both workspace grant and current member access.
- Project repository bindings must retain identity after a grant or connection is removed, while new Runs reject unavailable bindings.
- The GitHub settings UI needs a live browser review for desktop, mobile, keyboard, and screen reader use.
- A real GitHub App must be configured to verify device authorization, organization installation, and revocation against GitHub.
- Keep the sprint status unchanged until each story's complete acceptance criteria are verified.
