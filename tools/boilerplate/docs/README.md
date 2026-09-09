# kt-scaffold documentation

This directory is the user-facing entry point for the boilerplate generator and the projects it
creates.

- [Türkçe dokümantasyon](tr/README.md)
- [English documentation](en/README.md)
- [Global MCP knowledge-plane contract](global-mcp.md)

The Turkish and English trees follow the same numbering and subject order. The executable code,
versioned rules, generated templates and tests remain authoritative when prose and behavior
disagree. The guides explain those contracts; they do not create a second governance source.

## Document scope

The repository has three distinct documentation audiences:

1. **Platform users** create a project, accept a PRD, implement a vertical capability and produce
   evidence. Start in `tr/` or `en/`.
2. **Agent and platform integrators** connect Claude Code, Codex, Cursor or VS Code Local Agent and
   may register the global MCP scaffolding and governance plane. See the overview and
   `global-mcp.md`.
3. **Boilerplate maintainers** change generator code, templates, rules and test contracts. The root
   `README.md`, source tree and test suite are their primary references.

Implementation plans under `plans/` are working records, not product documentation. Decision and
capability claims should be backed by current automated tests, local run records or cited official
sources.
