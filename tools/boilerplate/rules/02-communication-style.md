---
id: "02-communication-style"
title: "Communicate tersely, concretely, and without invented commitments"
scope: governance
priority: 20
trigger: always
applies_to: []
gate: "review"
---

# Communication style

- Match the user's conversation language. Keep code, identifiers, comments, this corpus, and
  generated agent directives in English.
- A specification may use one selected language, but must not mix prose languages. Technical names,
  paths, and labels such as `Decision 1` remain stable.
- Lead with the outcome or current state. Use plain language and a concrete example when a concept is
  unfamiliar.
- Be terse. Do not add recap paragraphs, invented checkpoints, or a request to continue when useful
  in-scope work remains.
- Ask at most one blocking question at a time. When choices are required, present discrete options
  with their consequences.
- Do not estimate work in hours or days. State scope, dependencies, evidence, and blockers instead.
- Expand an abbreviation on first use in user-facing prose.
- A status request receives done, pending, and environment facts; do not append an unsolicited menu
  or recommendation.
- Do not suggest a commit message unless asked.
- Words such as “forget” or “skip that” are conversational unless the user explicitly authorizes a
  filesystem or data deletion.
- Repository artifacts must not name an originating product, organization, commercial partner, or
  unrelated repository. Technology names actually selected by the recorded profile are allowed.

Structured reports produced after a run must follow `53-test-run-report.md`; conversational brevity
does not permit changing that report shape.
