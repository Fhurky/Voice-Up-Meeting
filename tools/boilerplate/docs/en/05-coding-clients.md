# Coding clients and Agent Platform

## Two distinct projection layers

The product has two client-facing layers that share canonical governance but have different
artifacts and evidence boundaries.

### Engineering-governance projections

The established baseline renders `rules/` and operational skills for four coding environments:

| Environment | Repository instruction surface | Closed-network position |
|---|---|---|
| Claude Code | `CLAUDE.md`, `.claude/rules/`, `.claude/skills/` | A zone allowing required Anthropic services |
| Codex | `AGENTS.md`, `.codex/config.toml`, `.codex/skills/` | A zone allowing required OpenAI services |
| Cursor | `.cursor/rules/*.mdc` | A zone where Cursor services and data policy are approved |
| VS Code Local Agent | `AGENTS.md`, `.claude/rules/`, `.claude/skills/` | Default for a fully closed network with bank-hosted Ollama/Qwen or a compatible gateway |

These are delivery projections of one rule corpus, not four independent standards. Claude Code,
Codex and Cursor remain approved-zone options. Pointing a provider endpoint at a local model does
not automatically make a client's authentication, telemetry and session behavior closed-network or
admitted.

### Agent Platform custom-agent projections

The Agent Platform compiler has four native adapter targets:

| Adapter target | Inert output shape | Live discovery root after authorized activation |
|---|---|---|
| Codex | TOML custom agents | `.codex/agents/` |
| Claude Code | Markdown subagents | `.claude/agents/` |
| GitHub Copilot in VS Code | `.agent.md` files | `.github/agents/` |
| Cursor | Markdown custom agents | `.cursor/agents/` |

`kt-scaffold init --agent-client ...` and `kt-scaffold render --agent-client ...` compile only the
selected custom-agent outputs under `.kt-scaffold/agent-projections/`. That store is inert. A
projection becomes discoverable only through the separate, transactional activation boundary after
verification of a disposable conformance grant or a signed, time-bound admission receipt for the
exact client/model/tool/policy/environment tuple.

Adapter implementation is not runtime support. The current contract records four implemented
serializers and 16 deterministic outputs, but no exact tuple is admitted. Real-client conformance,
owner admission and independent certification remain separate states.

## Rendering and drift

Use `--client` for engineering-governance projections and `--agent-client` for inert Agent Platform
custom-agent outputs:

~~~sh
kt-scaffold render --target-dir . --mode check
kt-scaffold render --target-dir . --agent-client codex --mode check
~~~

Do not repair either generated form in isolation. Change its canonical source, rerender, and inspect
the projection lock, conflicts and warnings. Ordinary project update replays the persisted Agent
Platform selection; changing that immutable selection requires a future governed migration.

## Starting a new session

Conversation history may persist or reset depending on the client. For every new task, the agent
should reread at least:

1. the applicable root and path-scoped instructions;
2. `technology-profile.yml`;
3. `specs/<domain>/DOMAIN.md`;
4. the accepted `PRD.md`, `plan.md` and `tasks.md`;
5. the current diff and latest independent test evidence;
6. when custom agents are active, the activation receipt and its exact runtime scope.

Example starting request:

> Read the relevant repository instructions, technology profile and accepted PRD/plan/tasks. Keep
> the existing diff intact. First summarize scope-to-acceptance traceability, then implement tasks
> in order and report only tests you actually executed as evidence.

## Evidence required before use

For an engineering coding environment, validate instruction discovery, accepted-PRD enforcement,
traceable multi-file work, tool and test execution, preservation of unrelated changes, browser
acceptance where applicable, and honest reporting of unexecuted checks.

For an Agent Platform runtime tuple, additionally validate native custom-agent discovery and direct
invocation, instruction precedence, effective tool and permission boundaries, denial behavior,
delegation, injection/exfiltration resistance, audit, drift, rollback and exact start/end version and
digest equality. Only then may the accountable owner issue a separate, expiring admission receipt.

The dated Local Agent PoC and historical four-environment comparison remain in
`mockups/03-kapali-devre-agentic-kodlama-raporu.html`. They do not replace the four-target Agent
Platform conformance matrix and are not production approval for future clients, models, hardware or
versions.

Next: [CLI guide](06-cli-guide.md).
