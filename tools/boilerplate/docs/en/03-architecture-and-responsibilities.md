# Architecture and responsibilities

## Two-plane model

`kt-scaffold` deliberately separates two planes:

1. **Local application plane:** the CLI, coding client and generated repository. File changes,
   tests, database work, browser scenarios and evidence stay here.
2. **Central governance plane:** the internal Streamable HTTP MCP. It serves bounded blueprint and
   versioned governance knowledge without receiving workspace content or initial-project bytes.

This separation is a core closed-network security boundary. The local MCP receives only bounded
answers and its startup-bound root; source, patches, secrets, database content and dependency trees
remain outside the remote MCP contract.

## Two bootstrap modes

| Mode | Tool | Valid result claim |
|---|---|---|
| Deterministic bootstrap | Local stdio `project_create`, or approved pinned CLI/OCI package | Managed files are byte-identical from the same inputs and generator version after tree-digest verification |
| Intent bootstrap | A running local agent + MCP `project_blueprint` | The agent applies architecture intent with local tools; generator byte-equivalence is not claimed |

An empty directory has no `AGENTS.md`, rules or skills yet. Trusted local MCP invokes the installed
transactional generator directly. Intent bootstrap remains a specialized integration path requiring
normal drift and quality gates.

## Generated repository map

| Path | Purpose |
|---|---|
| `technology-profile.yml` | Human- and machine-readable summary of fixed technology decisions |
| `.kt-scaffold/answers.yml` | Non-secret scaffold inputs |
| `.kt-scaffold/project-manifest.json` | Bounded project/governance metadata safe to send to MCP |
| `.kt-scaffold/managed-manifest.json` | CLI-local managed-file state; never sent to MCP |
| `.kt-scaffold/agent-projections/` | Selected inert Agent Platform outputs and projection lock; not live client configuration |
| `specs/<domain>/` | Domain context, roadmap, PRDs, plans and tasks |
| `rules/` | Versioned source engineering rules |
| `AGENTS.md`, `CLAUDE.md`, `.claude/rules/`, `.claude/skills/`, `.codex/skills/`, `.cursor/rules/` | Engineering-governance projections of the same rules |
| `app/backend/`, `app/frontend/` | Application layers |
| `schema/` | Persistence desired state and migration contract |
| `e2e/` | Browser scenarios and quality manifest |
| `scripts/` | Approved local operation entry points |

## Trust boundaries

- The CLI operates only in the explicit target directory. A quality operation that executes a
  project-owned script requires `--allow-project-code-execution` as an explicit trust statement.
- The MCP application refuses a direct non-loopback bind for Streamable HTTP. Enterprise access is
  provided through the OAuth 2.1/TLS gateway sidecar.
- The MCP request-body contract stays bounded and is not enlarged to transfer source.
- Secrets and mTLS material are never committed to a repository or MCP registration file.
- Dependencies and scanner material come only from bank-admitted, digest-bound offline inventory.

## Authority and drift

The source rules corpus is rendered into client-specific files. If a developer edits a projection
directly, `scripts/check-governance-drift.py` and render check expose the difference. Product needs
belong in an accepted PRD rather than silently overriding a central rule.

Agent Platform custom-agent outputs have a separate compiler, lock and activation boundary. An
inert output under `.kt-scaffold/agent-projections/` must not be confused with an activated discovery
file or an admitted client/runtime tuple.

Governance artifacts use three authority classes:

- `mandatory`: preserve required behavior; local wording and stronger constraints are allowed;
- `recommended`: accept, adapt, defer or reject with rationale;
- `project-owned`: the central service does not replace local content.

Next: [Spec, PRD, plan and task lifecycle](04-spec-prd-plan-task.md).
