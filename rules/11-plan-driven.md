---
id: "11-plan-driven"
title: "Derive implementation plans and tasks from accepted specifications"
scope: process
priority: 20
trigger: always
applies_to: []
gate: "done_report"
---

# Plan-driven delivery

Use top-level `plans/` for pre-decision exploration, audits, and architecture work that has not yet
become an accepted capability. It is not a second requirements store.

After a PRD is accepted, derive `plan.md` and `tasks.md` beside that PRD. The plan maps every affected
layer, file class, migration/deployment dependency, and verification command back to a requirement or
acceptance criterion. Tasks are ordered, independently checkable steps; each task names its output and
evidence. Do not place implementation decisions only in chat.

When discovery changes scope, update the PRD first. When a capability splits, add a separate roadmap
row and PRD with its own definition of done. Do not label unowned work “phase two”, “future”, “stale”,
or “out of scope” unless the owner explicitly made that decision and the roadmap records it.

A completed plan has no silently skipped task. `done_report` must name every incomplete task or
unsupported evidence tier. Once a top-level exploratory plan is absorbed by accepted specifications,
remove or clearly mark the duplicate through a user-authorized change so requirements do not drift in
two places.
