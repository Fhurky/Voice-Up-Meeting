---
id: "41-schema-mandatory-columns"
title: "Apply one mandatory lifecycle and audit shape to domain tables"
scope: schema
authority: mandatory
priority: 50
trigger: path-match
applies_to:
  - "schema/**"
  - "app/backend/**/domain/**"
gate: "mandatory-column-check"
---

# Mandatory table shape

Encode the mandatory block once in the SQLAlchemy profile as a shared mixin or base type. Do not copy
a slightly different version into each domain. Migrated-schema tests, not source text alone, prove
the database agrees with the authority.

Every applicable domain table carries:

| Element | Contract |
|---|---|
| Internal identity | `<table>_id`, database-generated, never exposed through the API |
| Public identity | `public_id` text, non-null and unique for externally addressable resources |
| Overflow | `props`, native binary JSON, non-null with an empty-object default |
| Audit | `created_at`, `updated_at`, `created_by`, `updated_by` |
| Soft delete | `is_deleted`, `deleted_at`, `deleted_by` |
| Active lookup | a partial index restricted to rows where `is_deleted` is false |
| Time | timezone-aware timestamps stored and compared in UTC; reject naive values |
| Semantics | a table description plus descriptions for important enums, links, and overflow keys |

Junctions, mappings, locale sidecars, and append-only streams use a stable natural/composite key when
that key already provides identity; do not add a meaningless `public_id`. Any deviation from the rest
of the block must be stated in the accepted PRD and asserted by the migrated-schema gate rather than
introduced silently.

Services perform soft delete by setting the flag, timestamp, and actor together. Default reads exclude
deleted rows; explicit audit/recovery paths may include them. Do not implement an `updated_at` trigger
when the recorded profile owns update timestamps in its persistence layer.

Keep schema authority, generated migration, persistence types, and API serialization aligned in the
same change.
