# Offline CI runner contract

These workflows run only on egress-blocked, self-hosted Linux runners. The runner labels are a
security boundary, not scheduling decoration: `bank-offline` means public package indexes,
registries and software-as-a-service endpoints are unreachable.

The repository variable `KT_SCAFFOLD_CI_BUNDLE` must name a read-only, platform-matched bundle
created by `packaging/offline-bundle.sh` and admitted through the bank's software-supply-chain
controls. Every job verifies `SHA256SUMS` before consuming it. The runner provides Python 3.13,
Node.js 22, Docker with BuildKit/Compose, and the immutable checkout action already mirrored
inside the internal forge. Runner admission allows trusted same-repository pull requests only;
fork-originated pull requests never execute on these hosts. Runners are disposable and workflows
never upload source or test artifacts to a public service.

`package-test.yml` verifies dependency admission, runs the bank-admitted offline security
toolchain, validates the generator, builds its wheel and inspects the archive. Its
`security-toolchain` runner label means Gitleaks, Semgrep and Trivy are available without egress.
The scanner snapshot has its own out-of-band `SHA256SUMS` digest and admission date; jobs reject a
replacement checksum list or a snapshot older than seven days.
Its manifest is a closed inventory: unlisted files, missing files, unsafe paths and symlinks fail
before Semgrep or Trivy can consume them.
The two jobs in `scaffold-matrix.yml` independently render the fixed Python/FastAPI profile: the
first performs
determinism, governance, chart, contract and static gates; the second loads the admitted OCI images
and runs the complete database-backed generated-project quality gate with dependency resolution
forced offline. That full gate points `PLAYWRIGHT_BROWSERS_PATH` at the verified bundle and invokes
`scripts/quality-gate.sh all --include-browser`; missing or mismatched Chromium is a failed L2 gate,
never a skipped success.
