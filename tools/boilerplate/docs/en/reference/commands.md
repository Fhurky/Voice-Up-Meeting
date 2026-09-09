# Command reference

This summary explains the contract in `src/kt_scaffold/cli.py`. Use
`kt-scaffold <command> --help` as the authority for options in the installed version. Every Turkish
alias calls the same implementation as its English command.

| Command / alias | Required input | Important options |
|---|---|---|
| `init` / `baslat` | `--target-dir`; for non-interactive use, `--intent`, `--primary-domain` | `--answers`, `--product-name`, `--product-slug`, `--env-prefix`, `--api-prefix`, `--tenant-header`, `--locales`, `--[no-]observability`, repeatable `--agent-client` |
| `update` / `guncelle` | Project root | Repeatable `--set key=value` |
| `rules` / `kurallar` | Project root | `--scope`, `--path`, `--trigger always|path-match|on-demand` |
| `rule` / `kural` | One or more rule IDs | `--target-dir` |
| `render` / `yansit` | Project root | Repeatable `--client` for engineering-governance projections, repeatable `--agent-client` for inert Agent Platform outputs, `--mode write|check` |
| `spec` / `spesifikasyon` | `--domain`, `--capability`, `--intent` | `--mode lean|comprehensive` |
| `domain` / `alan` | Accepted `--spec-path` | `--[no-]tenant-scoped`, repeatable `--permission key=value` |
| `page` / `sayfa` | `--spec-path`, `--page`, `--route` | `--permission` |
| `schema` / `sema` | `--spec-path`, `--change-summary`, `--migration-name` | `--target-dir` |
| `gate` / `kalite-kapisi` | Project root | `--scope backend|frontend|all`, `--include-browser`, `--allow-project-code-execution`, `--phase execute|prepare|finalize` |
| `scenario` / `senaryo` | `--spec-path`, `--suite`, `--scenario-title`, at least one `--acceptance-point` | Repeatable acceptance point |
| `done` / `tamamla` | `--change-summary`, `--claimed-tier L0|L1|L2|L3` | `--target-dir` |
| `apply-bundle` / `paketi-uygula` | `--archive`, `--descriptor`, `--target-dir` | Applies only to an empty target or an exact retry of the same bundle |
| `mcp` / `mbp` | None | `--transport stdio|streamable-http`, `--workspace-root` for trusted local stdio creation, `--host`, `--port`, `--path` |

`--agent-client` accepts `claude-code`, `codex`, `cursor` and `github-copilot-vscode`. Selection
writes inert outputs and does not activate or admit a runtime.
`--workspace-root` grants creation authority only to the local stdio surface; Streamable HTTP rejects
that authority and remains workspace-blind.

## Common result envelope

Local operations use at least these fields:

- `ok`: whether the operation succeeded according to its contract;
- `changes`: file outcomes such as created, updated or conflict;
- `warnings`: facts limiting a success claim or requiring a user decision;
- `next_steps`: structured next local actions.

Operation-specific fields are added to this envelope, such as `spec_path`, `scenario_path`, evidence
counts or rendered-client lists. Do not build integrations that silently accept unknown input.

## Exit codes

- `0`: `ok: true`, or normal termination of the long-running MCP process;
- `1`: the operation ran but returned `ok: false`;
- `2`: input, validation, filesystem or execution-contract error.

In shell automation, inspect both the exit code and JSON `ok/warnings/changes` fields.
