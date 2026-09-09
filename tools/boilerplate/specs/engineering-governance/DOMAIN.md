# Engineering Governance domain

Status: Draft

## Purpose

Engineering Governance owns the canonical engineering-rule corpus, deterministic projections into
supported repository discovery surfaces, and authority-aware distribution of governance changes
without treating a remote service as workspace authority.

## Actors

- Governance owner — authors mandatory and recommended engineering behavior.
- Rule maintainer — changes one canonical rule and regenerates deterministic projections.
- Application team — adapts centrally governed intent to an accepted local product need.
- Client user — receives equivalent discoverable guidance in an approved coding environment.
- Reviewer — detects projection drift and evaluates reconciliation decisions.

## Ubiquitous language

- **Corpus rule** — one stable, schema-validated source rule with scope, trigger, clients, and gate.
- **Projection** — replaceable client-native output derived from the canonical corpus.
- **Artifact authority** — `mandatory`, `recommended`, or `project-owned` ownership class.
- **Update proposal** — deterministic delta computed from bounded project metadata and canonical
  inventory.
- **Reconciliation receipt** — integrity-bound record of local decisions, not proof of workspace
  application or execution.

## Invariants

1. Canonical rule bodies are authored once; client files are generated outputs.
2. Hand edits to projections are detectable and recoverable but are not claimed to be impossible.
3. The central MCP receives bounded inventory metadata, never repository source or managed-file state.
4. Mandatory behavior may be reworded or strengthened but not silently weakened, deferred, or rejected.
5. Project-owned artifacts remain outside central control.
6. Reconciliation attests decisions only; local application and gates remain separate evidence.

## Owned data and artifacts

- Rule corpus schema, source rules, render mapping, and projection drift contract.
- Governance artifact catalog, authority classes, update proposal, decisions, and receipt semantics.
- Bilingual project command-skill projections and local reconciliation guidance.

## Upstream boundaries

- Organization engineering policy and accepted technology decisions.
- Capability PRDs that justify local adaptation.
- Documented client discovery formats.

## Downstream boundaries

- Generated repository instruction, rule, skill, command, and constitution files.
- Project Factory initial managed tree and later local update workflow.
- Agent Platform contracts that reference canonical rules symbolically.

## Explicit non-responsibilities

- Defining portable custom-agent manifests or client runtime conformance; Agent Platform owns those.
- Granting tool, filesystem, identity, network, or deployment authority.
- Executing project code or remotely verifying that a reconciliation was applied.
