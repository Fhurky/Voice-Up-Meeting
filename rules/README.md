# Canonical Rule Corpus

This directory is the only authored source for agent-facing project rules. Client-specific
instructions, skills, editor rules, and the spec-tool constitution are rendered from this corpus.
Generated copies are outputs: change the source rule here and regenerate them; never repair drift by
editing a generated copy.

## File contract

- One rule lives in one `<priority>-<slug>.md` file.
- Every rule starts with YAML front matter validated by `corpus.schema.json`.
- `id` is stable, unique, and equal to the filename without `.md`.
- `title` is a one-line imperative or invariant.
- `scope` is one of `governance`, `process`, `backend`, `frontend`, `schema`, `deployment`, or
  `quality`.
- `authority` defaults to `recommended`; mandatory behavior must declare `authority: mandatory`
  explicitly. Canonical rules never use `project-owned`, which is reserved for local inventory.
- `priority` orders rules inside a scope; lower values render first.
- `trigger` is `always`, `path-match`, or `on-demand`.
- `applies_to` contains repository-relative glob patterns. It is empty only for repository-wide
  rules.
- `gate` names the check that enforces the rule, or `none` when enforcement is review-only.
- The Markdown body must state observable behavior, affected paths, and a verification method.

Example:

```markdown
---
id: "20-example"
title: "Keep the example boundary explicit"
scope: backend
priority: 20
trigger: path-match
applies_to:
  - "app/backend/**"
gate: "backend-test.yml"
---
```

## Authoring rules

1. Keep product intent and domain vocabulary in `.kt-scaffold/answers.yml` and `specs/`; do not
   hardcode a product, organization, commercial partner, or industry into this corpus.
2. State profile-independent invariants here. When behavior differs by backend or persistence
   profile, route the reader to `.kt-scaffold/answers.yml` and `schema/profile.yml` and describe each
   supported branch explicitly.
3. Do not duplicate prose between corpus files. Link to the owning rule when another concern depends
   on it.
4. Do not put incidents, dates, migration history, or temporary exceptions into evergreen rules.
5. Add a gate with a rule whenever behavior is mechanically checkable. A gate name without a real
   check is not enforcement.
6. Keep rule bodies in English. Generated labels and user-facing prose may be localized by their
   owning rule.

## Change workflow

1. Edit or add the smallest owning corpus file.
2. Validate all front matter against `corpus.schema.json` and reject duplicate IDs or priorities.
3. Render every supported client.
4. Run `scripts/render-clients.sh --check` and the gate named by the changed rule.
5. Commit the corpus change and regenerated outputs together.
