# Delivery Assurance domain

Status: Draft

## Purpose

Delivery Assurance owns how a generated repository turns executed checks into bounded evidence and how
approved software artifacts are admitted, sealed, transported, and consumed without runtime internet
fallback.

## Actors

- Developer — runs the appropriate local gate and sees actionable failure evidence.
- CI runner — executes a content-bound challenge and returns attributable results.
- Evidence reviewer — evaluates observed tiers and provenance without trusting prose or exit code alone.
- Artifact factory operator — assembles platform-native offline bundles from reviewed authorities.
- Security reviewer — admits dependency, image, browser, action, and scanner inventories by digest.

## Ubiquitous language

- **Evidence tier** — L0 written, L1 full local/integration, L2 live browser, or L3 owner acceptance.
- **Provenance** — `local-executed`, `runner-attested`, `client-reported`, or `unrecorded` origin.
- **Gate marker protocol** — stable machine-readable scope, step, and test records emitted by a gate.
- **Admission ledger** — reviewed normalized inventory and digest for dependencies and executable inputs.
- **Offline bundle** — closed, checksum-sealed, platform-specific artifact set consumed without fallback.
- **Out-of-band trust anchor** — bundle inventory digest distributed separately from bundle content.

## Invariants

1. Exit code zero or an agent success statement alone never establishes an evidence tier.
2. Only the complete project gate can establish L1; L2 additionally requires real browser assertions.
3. Provenance is recorded and never silently upgraded.
4. Package managers, image builds, browser execution, and scanners fail closed when admitted material is
   missing or mismatched.
5. Native artifacts are assembled on their declared target platform and bound by content digest.
6. Runtime or CI has no implicit public-network fallback.

## Owned data and artifacts

- Gate marker, evidence JSON, prepare/finalize challenge, report, and completion semantics.
- Dependency authority inventory, compatibility evidence, exceptions, and admission digest.
- Offline wheelhouse, npm cache, browser, image, scanner, and verification contracts.

## Upstream boundaries

- Capability acceptance criteria and generated project gate scripts.
- Technology Governance version and maintenance decisions.
- Organization-controlled mirrors, registries, scanner data, and trust-anchor distribution.

## Downstream boundaries

- Capability completion reports and owner acceptance review.
- Project Factory package/OCI provisioning and Application Foundation builds.
- CI and deployment admission decisions.

## Explicit non-responsibilities

- Accepting product behavior or granting L3 automatically.
- Operating public mirrors, registries, PKI, or organization-wide promotion systems.
- Treating the generator repository test suite as evidence for a generated product capability.
