# PRD — Observed quality evidence and completion

Status: Draft

Document version: 0.1.0

Domain: [Delivery Assurance](../../DOMAIN.md)

Roadmap: [Capability 001](../../roadmap.md)

## Intent

Turn executed generated-project checks into bounded, provenance-aware evidence and completion reports so
developers, agents, runners, and reviewers cannot promote “written,” “reported,” and “observed passing”
states into one another.

This retrospective Draft records an existing quality-gate protocol and reporting implementation. It
does not accept current evidence, certify generated applications, or allow automated L3 approval.

## Actors and outcomes

- A developer can run one canonical gate and see which fixed-profile step or test failed.
- A coding agent can report observed results without upgrading its own statement into trusted evidence.
- A CI runner can execute a content-bound prepared command and return results tied to the intended
  project metadata and gate script.
- An evidence reviewer can compare scope, provenance, counts, failures, skipped work, and claimed tier.
- A product owner retains explicit authority for representative-data L3 acceptance.

## Verified baseline and gap

Generated projects contain a `quality-gate.sh` entry point with backend, frontend, all, and optional
browser scopes. The gate emits stable scope, step, and test markers. CLI operations verify the managed
gate-script digest, prepare a challenge tied to project metadata and command, optionally execute trusted
project code with an allow-listed environment, parse bounded output, write evidence JSON, and create a
localized report skeleton. Evidence provenance distinguishes local-executed, runner-attested,
client-reported, and unrecorded results. Completion reporting refuses to support a claimed tier above
observed evidence while preserving the user's claim and open gaps.

The gaps are an accepted runner attestation/signature contract, tamper-resistant evidence storage,
formal L3 owner workflow, stable retention and privacy policy, and fresh evidence that the current full
generated-project gate and browser bundle pass on every supported platform matrix.

## Decisions, invariants, and trust boundaries

1. Written change, test code, test execution, and passing observed behavior are distinct states.
2. Exit code zero is necessary but insufficient; required marker sequence, step status, test counts,
   failures, skipped work, and protocol integrity are also validated.
3. Only `scope=all` may establish L1 for the project; partial scopes remain diagnostic L0 evidence.
4. L2 additionally requires at least one real browser scenario through the live application boundary.
5. L3 is product-owner acceptance with representative data and is never emitted automatically.
6. Provenance is explicit and never upgraded: client-reported is not runner-attested or local-executed.
7. Running project-owned code requires explicit trust and a content-bound canonical script path.
8. The MCP governance plane does not execute or finalize project quality evidence.
9. Generator repository tests and generated application tests are evidence for different products.
10. A completion report advises and exposes unsupported claims; it does not rewrite history silently.

## Functional requirements

1. The managed gate must expose backend, frontend, all, and optional browser behavior through one
   documented interface.
2. Gate output must use versioned, stable, ASCII-safe scope, step, and test markers with strict field and
   value grammar.
3. The complete gate must run fixed-profile formatting, lint, type, unit/integration, migration/drift,
   contract/type sync, frontend, governance, dependency, security, chart, and selected browser checks in
   deterministic fail-fast order.
4. Full-gate database behavior must create a uniquely named disposable `_test` database, apply real
   migrations, run integration checks, and remove it through cleanup even on failure.
5. Browser execution must use admitted Playwright/Chromium content and fail when a scenario retains its
   generated guard or lacks executable assertions.
6. Prepare must bind project-metadata digest, managed gate digest, scope, browser flag, and command into a
   challenge.
7. Finalize must reject malformed/tampered challenges, oversized output, invalid markers, missing steps,
   inconsistent scope, and unsupported provenance.
8. Direct execution must require explicit consent, reject a missing/symlinked/drifted gate script, invoke
   its canonical path, and pass only allow-listed environment names/prefixes.
9. Evidence JSON must record reached tier, scope, browser status, command, counts, step/test results,
   protocol errors, provenance, and challenge without secrets or unbounded raw logs.
10. Completion reporting must compare claimed and supported tier, retain the claim, enumerate missing
    evidence and defects, and produce stable localized structure.
11. Skipped tests and unavailable real boundaries must lower or block the relevant claim and remain
    visible.
12. Evidence schemas and marker protocol must be versioned for backward-compatible runner integration.

## Security and authorization

- Local execution occurs only after explicit trust in the target and content-bound script verification.
- Ambient workstation secrets are excluded; only reviewed safe names and project-specific prefixes may
  enter execution.
- Runner attestation requires authenticated runner identity, challenge binding, result integrity, and
  replay prevention before it can be stronger than client-reported evidence.
- Raw gate output, screenshots, traces, and reports must be classified, bounded, redacted, and retained
  under an approved policy.
- Evidence files grant no deployment or product acceptance authority by themselves.

## Data and migration

- Marker and evidence schema versions are durable machine contracts.
- Evidence records contain no credentials, token values, full environment, database contents, or source
  snapshot.
- Tamper-resistant production retention, signature, deletion, and access policy remain external design
  decisions.
- Old evidence is tied to exact generator, project, dependency, model/client where relevant, environment,
  and date; later changes must identify what was re-run.

## Validation and observability

- Parser tests cover malformed, duplicated, missing, out-of-order, oversized, inconsistent, skipped,
  failed, and successful marker streams.
- Tier tests cover every scope/provenance/browser combination and prove no partial or prose-only path
  reaches L1/L2.
- Execution tests cover explicit trust, gate digest drift, symlinks, environment filtering, database
  cleanup, failure exit, and timeout/cancellation.
- Report tests cover stable sections/groups, localization, counts derived from evidence, unsupported
  claims, defect/open-item numbering, and unrecorded behavior.
- Operational telemetry records gate duration/status and runner identity without source or secret content.

## Risks and open questions

- Which cryptographic or platform attestation makes a runner result independently trustworthy?
- Where is evidence retained immutably, for how long, and under whose access/deletion authority?
- What UI or review workflow records product-owner L3 acceptance?
- How are flaky, quarantined, retried, or conditionally skipped tests reflected in tier decisions?
- Which live database, browser, model, telemetry, and cluster boundaries are mandatory by capability type?

## Acceptance criteria

- [ ] Quality, security, CI, and product owners accept tier, provenance, retention, and L3 semantics.
- [ ] Marker/evidence schemas reject malformed, missing, duplicated, inconsistent, or oversized data.
- [ ] Partial gates never exceed L0; complete non-browser gates may reach L1; real browser evidence is
  required for L2; no automation emits L3.
- [ ] Direct execution requires explicit trust, a matching managed digest, canonical path, and filtered
  environment.
- [ ] Prepare/finalize rejects challenge tampering, replay outside policy, and mismatched project/gate
  identity.
- [ ] The full gate owns and cleans a disposable PostgreSQL `_test` database and executes real migration
  history.
- [ ] Generated browser guards, missing browser bundle, skipped/failing assertions, and API-only scenarios
  block L2.
- [ ] Completion reports preserve unsupported claims, state supported tier/provenance, and enumerate every
  missing or defective item.
- [ ] A fresh generated project passes the complete offline gate and browser scenario with observed counts
  for an admitted platform tuple.
- [ ] Runner-attested evidence includes independently verified runner identity and result integrity before
  promotion.

## Delivery flow

Draft -> quality/security/product review -> Accepted -> protocol/schema reconciliation -> parser and
execution tests -> real generated-project L1/L2 evidence -> runner attestation -> owner L3 workflow
