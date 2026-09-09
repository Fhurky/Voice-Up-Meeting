# PRD — Offline artifact and dependency admission

Status: Draft

Document version: 0.1.0

Domain: [Delivery Assurance](../../DOMAIN.md)

Roadmap: [Capability 002](../../roadmap.md)

## Intent

Enable `kt-scaffold` and generated projects to install, build, test, scan, and run in an egress-blocked
environment using only reviewed, platform-correct, content-addressed artifacts whose complete inventory
is verified against an out-of-band admission digest.

This retrospective Draft records an extensive dependency ledger, locks, packaging script, generated
verification/security gates, and offline CI behavior. It does not claim that an artifact bundle has been
freshly built or admitted for every platform in this change.

## Actors and outcomes

- An artifact factory operator can assemble one sealed platform bundle in an approved connected zone.
- A security/release reviewer can review all direct package, workflow action, image, browser, and scanner
  authorities as one normalized inventory.
- A developer or runner can verify and consume the bundle without network fallback.
- An application team can reproduce the same project baseline and full quality/browser gates in a closed
  environment.
- An auditor can trace every exception and version change to dated release, advisory, license, maturity,
  and compatibility evidence.

## Verified baseline and gap

The repository contains exact Python locks, committed npm lockfiles, image digests, workflow action pins,
a normalized `dependency-admission.json`, Gitleaks configuration, generated Dependabot policy for managed
internal mirrors, closed scanner-snapshot validation, an offline bundle factory, OCI wrapper input, and
generated scripts that verify bundle inventory before bootstrap/build/test. The factory separates
generator and generated-profile wheelhouses, requires hashes before executing downloaded Python build
code, includes npm cache and matching Playwright browser content, and refuses to label artifacts for a
platform different from its native factory platform.

The gaps are a named production artifact authority, signed/out-of-band digest distribution, current
SBOM/provenance and license policy, repeatable admitted bundles for every supported OS/architecture,
continuous vulnerability response and revocation, and a fresh egress-blocked end-to-end run for the
current release.

## Decisions, invariants, and trust boundaries

1. Runtime services, generated CI, and closed developer workflows have no implicit public-network
   fallback.
2. The controlled artifact factory is the only zone that may contact approved package, image, browser,
   action, or scanner sources.
3. Consumers receive bundle content and the expected `SHA256SUMS` digest through separate trusted
   channels.
4. The bundle inventory is closed: missing, extra, symlinked, modified, or wrong-platform content fails.
5. Direct package authorities, OCI digests, workflow actions, browser revision, and scanner data are
   reviewed as one normalized dependency identity.
6. Pin changes invalidate admission and require refreshed evidence; lockfile resolution is not approval.
7. Generator/build Python artifacts use exact hash locks before downloaded code executes.
8. Native wheel, npm optional dependency, browser, and OCI artifacts are assembled on the target platform.
9. Package managers and BuildKit receive explicit offline contexts and cannot fall back to public indexes.
10. Security urgency may override release-age policy with recorded advisories; the policy never requires a
    downgrade.

## Functional requirements

1. The admission ledger must enumerate every direct pyproject, requirements, npm, OCI, workflow action,
   browser, and scanner authority that can influence generation, build, test, scan, or runtime.
2. It must bind normalized inventory to a reviewed digest, decision ID/date, compatibility evidence,
   release maturity, security/advisory evidence, and explicit exceptions.
3. Any authority/pin/lock/image/action change must invalidate the recorded inventory digest until review.
4. The artifact factory must start from an empty output, use a private temporary workspace, and produce a
   closed deterministic inventory and checksums.
5. Platform tuple must include OS, architecture, Python ABI, Node/npm compatibility, browser revision, and
   OCI platform; relabeling a foreign native artifact set is forbidden.
6. Python downloads and build-system installation must use exact reviewed hashes and no implicit source
   build unless separately admitted.
7. Generated Python, npm, Playwright, image, workflow, and scanner consumers must use only absolute
   verified bundle paths or approved private-index mode with an explicit distinct contract.
8. Bundle verification must validate the out-of-band digest, every listed file hash, closed inventory,
   symlink absence, platform metadata, and required artifact categories before consumption.
9. Generated CI must require the admitted bundle/digest, force offline/no-index modes, load sealed images,
   and provide explicit named build contexts.
10. Browser execution must select the matching bundled Chromium tree and fail if missing or incompatible.
11. Scanner execution must verify one closed, checksum-sealed, symlink-free snapshot before running
    Semgrep/Trivy or equivalent approved tools.
12. Release artifacts must exclude credentials, local environment, dependency caches outside inventory,
    VCS state, build debris, and private topology.
13. The offline bundle must carry machine-readable inventory, human review metadata, install/use guidance,
    and revocation identity.
14. Emergency security updates must record advisory IDs, changed artifacts, compatibility scope, and
    required re-execution evidence.

## Security and authorization

- Factory credentials and mirror endpoints remain factory/runtime configuration and never enter the
  portable bundle inventory or generated repositories.
- Artifact admission requires separation between artifact source/build operation and accountable review
  where organization policy requires maker-checker.
- Checksums protect integrity only when their root digest is distributed through a separate authenticated
  channel.
- Symlinks, path traversal, unlisted executable content, mutable tags, public endpoints, and implicit
  install scripts fail closed.
- Vulnerability, license, provenance, and supplier risk review must occur before admission, not after
  closed-environment deployment.

## Data and migration

- Admission decisions are immutable records keyed by normalized inventory digest and platform tuple.
- Updated bundles receive new identities; content is not modified in place after sealing.
- Revocation and replacement must identify affected projects/runners and the evidence that must be rerun.
- Retention and destruction of superseded bundles, scanner data, and signing material belong to the
  organization software-supply-chain policy.

## Validation, observability, and evidence

- L1 covers ledger normalization, digest mismatch, changed pin, missing/extra/symlink files, wrong
  platform, missing hash, public fallback, mutable image/action, incomplete browser, scanner snapshot,
  and release-context secret mutation tests.
- Reproducibility checks compare inventories and content digests for repeated same-source/platform builds,
  with documented exceptions for inherently signed metadata if any.
- L2 runs on an egress-blocked target: verify bundle, install/use generator, create project, build/load
  images, apply migration, run full quality/security/chart gates, and complete the real browser scenario.
- Evidence records source revision, profile/generator version, platform tuple, inventory/root digest,
  builder identity, reviewer, date, exceptions, scan/advisory status, and end-to-end result.

## Risks and open questions

- Which service distributes and authenticates the out-of-band root digest and revocation notices?
- Which OS/architecture tuples are initially supported and how often are bundles refreshed?
- What SBOM, provenance/signature, license, supplier, and vulnerability thresholds are mandatory?
- How are emergency scanner/advisory updates admitted without reopening unrelated artifacts?
- What retention and rollback policy applies after an artifact or signing key is revoked?

## Acceptance criteria

- [ ] Security, release, architecture, and artifact-factory owners accept admission and exception policy.
- [ ] The ledger covers every executable or resolved direct authority and binds one reviewed normalized
  digest.
- [ ] Any authority, lock, image, action, browser, or scanner change invalidates admission before use.
- [ ] Factory builds refuse foreign target relabeling, unreviewed hash locks, existing output merges, and
  unlisted content.
- [ ] Consumers verify the separately distributed root digest, closed inventory, platform, symlinks, and
  every file hash before package/build/test/scan execution.
- [ ] Generated package managers, BuildKit, workflows, browser, and scanners have no public fallback.
- [ ] Negative tests reject mutable/public images, unpinned actions, incomplete/wrong browser content,
  tampered scanner data, and secret-bearing release contexts.
- [ ] Repeated same-source/platform factory builds produce equivalent admitted inventories.
- [ ] A fresh egress-blocked machine completes project creation, build, migration, full gate, security
  scan, chart render, and browser login using only the bundle.
- [ ] Admission records include revocation, replacement, affected-scope, and required revalidation
  semantics.

## Delivery flow

Draft -> supply-chain/security review -> Accepted -> ledger/factory reconciliation -> platform-native
bundle build -> independent admission -> egress-blocked L2 evidence -> distribution -> vulnerability and
revocation monitoring
