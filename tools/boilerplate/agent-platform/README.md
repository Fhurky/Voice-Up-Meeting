# Canonical Agent Platform

This directory is the source-owned, vendor-neutral custom-agent contract consumed by the production
projection compiler. It is never generated `.kt-scaffold/` state and vendor-native outputs never
become policy sources.

Contents:

- `agent-contract.schema.json` — strict JSON Schema Draft 2020-12 for portable agent intent.
- `agent-policy.schema.json` — strict schema for source-owned agent policy packs.
- `agent-catalog.schema.json` — strict schema for external-seed inventory and migration status.
- `orchestration.schema.json` and `decision-policy.schema.json` — strict contracts for deterministic,
  fail-closed aggregation.
- `agent-catalog.yml` — implementation inventory for the 14 external seed roles; the seed is not
  canonical.
- `agents/` — version `1.0.0` canonical packages for Requirements & Scope, Code Review, Application
  Security, and Test Automation. Each package contains `agent.yml`, `instructions.md`, and
  `policy.yml`.
- `orchestrations/governed-review.yml` — deterministic four-worker review flow. It replaces an LLM
  supervisor for decisions and explicitly excludes AutoFix.
- `policies/aggregation/governed-review.yml` — uncalibrated Draft thresholds imported as research
  hypotheses, not runtime admission policy.
- `examples/pr-reviewer.agent.yml` — a deliberately read-only R1 schema-test fixture.
- `client-capabilities.yml` — 2026-08-18 primary-source mapping for the four implemented serializers;
  generation status is independent from runtime conformance and admission.
- `runtime-candidate.schema.json` and `conformance/candidates/macos-arm64-2026-08-19.yml` — strict,
  exact installed-artifact inventory with digests/signing receipts; installation is not conformance.
- `conformance-snapshot.schema.json` and the date-stamped files below `conformance/runs/` — strict L2
  smoke observations for all four clients. Each snapshot is immutable historical evidence bound to
  the compiler lock observed at capture; it is not rewritten when the current compiler changes. The
  full suite remains `not_run` and no tuple is admitted.
- `standards-crosswalk.yml` — partial design mapping from standards/framework anchors to requirements,
  enforcement points, evidence, and accountable roles; it is not a conformance claim.

The owning specification is
[`specs/agent-platform/PRDs/001-vendor-neutral-agent-contract/PRD.md`](../specs/agent-platform/PRDs/001-vendor-neutral-agent-contract/PRD.md).
It is Accepted and authorizes implementation. It does not authorize client activation, runtime use,
or production admission for any exact tuple.

## Canonical custom-agent package

```text
agent-platform/agents/<agent-id>/
├── agent.yml        # portable identity, interfaces, capabilities, authority request, and evidence
├── instructions.md  # narrow behavioral instructions referenced by agent.yml
└── policy.yml       # normalized controls with external-seed lineage
```

The external `desktop-agents` seed remains untouched and non-authoritative. The compiler generates 16
client-native files for Codex, Claude Code, VS Code/Copilot, and Cursor, plus
a strict content-addressed lock. Scaffolded projects store them below
`.kt-scaffold/agent-projections/`; no default operation writes them to a client discovery path.
Activation still requires a disposable conformance grant or separately issued admission receipt. A
generated client file is never a second policy source. Repo-local Codex TOML applies to local Codex
clients; it is not presented as a generic hosted ChatGPT Work filesystem contract.

## Enforcement APIs

Production code under `src/kt_scaffold/agent_platform/` keeps the trust transitions explicit:

- `compiler.py` and `projection_store.py` compile and manage inert, content-addressed outputs. The
  repeatable CLI `--agent-client` selector never activates a native discovery path.
- `registry.py` verifies pinned Agent Control Registry records through injected signature and
  revocation ports; no workspace registry fallback or raw-secret payload is accepted.
- `admission.py` verifies exact, stable, time-bound accountable-owner admission records. The receipt
  performs no activation or execution and still requires the external policy intersection.
- `activation.py` re-verifies either a signed, 15-minute maximum, externally single-use conformance
  grant for a disposable workspace or a signed admission envelope plus the complete effective runtime
  tuple for persistent activation. Native writes and deactivation are client-allowlisted,
  digest-owned, transactional, rollback-tested, and bound to the exact prior receipt and an externally
  retained previous-state digest; there is intentionally no ungated activation CLI command.
- `aggregation.py` combines only integrity-bound normalized findings from the four canonical workers.
  Missing, invalid, timed-out, low-confidence, or tampered evidence routes to `MANUAL_REVIEW`; its
  research thresholds do not grant runtime or production authority.

## Adapter and candidate snapshot

The stable-field compiler baseline and three client adapters remain version `1.0.1`; the Codex adapter
is version `1.0.2` after adding a bounded read-only shell/tool mapping for workspace inspection. It deliberately excludes Codex
experimental execution rules, VS Code Preview hooks, Claude legacy command files, and the auto-updating
Cursor headless CLI. Cursor custom agents emit only the five currently documented fields: `name`,
`description`, `model`, `readonly`, and `is_background`.

The installation inventory records these exact artifacts on macOS arm64: Codex `0.147.0`, Claude Code
`2.1.227`, VS Code `1.133.0` with bundled Copilot `0.61.0`, and Cursor IDE `3.15.19`. Cursor's
`2026.08.11-e8db854` headless CLI, Codex desktop `26.818.21641`, and the bundled pre-release Codex
binaries are exploratory exclusions, not admitted adapter targets.
Codex native agent names deterministically translate canonical hyphens to underscores because the
runtime spawn identifier accepts lowercase letters, digits, and underscores; canonical IDs and file
paths remain unchanged in the content-addressed manifest.
The 2026-08-19/20 bounded runs found Claude project-agent
discovery, direct read-only invocation, adversarial refusal, parent-mode observation, and external hook
events working without workspace or session retention. Stable Codex CLI `0.147.0` could not create its
custom child under `--ephemeral`; a subsequent owner-observed Codex desktop run discovered and invoked
the project-scoped agent once, used only bounded read-only shell inspection, rejected the synthetic
prompt injection, preserved the exact workspace digest, removed its temporary trust entry, and
destroyed the workspace. This is an exploratory partial pass because desktop `26.818.21641` bundles
pre-release Codex CLI `0.148.0-alpha.21` and emitted no machine-exported immutable event stream. The
VS Code/Copilot stable extension-host run exposed the canonical `requirements-scope` mode, used only
two `read_file` calls, rejected the synthetic prompt-injection request, preserved the exact workspace
digest, and destroyed the disposable workspace. It remains a partial, owner-observed UI result rather
than a machine-exported immutable audit receipt. Cursor IDE likewise discovered the explicit
`/requirements-scope` invocation, used only two Read calls, rejected the injection, preserved the
digest, and destroyed the workspace; its response reported direct mode execution without delegation,
so independent subagent isolation remains unproven. The complete suite remains `conformance: not_run`
and every tuple remains `admission: research`.

The states must be read independently:

1. `generation_status: implemented` means the serializer can produce an inert projection.
2. An installed candidate receipt proves artifact identity, version, digest, and available signing data.
3. `conformance: passed` requires real discovery, invocation, denial, override, and audit evidence.
4. `admission: admitted` requires a separate, time-bound accountable-owner decision.

## Trust model

The manifest requests capabilities; it does not grant them. Effective authority is always:

```text
manifest request
  ∩ admitted tool/MCP policy
  ∩ environment identity, filesystem, network, and data policy
  ∩ recorded human approval
```

Client-specific instructions, skills, commands, custom agents, and hooks are projections. External
identity, sandbox, egress, CI rulesets, policy decision points, and deployment admission are the durable
guardrails. A documentation mapping is not runtime conformance, and a green local test is not owner
acceptance or certification.

## Validation layers

1. JSON Schema validation for shape and strict unknown-field rejection.
2. Package validation for instruction resolution, policy identity, catalog lineage, and deterministic
   orchestration invariants.
3. Semantic validation for registry references, identity-based duplicates, glob containment, handoff
   cycles, secret/URL scanning, and authority intersections.
4. Adapter golden/negative tests and deterministic projection digests.
5. Real client/model/tool conformance tied to the exact runtime tuple.
6. External risk-owner admission with expiry, monitoring, incident response, and revocation.
