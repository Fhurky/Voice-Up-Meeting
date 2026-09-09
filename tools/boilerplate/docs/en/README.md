# kt-scaffold — English user guide

`kt-scaffold` creates a spec-first application repository suitable for closed-network operation
from an empty directory. The result is more than a folder template: it carries the fixed technology
profile, architecture rules, agent instructions, local runtime, quality gates and evidence contract
as one baseline.

This guide answers three questions:

- **What?** Product scope, fixed decisions and evidence model.
- **Where?** Location of source rules, PRD/plan/task documents, agent projections and operational
  scripts.
- **How?** The path from the first scaffold to an accepted business capability and verified
  delivery report.

## Reading order

1. Read the [overview](01-overview.md) for the product boundary and component responsibilities.
2. Follow the [quick start](02-quick-start.md) to generate a project and exercise the spec-first
   workflow.
3. If you use MCP, read the [global MCP contract](../global-mcp.md). MCP is not a filesystem service
   that reads a workspace or installs the scaffold remotely.

## Guides

- [Architecture and responsibilities](03-architecture-and-responsibilities.md)
- [Spec, PRD, plan and task lifecycle](04-spec-prd-plan-task.md)
- [Coding clients](05-coding-clients.md)
- [CLI guide](06-cli-guide.md)
- [MCP guide](07-mcp-guide.md)
- [Updates and reconciliation](08-updates-and-reconciliation.md)
- [Quality, evidence and E2E](09-quality-evidence-and-e2e.md)
- [Closed-network operation](10-closed-network-operation.md)
- [Troubleshooting](11-troubleshooting.md)

## Reference

- [Commands](reference/commands.md)
- [MCP tools](reference/mcp-tools.md)
- [Directories and files](reference/directories-and-files.md)
- [Manifests](reference/manifests.md)
- [Evidence levels](reference/evidence-levels.md)
- [Glossary](reference/glossary.md)
- [Verification records](../evidence/README.md)

## Fixed principles

- The canonical engineering-rule corpus has established projections for Claude Code, Codex, Cursor
  and VS Code Local Agent. This four-environment baseline is distinct from Agent Platform runtime
  admission.
- The Agent Platform compiler has four inert adapter targets: Codex, Claude Code, GitHub Copilot in
  VS Code and Cursor. Selected output stays under
  `.kt-scaffold/agent-projections/`; generation does not imply conformance or admission.
- VS Code Local Agent is the default engineering environment for a fully closed network with a local
  model. The other established engineering environments are used only in network zones where their
  required services are approved.
- The backend and persistence profile is fixed: Python/FastAPI, async SQLAlchemy, asyncpg, Alembic
  and PostgreSQL.
- Business code starts only after `specs/<domain>/PRDs/<capability>/PRD.md` has `Status: Accepted`.
- An agent's “done” message is not evidence. Local tests, quality gates and approval records are
  authoritative.
- CLI and MCP are not the same surface: CLI and trusted local stdio creation produce identical
  deterministic bytes; HTTP MCP serves workspace-blind blueprint and governance contracts only.

## Language parity

Every numbered document in this directory has a Turkish counterpart with the same number under
`docs/tr/`. Turkish aliases for commands and MCP tools call the same implementation; JSON field
names and the machine contract are not translated.
