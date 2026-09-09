---
id: "54-dependency-currency"
title: "Keep pinned versions current under security findings"
scope: governance
authority: mandatory
priority: 54
trigger: always
applies_to: []
gate: "security-scan.yml"
---

# Dependency and image currency

The technology profile fixes which technologies are used; this rule fixes how their versions move.
Version pins — package manifests, hash-locked requirement files, committed lockfiles and
digest-pinned images — are governance-owned floors, not developer or agent choices.

A finding from an approved security scanner (Trivy, Semgrep, Dependabot, an OSV query, or the
internal ruleset) against a pinned version obliges an upgrade to the nearest fixed release. Security
fixes are adopted immediately and are exempt from the maturity window below.

Adopting a new version for any other reason requires that the release has been publicly available
for at least 30 days. Evidence is recorded with the change: the registry or upstream release date
and, for a security-driven upgrade, the advisory identifier. Downgrading a pin to satisfy the
window is forbidden; an existing newer pin stays until its own successor qualifies. The governance
owner may grant a recorded exception to the maturity window; the exception and its compatibility
evidence travel with the change.

`dependency-admission.json` is the executable record. Its reviewed inventory digest covers every
direct package authority, digest-pinned OCI identity and commit-pinned workflow action. Any
authority change invalidates that digest. When a supported scaffold option changes the emitted
authority surface, the ledger carries a separately reviewed digest for each exact variant and the
checker proves that `.kt-scaffold/answers.yml` agrees with the files present. It never computes and
self-admits a new digest during generation. `scripts/check-dependency-admission.py` fails closed until
governance records the release evidence or an explicit compatibility exception and reviews the new
inventory. Dependabot and OSV findings are proposals or evidence inputs; neither may rewrite or
admit a pin by itself.

Upgrades reach projects through scaffold update replay or the governance update channel. Do not
hand-edit a generated lock or digest to silence a scanner; regenerate it from its authority file so
the manifest, the lock and the admitted artifact hashes stay consistent.
