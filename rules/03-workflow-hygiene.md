---
id: "03-workflow-hygiene"
title: "Keep repository mutation explicit, reversible, and user-owned"
scope: governance
authority: mandatory
priority: 30
trigger: always
applies_to: []
gate: "review"
---

# Workflow hygiene

Version-control publishing is user-owned. Do not stage, commit, push, tag, rewrite history, create or
merge a pull request, or change branches unless the user explicitly requested that exact operation.
Read-only status, diff, and history inspection are allowed. Preserve unrelated user changes in a
dirty worktree.

Before writing an ad-hoc command or helper, inspect `scripts/` and use the existing wrapper. Do not
leave one-off scripts, debug artifacts, or generated output in the repository. Never hide incomplete
work with a stub, commented block, stale marker, or fabricated passing result.

Do not initiate delivery phases or park part of an accepted scope. When scope genuinely separates,
create another roadmap-linked PRD with its own acceptance criteria; do not bury it in a “later” note.
Finish the layers required by the accepted PRD in one coherent change.

Destructive data or filesystem operations require explicit authorization naming the destructive
action and target. Resolve the exact target read-only first. Database migrations may be applied from
a developer environment only to the local database; deployment environments use the migration
release.

Generated governance files are read-only outputs. Change `rules/`, regenerate all clients, and run
the drift gate. Scaffold updates never silently overwrite team-edited files and never silently delete
files removed from a later template.

`project_init` requires resolved project intent and profiles, refuses a non-empty target, renders to a
sibling staging directory, validates the whole tree, and publishes through a journaled transaction. It
has no dry-run or trial-scaffold mode. On failure it rolls back only init-owned paths. Later generators
write atomically and refuse conflicts rather than overwriting an existing team file.

The global MCP surface is a blueprint and governance knowledge plane. Never upload workspace source,
secrets, dependency trees, database data or a full filesystem snapshot to it. The local agent owns
all repository mutation, code execution, tests and evidence. Reconcile MCP update intents against the
local copy, preserve every mandatory behavior, and record accepted, adapted, deferred or rejected
decisions before changing locally owned governance files.
