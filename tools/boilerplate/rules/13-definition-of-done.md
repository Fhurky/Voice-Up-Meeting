---
id: "13-definition-of-done"
title: "Claim only the evidence tier that was actually reached"
scope: process
authority: mandatory
priority: 40
trigger: always
applies_to: []
gate: "done_report"
---

# Evidence-tiered definition of done

Evidence tiers are cumulative:

- **L0 — Written:** the required code, configuration, schema authority, migration, specification, or
  documentation exists and has been reviewed for internal consistency.
- **L1 — Automated:** applicable format, lint, type, unit, integration, contract, generated-artifact,
  and render gates passed.
- **L2 — Live:** the behavior was exercised against the running stack over real HTTP or a real browser
  and its acceptance points were observed.
- **L3 — Owner accepted:** the owner accepted the behavior using representative real data in the
  intended environment.

State the highest tier actually observed. Never infer a pass from code inspection, convert a skipped
step into a pass, or silently lower the claim to match available evidence. `done_report` is advisory:
it may return success when a claim is unsupported, but it must list the missing evidence and carry the
gap into the hand-off report.

“Done” also means all layers required by the accepted PRD landed together and generated contracts are
current. Name every test, live flow, worker, migration, chart, or environment check that could not be
run and the reason. An honest L1 is valid; an unrun L2 claim is not.
