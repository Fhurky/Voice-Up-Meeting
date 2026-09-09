# Local Project Factory and remote governance MCP

`kt-scaffold` exposes two explicit authority surfaces from one installed package. They are not
transport aliases for the same powers.

| Surface | Capability | Workspace authority |
|---|---|---|
| Trusted local stdio | Deterministic creation, blueprint and governance | One explicit root fixed at process startup |
| Internal Streamable HTTP | Blueprint and governance | None |

Generated projects contain no MCP registration. Client or organization configuration owns the
registration, executable pin and sandbox policy.

There is no universal MCP client configuration file. VS Code uses a `"servers"` object (for
example in user configuration or `.vscode/mcp.json`), while Claude Code, Cursor and several other
clients use a client-owned `"mcpServers"` object. Use each vendor's supported registration surface;
do not copy one client's JSON shape into another. Generated governance remains separate:
`AGENTS.md`, `.claude/rules/` and `.claude/skills/` are repository instructions, not MCP transport
configuration.

## Deterministic bootstrap: trusted local stdio creation

The local client starts the approved package with the selected workspace root:

~~~json
{
  "servers": {
    "kt": {
      "type": "stdio",
      "command": "kt-scaffold",
      "args": ["mcp", "--transport", "stdio", "--workspace-root", "${workspaceFolder}"]
    }
  }
}
~~~

Use the equivalent client-native configuration for Claude Code, Codex, Cursor, or VS Code/Copilot.
The command and behavior are vendor-neutral.

The local surface provides six bilingual tool pairs:

- `project_create` / `proje_olustur` invokes the installed generator in-process and transactionally
  publishes a complete scaffold in the fixed root;
- `project_blueprint` / `proje_plani` returns bounded architecture metadata;
- `governance_catalog` / `yonetisim_katalogu` lists canonical artifact metadata;
- `governance_artifacts_get` / `yonetisim_ogelerini_getir` fetches selected bodies;
- `governance_update_check` / `yonetisim_guncellemelerini_kontrol_et` compares bounded project
  metadata;
- `reconciliation_validate` / `uyumlastirmayi_dogrula` validates local decisions.

It also provides `project_start` / `proje_baslat`. The prompt collects only missing business context,
shows one summary/confirmation, then invokes the matching local creation tool.

In VS Code's prompt picker the same local registration may appear as `/mcp.kt.project_start` or
`/mcp.kt.proje_baslat`; that notation is client UI syntax, not an MCP method name.

The workspace root is not a tool input. `project_create` accepts product intent, primary domain,
product identity, locales, tenant header, observability and optional Agent Platform client selection.
It rejects unknown fields. It does not download or execute Python/shell artifacts, run project code,
invoke package managers or execute VCS commands.

The result is bounded and contains no source bodies:

~~~json
{
  "ok": true,
  "receipt": {
    "provenance": "local-mcp-observed",
    "status": "created",
    "file_count": 0,
    "entry_count": 0,
    "expected_tree_digest": "<sha256>",
    "observed_tree_digest": "<same-sha256>"
  }
}
~~~

The real counts are non-zero. The abbreviated example documents shape only.

## Workspace safety

Local creation accepts an existing explicit directory that is empty. It rejects filesystem root,
user home, symlink roots, non-directories and non-empty unowned content. Publication is staged beside
the target and swapped transactionally. An exact completed retry returns `unchanged`; partial,
edited, divergent or unowned content fails without overwrite.

The client should additionally sandbox the MCP process with write access limited to the same
workspace. That sandbox is defense in depth; the server still enforces its own root binding.

## Intent bootstrap: remote governance plane

The HTTP server starts without `--workspace-root`:

~~~sh
kt-scaffold mcp --transport streamable-http \
  --host 127.0.0.1 --port 8000 --path /mcp
~~~

It exposes five bilingual blueprint/governance pairs. It has no start prompt, `project_create`,
`project_scaffold`, bundle resource, applicator resource or executable download route. It never
receives a target path, source tree, workspace snapshot, secret, database content or VCS state.

The application binds loopback only. A production deployment places the organization OAuth/TLS
gateway in front. The Rancher LAB chart uses an unprivileged streaming Nginx sidecar for verification;
that sidecar is not a production identity boundary.

Example internal client configuration:

~~~json
{
  "servers": {
    "kt-governance": {
      "type": "http",
      "url": "https://mcp.bank.example/kt-scaffold/mcp"
    }
  }
}
~~~

## Agent Platform selection

`project_create` and CLI `init` may receive one or more `agent_clients`. The selection is persisted in
`.kt-scaffold/answers.yml`, and ordinary update replays the same set. Initialization compiles only the
selected client projections under `.kt-scaffold/agent-projections/`.

Those files are inert. Writing a VS Code projection into `.github/agents/`, a Codex projection into
`.codex/agents/`, or another client discovery path remains a separate Agent Platform
activation/admission operation. Creation does not silently claim runtime conformance.

## CLI and controlled offline import

`kt-scaffold init` calls the same renderer and must produce the same observed digest as local MCP for
identical normalized answers. `apply-bundle` remains a preinstalled CLI for controlled offline import;
MCP does not distribute it or instruct a model to download executable code.

## Evidence boundary

- `local-mcp-observed`: initial local tree bytes and counts were independently observed.
- `local-agent-attested`: governance reconciliation decisions were structurally validated.
- local quality/database/browser gates: project execution evidence.
- client conformance/admission: separate Agent Platform evidence.

None of these labels implies another.
