# Directory and file reference

| Path | Owner / purpose |
|---|---|
| `technology-profile.yml` | Platform owner; fixed technology profile |
| `rules/` | Governance source and input to client projections |
| `agent-platform/` | Canonical custom-agent contracts, six-client capability matrix, schemas and dated conformance records |
| `src/kt_scaffold/` | Generator, CLI, MCP and operation implementation |
| `src/kt_scaffold/templates/` | Content copied/rendered into generated repositories |
| `tests/` | Executable boilerplate acceptance/regression contract |
| `packaging/` | Offline wheel/npm/browser/OCI bundle preparation and locks |
| `docs/` | Boilerplate user and integration guides |
| `mockups/` | Decision reports and presentation output; not a runtime source |
| `plans/` | Working/design records; not user product documentation |

Generated projects additionally contain:

| Path | Owner / purpose |
|---|---|
| `.kt-scaffold/` | Generator state, bounded manifest and evidence |
| `.kt-scaffold/agent-projections/` | Selected inert custom-agent outputs and `PROJECTIONS.lock.json`; not a live discovery root |
| `specs/` | Domain-first product contract |
| `app/backend/` | Python/FastAPI layers |
| `app/frontend/` | React/Vite SPA |
| `schema/` | Desired-state persistence authority and migrations |
| `e2e/` | Durable browser acceptance scenarios |
| `scripts/` | Operational entry points used instead of ad-hoc commands |
| `.github/workflows/` | Egress-denied CI contract |
| `docs/en/`, `docs/tr/` | Project-specific end-user documentation |
| `.codex/agents/`, `.claude/agents/`, `.github/agents/`, `.cursor/agents/` | Client-native live custom-agent discovery roots; populated only through authorized Agent Platform activation |

Find source authority before editing a managed/client projection. Engineering-governance files such
as `AGENTS.md`, `CLAUDE.md`, `.claude/rules/`, `.claude/skills/`, `.codex/skills/` and
`.cursor/rules/` come from `rules/`. Agent Platform custom-agent artifacts come from the canonical
contracts and compiler, remain inert in `.kt-scaffold/agent-projections/`, and require a separate
activation/admission boundary. Change product requirements in `specs/`, never in a generated output.
