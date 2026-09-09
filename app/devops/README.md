# Deployment contract

These self-contained charts target an egress-denied, Rancher-managed Kubernetes namespace. They
render no Secret and no cluster-scoped resource. Administrators create referenced Secrets before
installation. Images come only from the internal registry and are selected by immutable digest.
The backend `existingSecret` must provide the resolved fixed profile's prefixed runtime keys; use
`app/backend/.env.example` as the key inventory and `python3 scripts/check-config-sync.py` as the
machine check. In particular, `VOICEUP_JWT_SECRET` has no application fallback: a missing key
stops startup instead of enabling a known signing secret.

`scripts/render-charts.sh` renders both committed fixture overlays, proves that their resource shape
is identical, and enforces the security/network/runtime-host contract. Real `lab` and `cluster`
overlays are deliberately unresolved until an operator supplies the internal registry, Kubernetes
version, ingress identity, host, StorageClass, Secret names, the full immutable source revision, and
every promoted image digest. The revision is a lowercase full 40- or 64-character source hash; the
migration Job name is derived from it so each promoted revision gets a distinct immutable Job.

Every workload runs non-root with a read-only root filesystem, drops all capabilities, disables the
service-account token, declares resources and probes where applicable, and has a bidirectional
NetworkPolicy. Network peers are pod/namespace selectors only; no chart admits an IP block or
unrestricted egress. A pod with a writable volume declares an `fsGroup` matching `runAsGroup` and
`OnRootMismatch`, so kubelet prepares the volume for that non-root identity without a privileged
initializer. The migration release runs before the dependent backend release.

The optional observability release is a closed five-component stack: collector, Tempo, Prometheus,
Loki, and Grafana. Exporters name only Services rendered by that release. Grafana uses a pre-created
administrator Secret, disables anonymous access and external analytics/update/plugin checks, and
loads its data sources and starter dashboard from ConfigMaps.

Contract fixtures prove chart shape. Real lab/cluster overlays deliberately retain __REQUIRED__
environment facts and fail readiness validation until an operator fills them.

The `.github/workflows` files target only the bank's egress-denied self-hosted runner label. The
pinned `actions/checkout` revision must be mirrored by the internal GitHub Enterprise installation;
the workflows never resolve an action from the public marketplace. Semgrep rules, Trivy databases,
Helm, and all language caches are runner-managed offline inputs.
