# Scripts

For fully local MacBook CPU use, `python3 scripts/setup-local-cpu.py` prepares
the pinned model, architecture-specific wheels, images, database and services.
`sh scripts/start-local-cpu.sh` starts prepared services without builds/downloads.
Both use the existing wrappers; `stack.sh --mode cpu` selects the CPU Compose layer.
`prepare-speaker-model.py` acquires only fixed public model bytes at build time,
verifies them before packaging and preserves an existing package. See the
[Mac guide](../docs/MACOS_SETUP.md) for account setup and observed device evidence.

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

For the accepted remote Spark capability, `inspect-spark.py` reads bounded device
facts without importing model packages. `configure-spark-host.py` is a reviewed
one-time local sudo helper: it adds one dedicated Ethernet profile and appends
the selected non-root user to the existing Docker group. It validates conflicts
before changing anything and preserves other connections. Run it only on the
named Spark interface/address; SSH access alone does not establish an Ethernet route.

`prepare-spark-wheelhouse.py` uses the exact publisher URLs, sizes and SHA-256
digests in `app/inference/spark-wheelhouse-manifest.json`. It never installs
packages or changes admission. Generate the separate offline lock with:

```sh
python3 scripts/prepare-spark-wheelhouse.py \
  --manifest app/inference/spark-wheelhouse-manifest.json \
  --write-lock app/inference/requirements.spark.txt
```

Use `--directory <build-time-wheelhouse>` to download and verify the 48 ARM64
artifacts. An existing identical lock/wheel is reused; a conflicting file is
preserved and rejected. The build consumes these files with `Dockerfile.spark`
and networking disabled. Native package/GPU verification is a separate required
step before switching the application to Spark.

`spark-tunnel.ps1 -Action Start|Stop|Status` manages only the project-owned,
strict-host-key SSH loopback tunnel. Its ignored connection JSON carries explicit
host/user/key/known-host paths and fixed ports. `start-local.ps1 -Mode Spark`
selects the verified remote transport; subsequent Auto invocations and `stack.sh`
use the ignored saved mode. Local mode requires an explicit override once Spark
is selected. See [the runtime guide](../docs/SPARK_RUNTIME.md) for device setup,
restart, failure behavior and the separate private Spark Compose service.

`Start-VoiceUp.cmd` in the repository root is the daily one-click entry point.
It invokes `connect-spark.ps1`: exclusive invocation lock, physical Ethernet check,
local Docker endpoint validation/Desktop startup, SSH-stdin execution of the prepared
`ensure-spark-runtime.py`, owned tunnel recovery, existing application startup and
web/API readiness. `-NoBrowser` suppresses browser opening. The remote helper uses
only the prepared private configuration and verified image; it never installs or
pulls artifacts. No scheduled cable watcher or machine-power controller is installed.

For accepted speaker-pilot evaluation, `prepare-public-speaker-dataset.py --download`
downloads the four pinned LibriSpeech development/test archives from their official
HTTPS source, checks exact sizes and upstream MD5 values, records SHA-256 and
prepares deterministic chapter-separated clips. It preserves conflicting local
files and rejects archive links, device entries and unsafe paths. The two selected
pools contain 140 distinct English speakers and 604 clips; successful model
enrollment and recognition must be measured separately.

`evaluate-public-speakers.py` exercises actual public upload, enrollment,
identification and newcomer-return APIs in an isolated evaluation tenant. Supply
`--manifest`, `--audio-root`, `--credentials`, `--state`, `--output` and
`--gallery-sizes`; use different empty tenants and state/output files for a new
calibration run and the held-out test. Its bounded queue does not change the
serialized model service. Repeating the same bound command resumes accepted jobs
using persistent idempotency keys; it refuses mismatched state or unexpected
gallery changes.

Fifty speakers is the primary quality target, not an application quota. Evaluation
manifests support up to 200 known and 200 unknown speakers within existing file
and operation budgets; a 200-person gallery's newcomer may become profile 201.
Historical deployments can still return explicit HTTP 409 `profile_limit`, which
is retained as a terminal failed evaluation operation without a fabricated job or
latency. The return query and final gallery check continue; resume does not repeat
this rejection. Other 409 errors still stop the runner. Historical reports keep
their original gallery sizes; input-budget support is not model accuracy evidence.

Every selected-candidate command must additionally include:

```text
--policy docs/evidence/2026-09-09-public-speaker-evaluation/selected-policy.json
```

This freezes the expected `0.55` match, `0.45` unknown and `0.10` margin values;
it does not configure the backend. Response policy must match. Omitting `--policy`
deliberately retains historical baseline expectations (`0.75` match threshold).
Raw credentials, audio, detailed results and resume state belong under ignored
`data/` or `outputs/`, not in committed evidence.

`report-public-speakers.py --input <private-results.json> --output <new-summary.json>`
creates an aggregate without audio or person/account/job identities. It retains
planned counts, failed enrollments, quality failures, source-split breakdowns,
timings and descriptive speaker-cluster intervals, and refuses to overwrite an
existing report. The evaluator's `manifest_sha256` is canonical JSON SHA-256;
preparation stdout hashes the manifest's exact bytes. The reporter also hashes
the private source result bytes. Keep these identities distinct.

Add `--metrics-protocol voiceup-open-set-v1 --manifest <matching-manifest.json>`
to produce schema 2 with manifest-validated identity precision/recall/micro F1,
speaker macro F1, unknown-class F1 and the separate 0–100 VoiceUp Score. The score
is the harmonic mean of identity macro F1 and unknown F1, scaled by 100; it is not
standard F1 or accuracy. Failed enrollment candidates remain in planned support;
missing or pending planned work withholds completed scores. The default invocation
retains schema 1. Re-scoring needs no audio, model, credentials or running stack.
See [the metric protocol and worked example](../docs/SPEAKER_METRICS.md).

See [the complete public-data protocol](../docs/PUBLIC_DATASET_PROTOCOL.md) for
copyable PowerShell commands, isolation, provenance and limitations. Diagnostic
score sweeps used for calibration are separate from live application evidence;
this English audiobook protocol does not establish Turkish meeting, mixed-speaker,
long-recording or streaming accuracy.
