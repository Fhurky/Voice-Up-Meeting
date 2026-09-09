# Agent Platform domain

Status: Draft

## Purpose

The Agent Platform domain owns the vendor-neutral contracts, capability mappings, and evidence
semantics needed to project governed AI-assisted development behavior into approved IDE, CLI, model,
agent, and tool surfaces.

The domain follows one operating principle: **freedom above immutable guardrails**. A developer may
choose an admitted client or model, while identity, data, tool, network, approval, audit, and release
controls remain enforced outside the agent-editable workspace.

## Actors

- Vibe coder — chooses an admitted client and uses generated projections without learning every
  vendor-specific configuration format.
- Agent author — defines portable intent, required capabilities, and bounded responsibilities.
- Adapter maintainer — maps the canonical contract to a documented client surface and records loss.
- Platform governance owner — owns admission policy, exceptions, lifecycle, and management review.
- Security and risk reviewer — reviews the risk tier, trust boundaries, threats, and residual risk.
- Evidence reviewer — distinguishes written design, test-observed behavior, runtime acceptance, owner
  acceptance, and independent audit evidence.

## Ubiquitous language

- **Canonical contract** — the source-owned, vendor-neutral statement of agent intent and capability
  requirements.
- **Projection** — a generated vendor-specific file such as `AGENTS.md`, a skill, hook, command, or
  custom-agent definition.
- **Adapter** — versioned compiler logic that emits or validates projections for one client surface.
- **Capability mapping** — a documented `supported`, `degraded`, `unmapped`, or `forbidden` decision
  for one contract capability and client/version tuple.
- **Semantic hook intent** — a lifecycle control objective, not executable vendor hook code.
- **Conformance tuple** — the exact contract, adapter, client, model, tool, policy, and environment
  versions under which behavior was observed.
- **Admission** — an external policy decision allowing a specific tuple for a risk tier and use case.
- **Evidence tier** — the repository-wide L0 written, L1 automated, L2 live, and L3 owner-accepted
  scale; independent assessment is recorded separately and never implied by an evidence tier.

## Invariants

1. The canonical contract is the source of portable agent intent; generated client files are
   disposable projections and external policy remains authoritative for effective access.
2. A client or provider may not grant more effective authority than the intersection of the manifest,
   tool policy, environment policy, and recorded approval.
3. Documentation discovery is not runtime conformance, and model discovery is not proof of chat,
   tool-use, streaming, latency, privacy, or security behavior.
4. Mandatory `unmapped`, `forbidden`, or materially lossy capabilities fail generation or admission.
5. Executable hooks, raw commands, credentials, endpoint URLs, model identifiers, and vendor-native
   tool identifiers do not belong in the portable agent contract.
6. Repository instructions can detect drift and guide recovery; they cannot be treated as immutable
   enforcement against an agent that can edit the repository.
7. Privileged, irreversible, destructive, regulated, or external-side-effect actions require policy
   checks outside the model and an appropriate human approval boundary.
8. Every support or compliance claim is tied to versioned sources and evidence; no matrix label alone
   constitutes certification or production acceptance.

## Owned data and artifacts

- Agent Contract JSON Schema and conforming manifests.
- Client Capability Matrix, source register, adapter decisions, and loss declarations.
- Semantic rule, skill, command, tool-capability, hook-intent, and custom-agent references.
- Conformance cases, evidence manifests, admission receipts, and time-bound exceptions.
- Risk-tier and evidence-tier semantics used by the Agent Platform.

## Upstream boundaries

- Organization AI policy, acceptable-use policy, data classification, and risk appetite.
- Repository rules, accepted domain specifications, technology profile, and dependency admission.
- Identity provider, secret broker, approved tool/MCP registry, and network policy.
- Authoritative vendor documentation and normative standards versions.

## Downstream boundaries

- Contract compiler and client adapters.
- IDE/CLI projections and governed execution sandboxes.
- CI validation, policy decision points, deployment admission, and audit evidence stores.
- Client/model/tool conformance suites and operational telemetry.

## Explicit non-responsibilities

- Model hosting, routing, procurement, or provider credentials.
- Installing, licensing, or operating developer clients.
- Storing secrets, private endpoints, personal data, or environment-specific topology in source.
- Replacing enterprise IAM, DLP, EDR, network enforcement, CI rulesets, or deployment admission.
- Declaring ISO certification, SLSA level attainment, or production support without scoped evidence
  and the required independent or owner acceptance.
