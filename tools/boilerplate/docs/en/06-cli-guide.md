# CLI guide

The CLI is the local deterministic application surface. Every command returns one line of
sorted-key JSON. A successful result has `ok: true`; contract/input errors generally use exit code
2, while an unresolved operation result uses exit code 1. Automation should evaluate this
structured result rather than only a human-readable message.

## Command families

| English | Turkish alias | Purpose |
|---|---|---|
| `init` | `baslat` | Create a deterministic scaffold in an empty directory |
| `update` | `guncelle` | Apply answer changes to managed files locally |
| `rules` | `kurallar` | List the rule inventory with filters |
| `rule` | `kural` | Retrieve requested rule bodies |
| `render` | `yansit` | Write client projections or check their drift |
| `spec` | `spesifikasyon` | Create a draft PRD, plan, tasks and roadmap entry |
| `domain` | `alan` | Prepare a backend vertical-slice skeleton from an accepted PRD |
| `page` | `sayfa` | Prepare a permission-protected frontend page from an accepted PRD |
| `schema` | `sema` | Prepare desired-state/migration work for an accepted PRD |
| `gate` | `kalite-kapisi` | Execute or prepare/finalize local quality evidence |
| `scenario` | `senaryo` | Create an acceptance-linked browser scenario that initially fails |
| `done` | `tamamla` | Report a delivery level from recorded evidence |

`mcp` / `mbp` starts either the trusted local stdio surface or the workspace-blind HTTP governance
surface; it is not one of the project operation pairs above.

## Target directory

When `--target-dir` is omitted for project commands, the CLI resolves the project root from the
current directory. Give an explicit target in automation to reduce ambiguity. Project operations
other than `init` fail outside a directory with a scaffold manifest.

~~~sh
kt-scaffold rules --target-dir ./payment-reconciliation --scope backend
kt-scaffold rule --target-dir ./payment-reconciliation 10-spec-first 50-quality-gate
kt-scaffold render --target-dir ./payment-reconciliation --mode check
~~~

## Updates and conflicts

~~~sh
kt-scaffold update --target-dir . --set product_name="New Product Name"
~~~

`update` computes the local file set from generator answers and the managed manifest. If it cannot
safely merge a user-modified managed file, the result reports a conflict; silent overwrite is not
success. No alternative value is accepted for the fixed backend/persistence fields.

## Trust confirmation for quality gates

`gate --phase execute` may run the target project's `scripts/quality-gate.sh`. Trust in the CLI
package is not automatic trust in a project-owned script in the target repository:

~~~sh
kt-scaffold gate --target-dir . --scope all \
  --include-browser --allow-project-code-execution
~~~

Remote runners can use the prepare/finalize protocol: `prepare` returns a challenge and expected
command; the runner captures raw output; `finalize` uses that output, exit code and challenge to
create bounded evidence. Validation fails when the challenge or stable `KT_GATE_*` lines do not
match.

Use `kt-scaffold <command> --help` for every option. Summary reference:
[Commands](reference/commands.md).
