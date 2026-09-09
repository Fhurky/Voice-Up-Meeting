# Overview

## What problem does it solve?

`kt-scaffold` binds the infrastructure decisions repeatedly debated on day one of an enterprise
application to one versioned baseline. The goal is not merely to let an agent generate files; it is
to trace one contract from requirement to code, and from tests to delivery evidence.

Each generated repository includes:

- a Python/FastAPI backend on PostgreSQL with Alembic migration authority;
- a separated React/Vite SPA, JWT/RBAC and an application-level `super_admin` baseline;
- local containers, deployment charts, dependency admission and closed-network scripts;
- spec, plan, task, schema, browser-scenario and Definition of Done workflows;
- instructions and skills derived from the same rules for four established coding environments;
- selected inert custom-agent projections compiled for four Agent Platform adapter targets.

No sample business entity is generated. Business scope enters the repository only through an
accepted PRD.

## Component responsibilities

| Component | Responsibility | Outside its authority |
|---|---|---|
| `kt-scaffold` CLI | Deterministic bootstrap, local file operations, client projections and quality/evidence helpers | Acting as a remote model or centralized coding service |
| Local stdio MCP | Invoke the installed generator inside one startup-bound workspace | Accept a model-supplied target, download executable code or run project commands |
| HTTP governance MCP | Serve blueprint intent, canonical inventory, update intent and reconciliation contracts | Receive caller source trees or gain workspace authority |
| Coding client | Select the workspace registration, inspect/edit later files, run tests and present evidence | Rewrite the initial scaffold from prose or substitute a success message for tests |
| Bank gateway | OAuth 2.1, TLS/mTLS, scopes, rate limits and audit identity | Forward public or unauthenticated traffic to the MCP application |
| Generated repository | Persist product requirements, accepted decisions, code and local evidence | Depend on transient chat history |

CLI and MCP are not identical authority surfaces. CLI and trusted local stdio creation must produce
the same digest. Streamable HTTP is workspace-blind and carries blueprint/governance only.

## Fixed technology profile

The caller or agent does not select an alternative backend or persistence stack. The validated
profile is:

- Python/FastAPI;
- async SQLAlchemy and asyncpg;
- PostgreSQL desired state governed by Alembic;
- PGVector inside the same PostgreSQL database when an accepted PRD owns the vector/embedding
  contract;
- a separated React/Vite SPA.

PGVector is an optional PostgreSQL capability rather than an alternative persistence engine. An
accepted capability must fix the embedding provider/model version, dimensions, distance metric,
index strategy, retrieval thresholds, tenant scope, data handling and re-embedding lifecycle.
Embedding generation uses an approved internal or on-premise adapter without runtime internet
egress or model downloads.

A Streamlit exception is available only for narrowly scoped products consisting entirely of prompt
input, chat and history, as permitted by `technology-profile.yml`. SSR and Next.js are not the
default profile.

## Two client layers, one governance source

The engineering-governance layer renders the canonical `rules/` corpus for four established coding
environments:

- **Claude Code:** `CLAUDE.md`, `.claude/rules/` and `.claude/skills/`.
- **Codex:** `AGENTS.md`, `.codex/config.toml` and `.codex/skills/`.
- **Cursor:** path-scoped `.cursor/rules/*.mdc` files.
- **VS Code Local Agent:** discovers `AGENTS.md` plus the `.claude/rules/` and `.claude/skills/`
  projections; the closed-network profile uses bank-hosted Ollama/Qwen or a compatible LLM gateway.

These are not four independent standards. Source rules are versioned, projections are rendered
from the same corpus, and drift checks compare their integrity.

The Agent Platform layer separately compiles four canonical custom agents into native-shaped
artifacts for Codex, Claude Code, GitHub Copilot in VS Code and Cursor.
Selected outputs stay inert under `.kt-scaffold/agent-projections/`. A generated artifact does not
become live client configuration until the separate activation boundary verifies a disposable
conformance grant or an exact-tuple admission receipt. Generation, real-client conformance and
runtime admission are never interchangeable claims.

## Context, sessions and durable memory

Four concepts must remain separate in a coding session:

- **Model context window:** the temporary content limit carried in one model request.
- **Client session/history:** the client-specific ability to reopen or continue a conversation.
- **Provider/API state:** server-side state such as a provider conversation identifier. Ollama's
  OpenAI Responses compatibility, for example, does not guarantee stateful conversations.
- **Repository memory:** `AGENTS.md`, rules, skills, spec/PRD/plan/task documents, manifests and test
  evidence. This is the durable, auditable source for long-running work.

Project continuity therefore rests on decisions written to the repository, not chat history. A new
session can continue safely by reading the same accepted PRD, plan, task list and rules.

## Source-of-truth order

If prose and behavior disagree, use this authority order:

1. `technology-profile.yml` — fixed technology decisions;
2. `rules/` — engineering and quality principles;
3. `src/kt_scaffold/` — actual CLI, MCP and generation behavior;
4. `src/kt_scaffold/templates/` — generated repository content;
5. `tests/` — executable acceptance and regression contract;
6. `docs/` — user guidance explaining those contracts;
7. `mockups/03-kapali-devre-agentic-kodlama-raporu.html` — portfolio decision and evidence summary.

Next: [Quick start](02-quick-start.md).
