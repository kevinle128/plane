# Self-hosted GitLab: scope decisions (2026-11-12)

The user added self-hosted GitLab to the scope on 2026-11-12 and accepted all recommended answers. The restored spec, epics and mockup cover GitHub only. These decisions extend them.

1. Parity with GitHub: connect, bind one repository to a project, Code jobs deliver a **draft Merge Request**, and Run conclusions mirror to the MR. The agent never pushes or merges to the default branch.
2. Order: Phase 1 builds a provider-neutral data model (connection, repository, binding, policies). GitHub and GitLab both ship in Phase 1. Later phases use the neutral model, so the Worker and Run code do not depend on one provider.
3. Authentication: a workspace admin pastes a **GitLab Group Access Token**. GitLab creates a bot user for the token, which acts like the GitHub App identity. Plane verifies the token scopes and expiry when the admin connects, and stores the token encrypted.
4. Instance facts are unknown (the user did not give the GitLab version, the CA setup or the network path). The plan must:
   - read the GitLab version from `/api/v4/version` when the admin connects, and reject versions below a stated minimum with a clear message;
   - accept an optional custom CA bundle for the GitLab URL, for both the Plane API and the Worker;
   - show a clear connection-failed reason when the Plane API or the Worker cannot reach the GitLab URL.
5. One workspace can connect GitHub and GitLab at the same time. Each workspace stores its own GitLab base URL. Each project binds one repository from either provider.
6. UI: reuse the GitHub screens from the mockup. Change only the provider name, the icon and the terms ("Merge Request" instead of "Pull Request"). There is no new design.

## Target instance (checked 2026-11-12)

- URL: `https://git.oceanlabs.dev/`. It is reachable from the development machine (HTTP 200 on the sign-in page).
- Edition: GitLab Enterprise Edition (from the sign-in page). Group Access Tokens are available on this edition.
- TLS: a public Let's Encrypt certificate that validates without a custom CA. The optional custom CA bundle stays in scope for other instances.
- Version: unknown. `/api/v4/version` needs authentication (it returns 401 without a token). Read the version with a token during Phase 1.

Open fact to confirm during Phase 1: the GitLab version, read with a test token. The user gives the test token through the secret store, never in chat.
