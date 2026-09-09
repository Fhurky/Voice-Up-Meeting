# MCP guide

Project creation and central governance use two explicit MCP authority surfaces.

## Local project creation

Register the approved installed package as a stdio server and bind it to the open workspace:

~~~json
{
  "servers": {
    "kt": {
      "type": "stdio",
      "command": "kt-scaffold",
      "args": ["mcp", "--workspace-root", "${workspaceFolder}"]
    }
  }
}
~~~

Prefer a user/organization registration so the selected project folder can begin completely empty.
The generated project contains no MCP registration.

Select `project_start` or call `project_create` directly. After one business summary/confirmation,
the tool calls the installed generator in-process. It uses no archive download, runtime applicator,
terminal command or model-authored file loop. Require a `local-mcp-observed` receipt whose expected
and observed tree digests match.

VS Code may show the registered prompt as `/mcp.kt.project_start`; this is client UI syntax only.

The tool schema has no target path. Server startup fixes the root, and the client sandbox should allow
writes only there. Unsafe/non-empty unowned roots fail closed. An exact retry returns `unchanged`.

For a VS Code/Copilot scaffold, send:

~~~json
{"agent_clients": ["github-copilot-vscode"]}
~~~

This compiles only VS Code projections into the inert store. Live `.github/agents/` activation remains
a separate conformance/admission step.

## Remote governance

The internal Streamable HTTP service exposes blueprint and governance operations only:

~~~sh
kt-scaffold mcp --transport streamable-http \
  --host 127.0.0.1 --port 8000 --path /mcp
~~~

It has no project-start prompt, creation tool, target path, bundle, applicator or executable download.
The service remains behind the organization OAuth/TLS gateway; the Rancher LAB sidecar is only a
transport verification boundary.

## Governance update flow

1. Export only `.kt-scaffold/project-manifest.json` with the generated helper.
2. Call `governance_update_check`.
3. Retrieve only selected changed artifacts.
4. Apply changes locally and run the project quality/database/browser gates.
5. Call `reconciliation_validate` with one decision per item.

The reconciliation receipt is not project-execution evidence.

Schema summary: [MCP tools](reference/mcp-tools.md).
