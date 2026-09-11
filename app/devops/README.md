# Deployment contract

These self-contained charts target an egress-denied, Rancher-managed Kubernetes namespace. They
render no Secret and no cluster-scoped resource. Administrators create referenced Secrets before
installation. Images come only from the internal registry and are selected by immutable digest.
The backend `existingSecret` must provide the resolved fixed profile's prefixed runtime keys; use
`app/backend/.env.example` as the key inventory and `python3 scripts/check-config-sync.py` as the
machine check. In particular, `VOICEUP_JWT_SECRET` has no application fallback: a missing key
stops startup instead of enabling a known signing secret.

The overlay's `inference.runtimeProfile` explicitly selects the inference CUDA
runtime: `x86_64-cu128` is the default; the separate ARM64 pilot image requires
`aarch64-cu129`. `inference.meetingEnabled` defaults to `false`. The chart emits
both existing typed settings explicitly, so a value in the referenced Secret
cannot silently enable meeting models or change the chosen runtime. The single
pre-created `existingSecret` still provides the inference key through `envFrom`;
no per-key Secret mapping or new Secret is generated. The backend configuration
sync check covers its own typed settings; inference-specific render checks prove
these additional workload values against `voiceup_inference.config.Settings`.

Meeting inference can be enabled only with `x86_64-cu128` and an explicitly
promoted internal-registry digest built from the admitted offline
`app/inference/Dockerfile.meeting`. The Pod selects Linux/AMD64 and requests one
NVIDIA GPU. ARM64 meeting activation is rejected; ARM64 source availability and
local RTX 4060 evidence do not certify a native Spark or Kubernetes deployment.
All real environment placeholders remain unresolved until the operator supplies
the corresponding deployment facts; fixture image digests are not deployable images.

The enabled variant declares a separate 4 GiB `meeting-models` PVC. Offline
artifact preparation must put the exact Community-1 package contents in its
`diarization/` subdirectory and the exact Whisper large-v3 package contents in
`asr/`. Both subdirectories are mounted read-only at `/models/diarization` and
`/models/asr`; the existing `/models/speaker` PVC stays unchanged. Include all
manifest-listed license/readme files and no extra files inside either model
directory. The immutable manifests are already part of the meeting image. The
chart does not download or populate weights and has no provisioning init
container; missing or mismatched packages keep the workload unready.

In meeting mode, startup and readiness use `/meeting-ready`; liveness uses
`/live`. In pilot mode, the existing `/live` startup and `/ready` readiness remain.
These GET checks need no inference key and stay within the private service
boundary. The pilot's 50 MiB/120-second settings remain unchanged: meeting chunk
and memory requests already have their own bounded endpoint contracts. Both
variants preserve the non-root/read-only security context, bounded `/tmp`, GPU
resources, ClusterIP, worker-only ingress and denied egress. Render evidence is
L1; actual model-PVC provisioning and cluster execution require separate live evidence.

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
