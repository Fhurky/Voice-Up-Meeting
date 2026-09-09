# PRD — Vendor-neutral agent contract

Status: Accepted

Document version: 1.1.0

Acceptance date: 2026-08-20

Acceptance record: Explicit owner authorization in the project delivery thread

Domain: [Agent Platform](../../DOMAIN.md)

Roadmap: [Capability 001](../../roadmap.md)

## Intent

Define a vendor-neutral, source-owned agent contract and a versioned capability matrix from which
reviewed adapters generate client-specific instructions, skills, commands, custom
agents, hooks, MCP/tool configuration references, and evidence requirements.

This Accepted baseline authorizes implementation of the canonical compiler and four client adapters.
It does not by itself claim completed delivery, real-runtime conformance, production admission, or
certification for any client/model/tool tuple; those states require the evidence gates below.

## Actors and outcomes

- A vibe coder can select an admitted IDE or CLI without changing the agent's mission or governance
  intent.
- An agent author can express responsibilities, capability needs, data limits, delegation, and
  evidence requirements without embedding a vendor, model, endpoint, credential, or executable hook.
- An adapter maintainer can make semantic loss explicit and fail safely when projection is impossible.
- A governance owner can apply progressive friction by risk tier and decide admission using real
  conformance evidence rather than documentation claims.
- A reviewer can trace each support and governance claim to a versioned source, enforcement point,
  test result, artifact digest, owner, date, and residual risk.

## Verified baseline and gap

The repository already treats canonical rules as source material for generated client projections and
uses drift validation. Current support, however, is instruction-centric. It does not define a portable
custom-agent manifest, semantic hook intent, capability-loss model, exact runtime conformance tuple,
or admission evidence for custom agents across clients.

The external seed inventory contains 14 role folders. This specification records all 14 in a non-authoritative
migration catalog and normalizes four narrow pilot roles—Requirements & Scope, Code Review,
Application Security, and Test Automation—into source-owned packages. It does not modify or load the
external seed. AutoFix remains deferred, and the former Supervisor role becomes a deterministic,
fail-closed orchestration proposal instead of an LLM decision authority.

Current vendor documentation exposes overlapping but non-identical surfaces. A common `.agents/skills`
shape is discoverable by several clients, while instructions, commands, custom agents, hooks, MCP
configuration, and permission policy differ in path, format, lifecycle, and enforcement semantics.
OpenAI-compatible inference or MCP compatibility does not remove these agent-runtime differences.

## Decisions, invariants, and trust boundaries

Decision 1: Use one strict, vendor-neutral Agent Contract as the source of intent. Client-native files
are generated projections and are never edited back into the canonical contract automatically.

Decision 2: Keep client capability status outside agent manifests in a dated Client Capability Matrix.
The status vocabulary is `supported`, `degraded`, `unmapped`, and `forbidden`.

Decision 3: Treat hooks as semantic lifecycle intents. Executable commands are adapter-owned and must
be independently reviewed, signed, and admitted; raw hook commands are not portable contract data.

Decision 4: Use symbolic registry references for rules, skills, tool capabilities, MCP registries,
egress, secrets, inference profiles, approval policies, and evaluation suites. Resolve them only in
the trusted environment.

Decision 5: Apply progressive friction using the highest triggered risk tier:

- R0 Sandbox — public/synthetic data, local/read-only behavior, no secrets or external side effects.
- R1 Internal development — internal data, reversible writes in an assigned workspace, controlled
  egress, required review and logged tool calls.
- R2 Sensitive or externally visible — confidential/personal data, publish/deploy/send/write APIs,
  persistent memory, or production-like access; formal assessment and per-action approval are required.
- R3 Critical/high-impact — production, irreversible actions, regulated decisions, broad admin access,
  or autonomous multi-agent execution; default deny, separation of duties, and two-person approval.

Decision 6: Repository-local policy is design, detection, and recovery evidence. Effective prevention
belongs to external identity, sandbox, network, CI, policy-decision, and deployment-admission controls.

Decision 7: Reuse the repository-wide evidence tiers: L0 written, L1 automated, L2 live, and L3 owner
accepted with representative data. Record independent assessment as separate attestation metadata;
never infer it from an evidence tier.

Decision 8: A capability may be marked `supported` in a documentation snapshot only as a mapping claim.
Admission remains `research` until the exact conformance tuple passes the required evidence tier.

Decision 9: Store each canonical custom agent under `agent-platform/agents/<agent-id>/` as an
`agent.yml`, referenced `instructions.md`, and normalized `policy.yml` package. Vendor-native custom
agent files are generated projections and are not canonical inputs.

Decision 10: Treat the external `desktop-agents` collection as immutable migration seed material. Its
inventory and lineage may be recorded, but environment-specific absolute paths, provider settings,
runtime assumptions, and unverified policy claims must not enter the portable contract.

Decision 11: Replace an LLM Supervisor decision authority with deterministic aggregation over validated,
integrity-checked finding reports. Missing, timed-out, invalid, or tampered required reports route to
`MANUAL_REVIEW`; AutoFix is not part of the pilot orchestration.

Decision 12: The compiler may deterministically produce client-shaped artifacts and an integrity lock,
but it may write live discovery paths only through an explicit activation boundary. Activation requires
either a valid admission receipt or a disposable conformance workspace; unadmitted default scaffolds
retain inert canonical and compiled assets without silently enabling a client runtime.

Decision 13: Production adapter coverage is Codex, Claude Code, GitHub Copilot in VS Code, and Cursor.
Repo-local Codex TOML is a local Codex client projection; it must
not be represented as a generic hosted ChatGPT Work custom-agent discovery contract.

## Functional requirements

Requirement 1: The Agent Contract must be validated by JSON Schema Draft 2020-12 and reject unknown
properties at every object boundary.

Requirement 2: The contract must identify the agent, owner, lifecycle, risk tier, mission,
responsibilities, non-responsibilities, invocation modes, interfaces, and evidence requirements.

Requirement 3: The contract must express required rules, skills, reusable commands, model
capabilities, MCP/tool capabilities, semantic hook intents, permissions, delegation limits, runtime
budgets, data handling, memory, retention, logging, and human-approval policy without naming a vendor
or model. Each MCP tool must carry its own access and approval classification.

Requirement 4: The contract must not contain credentials, tokens, headers, private endpoints,
environment variables, executable commands, vendor-native tool identifiers, or absolute filesystem
paths. Separate secret and content scanning must cover values that structural schema cannot detect.

Requirement 5: The Client Capability Matrix must scope every mapping by client, surface, adapter
version, contract version, documentation date, lifecycle, maturity, projection strategy, lossiness,
discovery path, limitation, source, and conformance status.

Requirement 6: Every client entry must map every canonical capability exactly once. Unknown capability
statuses, mappings, maturity values, lifecycle values, adapter strategies, and lossiness values fail
validation.

Requirement 7: `degraded` mappings must declare limitations and non-zero lossiness. `unmapped` must fail
generation for a required capability. `forbidden` must fail regardless of optionality.

Requirement 8: Preview, beta, experimental, legacy, or deprecated surfaces must be marked volatile and
must be revalidated before adapter or client upgrades are admitted.

Requirement 9: The compiler must produce a deterministic projection manifest containing source digest,
schema version, adapter version, input references, output digests, declared losses, and validation
results. Re-running with identical inputs must be byte-stable except for excluded evidence timestamps.

Requirement 10: The compiler must never silently discard a required instruction, permission, tool,
approval, data, or evidence constraint. It must stop with a stable, machine-readable reason code.

Requirement 11: A generated projection must be replaceable and drift-checkable. Changes to generated
files must be recovered from the canonical source, not promoted implicitly into policy.

Requirement 12: Runtime admission must evaluate the intersection of manifest request, tool policy,
environment policy, identity scope, risk tier, and recorded human approval. A manifest requests
capability; it never grants authority.

Requirement 13: Every tool and MCP server must be resolved from a trusted, pinned registry entry with
an owner, version/schema digest, least-privilege scopes, expiry, and provenance. Token passthrough is
forbidden.

Requirement 14: Privileged, destructive, irreversible, externally visible, or regulated actions must
be deterministic-policy checked before execution, logged immutably, and routed to the applicable
human approval boundary.

Requirement 15: Conformance evidence must bind the exact agent contract digest, projection digest,
adapter/client/model/tool/policy/environment versions, test dataset version, result, skipped checks,
reviewer, date, expiry, and residual risk.

Requirement 16: Changing a matrix label alone must never promote admission. Promotion requires the
configured real-runtime suite and an admission receipt from the accountable owner.

Requirement 17: The migration catalog must enumerate every external seed role, classify its intended
control boundary, identify canonical or explicitly excluded status, declare the seed non-authoritative,
and record projection lifecycle without treating seed material as a generation input.

Requirement 18: Every canonical custom-agent package must validate its agent and policy contracts,
resolve its instruction reference within the package, bind exactly the intended policy identity, and
remain Draft until its adapter and runtime tuple are admitted.

Requirement 19: Governed multi-agent review must use independent worker outputs and a deterministic
decision policy. The aggregator must not receive raw source, must verify result integrity, must fail
closed on incomplete or invalid evidence, and must exclude AutoFix from the pilot.

Requirement 20: Each of the four canonical pilot agents must compile to a native-shaped artifact for
all four clients. The production projection manifest must enumerate all 16 artifacts, their canonical
source, documented target path, mapped fields, omitted optional capabilities, semantic losses,
documentation source and date, and independent conformance/admission status. A strict Draft 2020-12
schema must reject unknown manifest fields.

Requirement 21: A Codex projection must be valid TOML containing `name`, `description`, and
`developer_instructions`. Read-only canonical workspace access maps conservatively to
`sandbox_mode = "read-only"`; provider, model, endpoint, MCP, skill, and credential bindings are not
invented. Parent runtime overrides remain outside the file's authority.

Requirement 22: Compilation, installation, and runtime activation must remain distinct machine-readable
states. Default project initialization must not write an unadmitted artifact to a live discovery path.
Activation must use allowlisted client roots, transactional ownership checks, and either a valid
admission receipt or a disposable conformance-workspace grant; edited or unowned stale artifacts fail
closed instead of being overwritten or deleted.

Requirement 23: Deterministic generation must cover all four clients. The first admission cohort is
limited to exact, stable Codex R0 and Claude Code R1 candidates on approved macOS arm64; alpha,
pre-release, wildcard, or unresolved versions fail closed. PRD acceptance and adapter generation do not
admit an exact tuple.

Requirement 24: An organization-owned Agent Control Registry must resolve inference, tool/MCP, egress,
secret-handle, approval, and evaluation references from signed, content-addressed records. Signature,
digest, expiry, and revocation are verified before resolution; workspace fallback, raw-secret return,
and token passthrough are forbidden.

Requirement 25: External policy-decision and audit controls must enforce risk-tier lifecycle behavior.
Unavailable required control fails closed; R0/R1 external side effects are denied, R2 needs a single-use
bound approval, and this delivery does not allow R3 direct execution.

Requirement 26: Evidence has no grace period after a tuple-affecting change and is also time-bound by
risk tier. Revalidation must use the required evidence tier, and registry revocation freshness must be
bounded, recorded, and fail closed when unavailable or stale.

Requirement 27: Hard prohibited uses cannot be waived at project level. The agent cannot self-approve,
apply or weaken its guardrails, perform autonomous destructive or production/admin actions, expose
credentials, or serve as sole decision maker for regulated/high-impact outcomes. Any future R3
read-only advisory use requires a separate Accepted delivery delta.

## Canonical agent contract

The canonical schema lives at
[`agent-platform/agent-contract.schema.json`](../../../../agent-platform/agent-contract.schema.json).

The external seed inventory is captured in
[`agent-platform/agent-catalog.yml`](../../../../agent-platform/agent-catalog.yml). The first canonical
packages live under `agent-platform/agents/`. Their instructions and policy packs are referenced
by, but are not embedded as executable authority in, the portable manifest.

The contract separates:

- identity and mission;
- typed interfaces and data classifications;
- rules, skills, reusable commands, model capabilities, tools/MCP, and semantic hook requirements;
- filesystem, network, secret, side-effect, and approval boundaries;
- delegation depth, parallelism, and context-sharing limits;
- sandbox, workspace access, task-scoped identity, and execution budgets;
- memory, retention, and logging constraints; and
- evaluation suites, minimum evidence tier, claims, and approval requirements.

Cross-manifest constraints such as unknown references, identity-based duplicate entries, self-handoff
and handoff cycles, and write-glob containment within read scope require a semantic validator and
registry; JSON Schema alone is not sufficient.

## Governed review orchestration

The governed-review source definition at
[`agent-platform/orchestrations/governed-review.yml`](../../../../agent-platform/orchestrations/governed-review.yml)
runs the four pilot workers independently and accepts only structured finding reports. The decision
engine is deterministic policy, not an LLM Supervisor. Its aggregation policy is fail-closed for a
missing worker, timeout, invalid schema, integrity failure, or unknown policy version.

Imported weights and thresholds are uncalibrated research hypotheses. They do not decide production
admission until representative datasets, deterministic implementation tests, security tests, and owner
acceptance establish the claimed behavior. AutoFix is explicitly prohibited from this pilot flow.

## Client capability matrix and adapter behavior

The research matrix lives at
[`agent-platform/client-capabilities.yml`](../../../../agent-platform/client-capabilities.yml).
Its initial clients are Codex, Claude Code, GitHub Copilot in VS Code, and Cursor. All entries are
documentation mappings with `admission.state: research` and
`conformance.status: not_run`.

Adapter strategies are:

- `emit` — generate the documented native representation;
- `import-wrapper` — reference a compatible canonical artifact without copying its authority;
- `translate` — transform with explicit bounded or material semantic loss; and
- `omit` — emit nothing and return a failure or explicit optional-capability result.

An adapter must select by exact supported client/version range, refuse ambiguous versions, validate
its output, emit a loss report, and preserve stable source references. A client update invalidates the
prior runtime acceptance until the affected tuple is rerun.

## Client projections

The production compiler emits one client-native artifact per canonical agent and client, plus a strict,
content-addressed projection manifest. Generated golden outputs may be retained only as compiler test
fixtures with byte-for-byte regeneration checks; hand-maintained preview copies are not a second source.

Adapters map only the common, conservative read-only subset until admitted runtime bindings exist.
Optional execution, static analysis, MCP, model selection, network, persistent memory, and external
side effects are omitted or fail closed. Hook intents, evidence capture, registry resolution,
filesystem deny globs, retention, and external policy remain explicit losses or external requirements
rather than being silently credited to a client file.

For Codex, the projection represents project-scoped custom agents in documented local Codex CLI and
IDE clients. A supported ChatGPT desktop experience may surface Codex subagent activity, but the
repository TOML makes no generic desktop or hosted ChatGPT Work discovery claim.

## Skills, commands, custom agents, and hooks

Skills are portable content packages when a client documents compatible discovery and format. Commands
are treated as user-invoked workflow entry points and may be translated into skills or workflows only
when invocation and authority semantics remain safe. Custom-agent projections may differ structurally;
for example, one client's TOML definition must not be copied into another client's Markdown format.

Hook portability is limited. The canonical contract therefore names control intents such as
`before-tool-policy`, `after-tool-audit`, `before-external-side-effect`, and
`after-completion-evidence`. The adapter either binds an admitted implementation or reports the intent
as degraded/unmapped. A command-only or fail-open hook cannot be credited as an external authorization
control.

## Model, MCP, and tool requirements

The contract requests semantic model capabilities such as reasoning, tool calling, structured output,
vision, long context, or code execution through an approved inference-profile reference. Provider,
model, endpoint, price, region, privacy terms, and fallback behavior belong in the environment-owned
profile and its admission evidence.

MCP and other tools are capability references resolved from an approved registry. Resolution requires
explicit consent, pinned server/tool/schema digest, least scope, resource/audience-bound authorization,
short-lived credentials, sandboxing, egress policy, operation approval, provenance, and invocation
logging. Tool output, prompts, retrieved content, memory, and generated code remain untrusted input.

## Security and authorization

The threat model must cover prompt injection, retrieval and memory poisoning, insecure tool output,
excessive agency, privilege escalation, confused deputy behavior, token theft, data exfiltration,
supply-chain compromise, cost/resource exhaustion, unsafe delegation, audit evasion, and agent attempts
to edit their own guardrails.

The control plane must default deny, use per-task identity, keep credentials out of model context,
isolate code execution, allowlist egress, cap duration/tool/cost/side effects, validate structured tool
arguments before execution, require human approval at the policy boundary, and retain tamper-evident
tool/approval/evidence records. R2 and R3 require formal impact and threat assessment; R3 also requires
separation of duties, independent adversarial testing, staged rollout, rollback, and a kill switch.

## Data and migration

No production business-data migration is introduced. Implementation adds versioned contract, matrix,
adapter, evidence, and exception records. Contract migrations must be explicit,
one-way version transforms with fixtures proving that required constraints are not weakened. Silent
schema coercion and auto-promotion of deprecated fields are forbidden.

The external Desktop collection is not moved, deleted, rewritten, or discovered at runtime. Migration
is an explicit normalization process into source-owned packages; lineage uses a symbolic seed
identifier rather than a machine-specific absolute path.

## API behavior

N/A — this capability defines source contracts and admission semantics; it does not introduce a runtime API.
A future API requires its own accepted delivery delta and threat model.

## Validation, observability, and evidence

Validation has four independent layers:

1. Schema and semantic validation of source contracts, references, mappings, and projections.
2. Deterministic adapter fixtures, golden outputs, negative cases, drift detection, and policy tests.
3. Real client/model/tool conformance covering instruction discovery, policy pressure, tool denial,
   approval, prompt injection, exfiltration, budget exhaustion, delegation, and evidence capture.
4. Operational admission, monitoring, incident exercise, exception expiry, rollback, and periodic review.

A green mock or policy file is design evidence only. Every claim records requirement/source/version,
implementation and enforcement point, observation, immutable artifact digest, full runtime tuple,
result and skips, owner/reviewer/date/expiry, and residual risk.

## Standards and guidance crosswalk

The machine-readable crosswalk lives at
[`agent-platform/standards-crosswalk.yml`](../../../../agent-platform/standards-crosswalk.yml). It
maps framework anchors to requirements, enforcement points, evidence, accountable roles, and
assessment status. Its mapping is intentionally partial and does not replace licensed-text review or
a scoped audit.

- Organization management and risk: ISO/IEC 42001:2023, ISO/IEC 23894:2023, ISO/IEC 42005:2025,
  NIST AI RMF 1.0, and NIST AI 600-1.
- Secure engineering: NIST SP 800-218 SSDF 1.1 and NIST SP 800-218A. SSDF 1.2 remains a draft at the
  research date and is not the normative baseline.
- AI/agent threats: OWASP GenAI LLM Top 10 2026 and OWASP Top 10 for Agentic Applications 2026.
- Tool boundary: Model Context Protocol specification 2026-07-28, its authorization specification,
  and security best practices. OWASP MCP Top 10 v0.1 is supplemental beta guidance.
- Supply chain: SLSA 1.2, CycloneDX 1.7 / ECMA-424 2nd edition, or SPDX 3.0.1. Published
  ISO/IEC 5962:2021 maps to SPDX 2.2.1; SPDX 3.0 ISO work is not yet a published ISO baseline.
- Policy enforcement: OPA, Cedar, and Kyverno are implementation tools selected by boundary, not
  compliance standards or certifications.

These references guide control design. This PRD does not claim certification, conformance, or a SLSA
level; such claims require all applicable normative requirements and scoped evidence.

## Deployment and operations

No long-running service, model route, MCP server, secret, or production policy is introduced. The
delivery packages the compiler and canonical assets, creates inert projections by default, and gates
live discovery-path activation separately. Build/release evidence must cover isolated execution,
content-addressed artifacts, SBOM/AIBOM, provenance, external admission, alerting, incident response,
rollback, stale-artifact handling, and decommissioning.

## Risks

- Vendor surfaces can change faster than adapters; version ranges and volatile mappings can become stale.
- Similar path or file formats can conceal different trust, precedence, or approval semantics.
- Users may mistake generated repository files for preventive controls or matrix labels for certification.
- Lowest-common-denominator projection can weaken safety or usefulness; the compiler must fail instead.
- Rich adapters may become a second policy source; deterministic generation and drift checks are required.
- Imported rules, weights, and thresholds may encode stale stack assumptions or unmeasured precision;
  normalization, calibration, and owner acceptance are required before admission.
- Real conformance across clients, models, operating systems, extensions, and enterprise policies is
  costly; risk-tiered representative tuples and expiry are required.

## Accepted owner decisions

Owner decision status: Accepted

On 2026-08-18 the owner explicitly authorized the proposed end-to-end implementation and client
installation sequence. The five accepted decisions below resolve Open Questions 1 through 5 and are
reflected in Requirements 23 through 27. This policy/design acceptance authorizes implementation; it
does not assert completed delivery, activate discovery paths, or promote a client beyond its recorded
conformance/admission evidence.

The source snapshot was rechecked on 2026-08-18 against the
[NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework),
[OWASP Agentic Applications Top 10 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/),
[MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28), and
[official OpenAI Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).
The time-to-live and revocation-freshness values below are proposed organization policy, not durations
prescribed by those sources.

### Decision 14 — Initial conformance and admission cohort

Resolves Open Question 1

Recommendation: Keep deterministic generation coverage for Codex, Claude Code, GitHub Copilot in VS
Code, and Cursor, while limiting the first runtime-admission cohort to exact,
pinned local tuples on approved macOS arm64. Use a stable Codex CLI or IDE tuple for an R0
`conformance-readonly-smoke` contract and a stable Claude Code CLI tuple with the R1
`requirements-scope` contract. A pre-release or alpha client is research-only and cannot be admitted.

Scope:

- The R0 smoke contract uses only public/synthetic data, read-only workspace access, no MCP, no
  secrets, no child delegation, and no external side effects. Agent tool and workload egress are
  denied; hosted inference transport is permitted only through a separately brokered and allowlisted
  control-plane path outside the agent tool surface.
- The R0 smoke contract is a test-only post-acceptance conformance fixture under
  `agent-platform/conformance/fixtures/`. It is excluded from the canonical agent catalog, production
  scaffold, managed-project renderer inputs and outputs, and this repository's live discovery paths.
  After PRD acceptance, an isolated conformance harness may materialize its candidate projection only
  inside an ephemeral workspace's documented discovery path, such as `.codex/agents/*.toml`, for an L2
  test and must then destroy the workspace. That temporary test does not promote the fixture into a
  managed project or supported adapter. Existing R1 agents are not relabelled as R0.
- Every receipt pins client surface, release channel, client/extension/build identity, binary digest and
  signing identity, OS build and architecture, contract/adapter/projection digests, resolved inference
  profile, model resolution, tool/MCP/policy/environment digests, evaluation dataset, effective parent
  and live sandbox/approval/permission/session overrides, and managed-policy precedence.
- Numeric versions belong in candidate evidence and receipts, not the durable PRD. `latest`, wildcard,
  major/minor-only, or unresolved version identifiers fail closed.
- PRD acceptance admits no exact tuple. A post-acceptance, schema-validated candidate manifest must pin
  the exact versions, builds, digests, and effective configuration before conformance begins. If no
  stable Codex candidate exists, its cohort slot remains empty and fails closed rather than substituting
  an alpha or pre-release build.
- Cursor, VS Code/Copilot runtime admission, Windows, WSL, Linux, and hosted
  ChatGPT Work remain outside the first cohort. They stay `research` until an exact tuple passes the same
  gate; ChatGPT Work remains `unmapped` for repository-file projection.

Accountable owner: `platform-governance-owner`

Required reviewers: `agent-security-owner`, `ai-risk-owner`, and developer-experience owner

Owner-review inputs: the client-capability matrix, reviewed projection mappings, current primary
client documentation, exact-version policy, and the proposed R0/R1 boundary above.

Required post-acceptance delivery/admission evidence: a schema-validated, content-addressed candidate
manifest; L1 deterministic generation for all four clients; L2 real discovery, invocation, instruction
precedence, effective live-configuration capture, permission denial, injection, drift, logging, and
rollback tests for the exact Codex R0 and Claude Code R1 candidates; then a time-bound L3 owner
admission receipt.

Residual risk: The initial cohort is intentionally narrow, vendor updates can invalidate it immediately,
and generation coverage must not be presented as runtime support for excluded clients or operating
systems.

Owner disposition: Accepted

Owner acceptance date: 2026-08-18

### Decision 15 — Organization-owned control registry

Resolves Open Question 2

Recommendation: Establish an organization-owned logical `Agent Control Registry` as the only resolver
for inference profiles, tool/MCP capabilities, egress policy, secret handles, approval policy, and
evaluation-suite references. Protected source records are released as signed, content-addressed bundles;
a trusted local resolver or policy decision point verifies signature, digest, version, expiry, and
revocation before resolution. Missing, expired, ambiguous, or unverifiable entries fail closed.

Scope:

- Workspace files and client configuration cannot act as fallback registry authorities.
- The registry stores metadata, policy, provenance, and secret-broker handles; it never stores or returns
  raw secret values, provider credentials, or bearer tokens to model context.
- Registry releases are immutable, independently reviewed, auditable, and applied atomically with a
  verification receipt. R2/R3 records require maker-checker separation.
- Every resolution verifies either current online revocation status or a signed revocation-state object
  binding an epoch, digest, `issued_at`, and `next_update`. The `next_update` interval is capped at
  `PT4H` for R0/R1 and `PT15M` for R2; R3 requires an online check at every resolution. A resolver that
  cannot obtain status within that bound fails closed. Its receipt binds the revocation-state digest,
  epoch, `checked_at`, and `next_update`; a pushed or newly observed revocation suspends affected use at
  the next policy decision and can trigger the kill switch.
- The backing product, endpoint, and environment topology are implementation/deployment choices and do
  not belong in this portable PRD.

Accountable owner: `platform-governance-owner`

Required reviewers: AI platform, tool-platform, network-security, identity/secrets, agent-security, and
evidence owners

Owner-review inputs: symbolic registry references in the canonical contracts, Decisions 4 and 6,
Requirements 4, 12, and 13, the standards crosswalk, and the external-trust-boundary threat model.

Required post-acceptance delivery/admission evidence: signed registry bundle and provenance;
authorization and reference-resolution conformance; expiry/revocation, unknown-reference,
signature-failure, secret-leak, rollback, and atomic-apply tests; immutable resolution receipts.

Residual risk: Registry or resolver compromise becomes a high-value supply-chain and authorization
failure, so availability, key rotation, incident response, and independent release review remain
mandatory external controls.

Owner disposition: Accepted

Owner acceptance date: 2026-08-18

### Decision 16 — Mandatory external lifecycle controls

Resolves Open Question 3

Recommendation: Never credit a client-native hook as a preventive authorization control. Mandatory
lifecycle intents are bound to external sandbox, policy-decision, approval, and audit boundaries and
fail closed when the required policy or audit sink is unavailable.

Scope:

| Risk tier | Mandatory external behavior |
| --- | --- |
| R0 | When any tool is enabled, enforce `before-tool-policy` and record success, denial, failure, and cancellation through `after-tool-audit`. `before-external-side-effect` is always DENY. `after-completion-evidence` is required for a conformance or admission claim. |
| R1 | Enforce `before-tool-policy` and `after-tool-audit` for every tool call and `after-completion-evidence` for every admitted workflow. Any external-side-effect request is denied. It may proceed only as a new, separately assessed and admitted R2 tuple/workflow; there is no automatic or in-session privilege elevation. |
| R2 | Enforce all four intents, including `before-external-side-effect`, through an external PDP. Side effects require a single-use approval bound to task identity, exact resource, normalized arguments, and expiry. |
| R3 | Enforce all four intents, two-person approval, separation of duties, immutable audit, rollback, and kill switch. Direct side effects remain prohibited in this pilot; only separately accepted read-only advisory analysis may be considered. |

Before execution, the runtime reserves a tamper-evident audit record or writes a sealed local outbox
entry. If neither is available, the tool call is denied. A post-execution audit-delivery failure cannot
undo an action; it suspends further actions, preserves the sealed record, and opens an incident.

Accountable owner: `agent-security-owner`

Required reviewers: `ai-risk-owner`, platform-runtime owner, audit/evidence owner, and affected system
owner for R2/R3

Owner-review inputs: the R0-R3 tier definitions, canonical hook intents, Decisions 3 and 6,
Requirements 3, 12, and 14, and the agent/tool-boundary threat model.

Required post-acceptance delivery/admission evidence: external policy and audit configuration digests;
positive and negative tool-call traces; unavailable-PDP/audit-reservation/outbox fail-closed tests;
post-execution delivery-failure suspension tests; approval binding/replay/expiry tests; R3 separation,
rollback, and kill-switch exercises when applicable.

Residual risk: Client updates, inherited tools, live permission overrides, and telemetry loss can bypass
instruction-only expectations; runtime evidence must observe the effective external controls.

Owner disposition: Accepted

Owner acceptance date: 2026-08-18

### Decision 17 — Evidence expiry and revalidation

Resolves Open Question 4

Recommendation: Treat evidence validity as both change-triggered and time-bound, with no grace period.
Any changed or unverifiable tuple component immediately invalidates admission for the new tuple even if
the prior evidence remains useful historical evidence.

Scope:

- Stable documentation mappings expire after `P90D`; preview, beta, experimental, or deprecated mappings
  expire after `P30D`.
- Unchanged exact runtime-tuple receipts expire no later than `P90D` for R0, `P30D` for R1, `P14D` for
  R2, and `P7D` for a separately accepted R3 read-only exception.
- R2 per-action approval is single-use and expires after at most `PT30M`; an R3 read-only run approval is
  two-person, single-run, and expires after at most `PT15M`.
- Contract, projection, adapter, client, model/fallback, tool/MCP/schema/scope, policy, identity, egress,
  environment image, OS, sandbox, trust root, dataset, use case, data classification, or risk-tier change
  invalidates affected admission. A critical advisory, incident, enforcement drift, or signature or
  registry revocation suspends use when observed; fresh status is required within Decision 15's bounded
  interval, after which new resolution fails closed.
- Every change requires at least L1 validation; runtime-affecting changes require L2; use-case, data, or
  risk changes require renewed assessment and L3 owner acceptance.

Accountable owner: `ai-risk-owner`

Required reviewers: evidence owner, agent-security, platform-runtime, tool-platform, model-platform,
and affected data or system owner

Owner-review inputs: Requirement 15, the complete change tuple, the proposed risk tiers, current vendor
volatility, and organizational risk appetite. The numeric TTL values are internal policy proposals, not
standard-prescribed durations; the same is true of Decision 15's revocation-freshness bounds.

Required post-acceptance delivery/admission evidence: immutable tuple and evidence manifest, timestamps
and earliest-linked expiry, change-impact classification, revalidation results, revocation/suspension
receipt, and reviewer decision.

Residual risk: Short validity windows increase operational cost, while longer windows increase exposure
to vendor and policy drift. Any TTL extension is a separately recorded, narrower, time-bound risk-owner
exception and cannot survive a change-triggered invalidation.

Owner disposition: Accepted

Owner acceptance date: 2026-08-18

### Decision 18 — Prohibited R2/R3 uses and accountability

Resolves Open Question 5

Recommendation: Define hard prohibitions that a project-level approval or waiver cannot override. This
pilot does not admit R3 direct execution. R2 read-only analysis or bounded external action may be
evaluated only case by case with the required assessments, external policy, and per-action approval.

Scope:

- Prohibit raw credentials or tokens in model context, token passthrough, and unapproved
  confidential/personal/regulated-data egress.
- Prohibit unauthorized or self-directed runtime application, bypass, disablement, or weakening of IAM,
  DLP, EDR, sandbox, policy, approval, audit, evidence, rollback, kill-switch, or deployment-admission
  controls; an agent cannot approve itself or apply edits to its guardrails. An advisory policy-as-code
  patch may be proposed only through a separate human-controlled review workflow and cannot be applied
  by the proposing agent.
- Prohibit autonomous destructive, irreversible, broad-admin, production-write/deploy, release-signing,
  secret/key-management, payment, deletion, or physical/safety actuation through this Lab.
- Prohibit an agent as the sole or final decision-maker for employment, credit, insurance, healthcare,
  education, justice, public-service, safety-critical, or other legally/high-impact outcomes.
- Prohibit unauthorized access, credential theft, malware deployment, unlawful surveillance, unbounded
  recursive delegation, privilege aggregation, and cross-task sensitive persistent memory.
- Prohibit any use forbidden by applicable law or the organization's acceptable-use policy; neither a
  project owner nor this PRD can waive that floor.
- A future R3 read-only advisory use requires its own Accepted PRD delta, independent two-person approval,
  separation of duties, redacted evidence, continuous monitoring, rollback, and kill switch.

Accountable owner: `ai-risk-owner`; `team:ai-governance` maintains the prohibited-use catalog

Required reviewers: CISO/agent-security, Legal/Data Protection, affected business/system/data owner, and
platform-governance owner

Owner-review inputs: the R0-R3 tier definitions, threat model, Requirements 3 and 14, and the proposed
prohibited-use catalog above. These detailed prohibitions are proposed organizational policy and must be
reconciled with applicable law and the authoritative acceptable-use policy.

Required post-acceptance delivery/admission evidence: intended/prohibited-use record,
impact/privacy/threat assessment, data-flow and tool inventory, policy-denial tests, owner and
independent-review decisions, incident/rollback exercise, and time-bound residual-risk receipt for any
approvable R2 case.

Residual risk: Laws, organizational risk appetite, and client capability can change. Legal, privacy, or
security veto cannot be overridden by a project owner, and hard prohibitions remain outside exception
workflow.

Owner disposition: Accepted

Owner acceptance date: 2026-08-18

## Resolved questions

Open Question 1: Which initial client/OS cohort and exact-tuple admission mechanism form the first
supported admission boundary? Resolution: Decision 14. Status: Resolved — Accepted.

Open Question 2: Which organization-owned registry service will resolve inference profiles, tool
capabilities, MCP registries, egress policies, secrets, approval policies, and evaluation suites?
Resolution: Decision 15. Status: Resolved — Accepted.

Open Question 3: Which semantic hook intents must be mandatory externally enforced controls rather than
client convenience hooks for each risk tier? Resolution: Decision 16. Status: Resolved — Accepted.

Open Question 4: What evidence expiry and revalidation policy applies to client, adapter, model, MCP,
policy, and environment changes? Resolution: Decision 17. Status: Resolved — Accepted.

Open Question 5: Which R2/R3 use cases are prohibited rather than approvable, and who owns that decision?
Resolution: Decision 18. Status: Resolved — Accepted.

## Acceptance criteria

- [x] The accountable owner marks this PRD `Status: Accepted` after resolving the open questions.
- [x] The accountable owner records an Accepted disposition for Decisions 14 through 18 and reflects
  them in derived Requirements 23 through 27 before metadata acceptance.
- [x] The Agent Contract schema passes meta-schema validation and all valid/invalid fixture tests.
- [x] The catalog, canonical agent packages, policy packs, and deterministic orchestration pass strict
  schema, path-containment, identity-binding, and fail-closed invariant tests.
- [x] Semantic validation rejects unknown references, authority escalation, invalid glob containment,
  conflicting capability declarations, self/cyclic handoffs, and embedded secret/endpoint/vendor fields.
- [x] The matrix covers every canonical capability for every proposed client with dated primary sources,
  explicit loss, lifecycle, maturity, and adapter behavior.
- [x] The compiler produces deterministic, validated projections and a content-addressed projection
  manifest; external signing, when configured, is verified separately.
- [x] Negative tests prove mandatory unmapped, forbidden, materially lossy, and unknown-version mappings
  fail closed.
- [ ] At least one exact R0 and one exact R1 tuple pass real-client conformance; discovery-only and mock
  results are reported separately.
- [ ] Security tests cover injection, poisoning, exfiltration, privilege, approval, budgets, delegation,
  audit, rollback, and guardrail tampering.
- [ ] Governance, security, platform, and developer-experience owners review residual risks and issue a
  time-bound admission receipt.
- [x] Documentation clearly distinguishes research mapping, implemented adapter support, runtime
  conformance, owner acceptance, and independent certification.
- [x] All 24 compiler outputs parse in their native syntax, bind to the intended canonical agent,
  declare semantic losses, and report conformance/admission independently from generation success.
- [x] Negative checks prove default unadmitted scaffolding creates no live discovery file and that
  receipt-gated or ephemeral activation is allowlisted, transactional, drift-checked, and reversible.

## Delivery flow

Draft -> owner review -> **Accepted** -> active implementation plan -> ordered tasks ->
contract/compiler work -> deterministic validation -> real-runtime conformance -> risk-owner admission
-> staged rollout -> continuous monitoring and periodic revalidation.
