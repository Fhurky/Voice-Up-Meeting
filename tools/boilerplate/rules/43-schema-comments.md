---
id: "43-schema-comments"
title: "Keep database semantics queryable through profile-native descriptions"
scope: schema
priority: 70
trigger: path-match
applies_to:
  - "schema/**"
  - "app/backend/**/domain/**"
gate: "schema-comment-check"
---

# Schema descriptions

Place durable table and column semantics in the selected schema authority when it can emit database
descriptions, or in a reviewed SQL migration when it cannot. A description explains present behavior,
not the history of a decision.

Descriptions are required for:

- every table's purpose and owning bounded context;
- enumerations and bit fields, including every defined value and the code mirror when one exists;
- cross-table and cross-boundary references, including the target and ownership semantics;
- `props` keys written by known code paths;
- compatibility fields not currently consumed by the application;
- non-obvious uniqueness, writer, retention, or lifecycle contracts.

Do not comment obvious type facts. Do not write ellipses or invent enum values. If no code mirror
exists, say so explicitly and keep the authority as the sole definition until the mirror is added.

Use present tense. Do not include incidents, dates, migration numbers, plan sections, commercial
partners, originating products, or industry-specific examples in generic schema descriptions. Domain
vocabulary is allowed only after an accepted domain PRD owns it.

Review description changes in the generated migration and verify them against the migrated database;
source-only comments that never reach the database do not satisfy this rule.
