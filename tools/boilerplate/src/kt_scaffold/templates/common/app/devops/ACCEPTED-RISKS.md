# Accepted risks

| Risk | Why accepted | Compensating control | Re-evaluation trigger | Owner |
|---|---|---|---|---|
| Trivy KSV-0125 does not recognize the project-specific bank registry as trusted | The approved registry hostname is an environment fact and cannot be hard-coded into a reusable chart | `render_charts.py` rejects public or out-of-scope registries and requires immutable image digests | Registry admission or overlay validation changes | Platform Security |
| Trivy KSV-0110 reports workloads in the default namespace | Helm release namespace is supplied by the deployment environment so the same chart remains portable across admitted namespaces | Release automation supplies the namespace; charts create no `Namespace` or cluster-scoped resources | Deployment ownership or namespace strategy changes | Platform Engineering |
| Trivy KSV-0020/KSV-0021 report vendor UIDs/GIDs below 10001 | Nginx, PostgreSQL, Redis and Grafana images require their reviewed non-root runtime identities | `runAsNonRoot`, read-only root filesystems, dropped capabilities, seccomp and bounded writable volumes remain mandatory | A base image or runtime identity changes | Platform Security |
| Trivy DS-0026 reports no Dockerfile `HEALTHCHECK` on development and one-shot images | Runtime health is defined by Compose/Kubernetes probes; the generator image is a terminating CLI process | Compose healthchecks and Kubernetes readiness/liveness probes are contract-tested | A long-running image is introduced without an external probe | Platform Engineering |
