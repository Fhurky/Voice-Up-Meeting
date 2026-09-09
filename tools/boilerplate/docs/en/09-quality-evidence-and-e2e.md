# Quality, evidence and E2E

## Core principle

A capability's status comes from observed and recorded checks, not the agent's wording. “Code was
written,” “a test was written,” and “the test was executed and passed” are three different states.

## Local quality gate

`scripts/quality-gate.sh` is the approved entry point:

- `backend`: static/backend checks and read-only migration validation; narrower than the live test
  database flow;
- `frontend`: profile-native frontend checks;
- `all`: backend + frontend + a live unique PostgreSQL test database, migration/drift and shared
  policy checks;
- `--include-browser`: add E2E scenarios using the admitted offline browser bundle.

The gate emits stable `KT_GATE_SCOPE`, `KT_GATE_STEP` and `KT_GATE_TESTS` lines. Machine evidence is
constructed from these lines; normal stdout remains for human inspection.

## Evidence provenance

| Provenance | Meaning |
|---|---|
| `local-executed` | The CLI locally ran a project script whose trust was explicitly confirmed |
| `runner-attested` | An approved runner completed the prepare/finalize challenge contract |
| `client-reported` | The client reported a result; not as strong as independent execution |
| `unrecorded` | No execution evidence exists |

Exit code 0 alone is insufficient. Expected steps must start and finish as `passed`; test counts,
skips/failures and challenge integrity are also validated.

## Browser evidence

`kt-scaffold scenario` creates a file with acceptance comments and a deliberate failing guard. L2
requires:

1. a real user role and permission boundary;
2. a browser triggering behavior through the real UI;
3. executable assertions for the outcome and material error/empty/loading states;
4. a scenario matching its acceptance point in `e2e/QUALITY_MANIFEST.md`;
5. offline execution with the admitted Playwright/Chromium bundle.

A scenario that only calls an API or logs acceptance prose is not browser evidence.

## Delivery report

~~~sh
kt-scaffold done --target-dir . \
  --change-summary "Deliver accepted capability" \
  --claimed-tier L2
~~~

The report should present the change, supported/claimed tier, observed test counts and provenance
together. If a check could not run, state why and which claim is therefore unavailable.

The boilerplate's own regression suite does not replace the generated project's quality gate. They
validate different products.
