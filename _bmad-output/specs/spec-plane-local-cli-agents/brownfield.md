# Brownfield: this Plane CE repo

- This repository is Plane Community Edition. Paid Agents (OAuth app, Enable App Mentions, Agent Run APIs/UI) are **not** present as a product to enable. v1 **adds** mentionable bot users, Agent Run records/activities, and the card+panel UI here; it does not clone `plane-ee`.
- Mention picker today is human users (`user_mention`). v1 must add the two bot identities to that picker.
- Stack on the Mini already includes Docker Compose for Plane. Code-job isolation reuses Docker; it does not replace the Plane stack.
- Tailscale Serve already publishes Plane to the tailnet. Worker must not require a new public hostname.
- Existing work-item Activity log (status, assignee, comments) stays for humans/system events. Agent tool traces are a separate Agent Run surface.
