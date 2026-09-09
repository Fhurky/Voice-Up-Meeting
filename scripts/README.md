# Scripts

Use these entry points instead of ad-hoc commands. They pin the scaffold version, local stack,
profile-native migrations, generated contracts, chart policy and quality sequence. `e2e.sh` is the
fail-closed browser entry point; it defaults to the admitted offline bundle named by
`KT_SCAFFOLD_OFFLINE_BUNDLE` and requires the out-of-band admission digest in
`KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256`. Run `python3 scripts/check-config-sync.py` to prove the resolved
fixed profile's typed settings, `.env.example`, local Compose environment and the chart's single
pre-created `existingSecret` boundary remain synchronized.

`check-dependency-admission.py` reconstructs the normalized direct dependency, OCI and workflow
action inventory without network access and compares it with `dependency-admission.json`. A pin
change therefore fails bootstrap, the local quality gate and CI until its maturity/security
evidence is reviewed. `security-gate.sh` additionally verifies the bank-admitted scanner snapshot
as a closed, symlink-free inventory before it runs Gitleaks, Semgrep and offline Trivy. Trivy scans
runtime and development dependency locks, secrets and IaC misconfiguration; the migration chart is
rendered separately with its committed values and a valid synthetic revision so required-value
validation cannot silently remove it from the scan.

`compile-dependency-locks.sh` runs the pinned `pip-tools` inside the profile's Python 3.13 backend
container and regenerates both hash locks from the exact direct authorities. It deliberately checks
and prints the candidate inventory without admitting it. Governance then records the new digest and
release/exception evidence and runs the complete quality and security gates before merge.

`verify-offline-bundle.sh` is the CI/build admission boundary. It validates those two bank-managed
values, every sealed artifact and the host platform, then fails before a build if the Python
wheelhouses, npm cache, Playwright browser tree or runtime image archive is absent.

`check-governance-drift.py` verifies the content-addressed corpus and every generated client
projection without requiring a local generator installation. `render-clients.sh --check` uses that
verifier; write mode is a local-agent operation or uses the optional installed CLI.
`export-project-metadata.py` emits only the bounded `.kt-scaffold/project-manifest.json` accepted by
the governance MCP. It never walks the workspace or includes source, secrets, dependency state or
database data.

`quality-gate.sh all` creates a unique profile-specific PostgreSQL database ending in `_test`,
deploys the committed migration history, enables the live integration suite, proves desired-state
drift, and drops the database on every exit path. It never migrates the configured application
database. `quality-gate.sh backend` is deliberately narrower: it skips live PostgreSQL tests and
performs only read-only migration validation against the configured database. Stable
`KT_GATE_SCOPE`, `KT_GATE_STEP`, and `KT_GATE_TESTS` lines are the machine evidence consumed by the
scaffold operation; ordinary tool output remains for people.

The full gate's chart-policy step runs the repository-owned renderer with the exact Python
interpreter behind `kt-scaffold`; keep that admitted CLI version on `PATH` together with Helm.
If it is absent, `render-charts.sh` fails with an explicit toolchain error before rendering.
