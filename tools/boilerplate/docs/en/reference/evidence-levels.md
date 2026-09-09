# Evidence levels

| Level | Minimum evidence | Claim it does not provide |
|---|---|---|
| L0 — Written | The change exists in the diff/files | That it runs or satisfies the requirement |
| L1 — Test observed | Relevant deterministic, unit and integration tests executed and passed, with skips/open failures disclosed | Real-boundary acceptance, conformance or owner approval |
| L2 — Real-boundary observed | L1 + the domain-relevant acceptance scenario on the real boundary | Accountable-owner acceptance or runtime admission |
| L3 — Owner accepted/admitted | L2 + a recorded accountable-owner decision for the exact scope and evidence | Automatic approval of future versions, models, tools, policies or environments |

Evidence always carries command or scenario, environment/version, exit code, observed test counts,
skips/failures, provenance and date. “Agent completed” alone does not move a claim above L0.

An MCP reconciliation receipt is formal evidence of a governance decision, not an execution level.
A client session transcript can aid review but does not replace an independent gate result.

The L2 boundary depends on the capability: a generated web capability uses the real HTTP/browser
stack, Project Factory uses a real local or HTTP MCP session plus independent tree/tool observation,
and Agent Platform uses the exact real client/model/tool/policy/environment tuple. Agent Platform L3
admission is signed, time-bound and revocable; PRD acceptance alone does not admit a runtime tuple.
