# Local infrastructure

The local stack is PostgreSQL, Redis, the selected backend, the shared frontend and one same-origin
reverse proxy. The application/data runtime network is marked internal so those services cannot
reach the internet. Docker Desktop cannot publish a port from an internal-only bridge, so only nginx
(and optional Grafana) also joins a host-facing edge bridge. Its port is loopback-only, DNS is
disabled, and its configuration contains no outbound upstream; the bank host firewall remains the
enclosing egress control. Observability, when selected, otherwise remains inside the internal
network.

All third-party images are digest-pinned and use `pull_policy: never`; load them from the reviewed
offline bundle before starting the stack. Published ports bind only to loopback. The optional
collector exports exclusively to the local Tempo, Prometheus, and Loki services, with a locally
provisioned Grafana dashboard. Set `GRAFANA_ADMIN_PASSWORD` in the gitignored `.env` before enabling
that compose layer; anonymous access, update checks, analytics, Gravatar, and plugin downloads are
disabled.

Every runtime/base image reference is an environment override whose committed default remains
digest-pinned. A bank deployment changes only the repository prefix to its promoted internal image;
the digest remains the reviewed identity. `DEPENDENCY_MODE=offline` plus absolute
`PYTHON_WHEELHOUSE_CONTEXT` and `NPM_CACHE_CONTEXT` paths wire the verified bundle into BuildKit.
Offline Python and frontend builds use only those admitted dependencies. Connected mode still uses
only bank-managed package mirrors supplied through controlled environment configuration.
Generated offline CI requires absolute `KT_SCAFFOLD_OFFLINE_BUNDLE` and the separately distributed
`KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256` admission digest, verifies them before loading images, and then
sets all named contexts explicitly; it never falls back to connected dependency resolution.

Loki and Tempo remain non-root while retaining data across restarts. Their named volumes mount at
`/loki` and `/var/tempo`, directories the pinned images already own as UID/GID 10001, so Docker's
fresh-volume copy-up preserves the correct owner without a root initializer. Both services declare
that identity explicitly, use a read-only root filesystem, drop every capability and enable
`no-new-privileges`; only their admitted state volumes are writable.
An older local volume previously mounted at the legacy temporary paths keeps its existing owner;
automation never deletes it. Preserve any needed data through an operator-approved
export/recreate/import before adopting these mount points.

Use scripts/stack.sh; it keeps the compose project name and file selection consistent.
