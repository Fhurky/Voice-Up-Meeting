# Spec, PRD, plan and task lifecycle

## Authority chain

An idea does not turn directly into code. The repository authority chain is:

`Domain context → Draft PRD → Human review → Accepted PRD → Plan → Tasks → Implementation → Evidence`

Each document answers a different question:

- `DOMAIN.md`: What does this bounded context own and not own?
- `PRD.md`: Which measurable outcome, boundary and acceptance criteria are required for which actor?
- `plan.md`: Which layers and validations change to satisfy the accepted criteria?
- `tasks.md`: What are the ordered, independently checkable outputs?

## Domain and roadmap

`init` creates `specs/<domain>/DOMAIN.md` and `roadmap.md` for the primary domain. A new capability
uses that domain language and ownership boundary. Create another domain for another bounded context;
do not accumulate unrelated work in a “misc” area.

## Creating and accepting a PRD

~~~sh
kt-scaffold spec --target-dir . \
  --domain payments \
  --capability transaction-search \
  --intent "Let an authorized operator find reconciliation transactions"
~~~

A new PRD starts with `Status: Draft`. Make its actor/outcome, invariants, authorization,
data/migration impact, operational risk and acceptance criteria concrete. If part of the scope is
independently deliverable, create another PRD instead of parking it in an ambiguous “later” note.

After review, the human owner records the `Status: Accepted` decision. The `domain`, `page`, `schema`
and `scenario` commands reject a draft or missing PRD.

## Plan and tasks

The plan maps every acceptance criterion to affected layers: desired schema, migration, backend
domain/service/API, authorization, frontend, localization, observability, unit/integration and
browser evidence. Give a rationale for a non-affected layer rather than silently skipping it.

Tasks are ordered and executable. Each task names:

- the file or behavior it produces;
- its linked acceptance criterion;
- the test or gate proving completion;
- any preceding task on which it depends.

Plans and tasks are not a second requirements store. If they conflict with the PRD, stop and present
the conflict to the owner.

## Implementation and scenarios

Pass the same accepted `spec_path` to backend, schema, page and browser-scenario operations. This
trace preserves the link from generated code to requirement. `scenario` creates only a failing
guard and acceptance prose; the developer must add executable browser assertions before claiming
L2.

## Completion levels

| Level | Meaning |
|---|---|
| L0 | The change is written; no execution evidence |
| L1 | Relevant deterministic, unit and integration behavior was executed and passed |
| L2 | The domain-relevant real boundary also passed: HTTP/browser, real MCP session or exact client tuple |
| L3 | The accountable owner accepted or admitted the exact behavior/runtime scope with recorded evidence |

`kt-scaffold done` does not approve a level above the observed evidence in
`.kt-scaffold/evidence.json`. Skipped tests or client-reported success are not equivalent to
independent local or runner evidence.

For generated business capabilities, L2 normally means the live HTTP/browser path described above.
Project Factory and Agent Platform use their own Accepted PRD definitions for real MCP and exact-client
conformance; neither broadens the generated application's browser claim.

Next: [Coding clients](05-coding-clients.md).
