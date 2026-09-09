# Manifest reference

| File | Content | Sent to MCP? |
|---|---|---|
| `.kt-scaffold/answers.yml` | Non-secret scaffold inputs and generator version | No |
| `.kt-scaffold/project-manifest.json` | Blueprint/governance version, intent/domain, fixed profiles, locales and content-addressed artifact inventory | Yes, as `governance_update_check` input |
| `.kt-scaffold/managed-manifest.json` | State/digests of CLI-managed local files | No |
| `.kt-scaffold/evidence.json` | Local/runner test provenance, level and observed counts | No |
| `dependency-admission.json` | Direct package, OCI and workflow-action admission inventory | No |
| `e2e/QUALITY_MANIFEST.md` | Browser suite, scenario and acceptance trace | No |

`scripts/export-project-metadata.py` emits only bounded `project-manifest.json` fields to stdout and
does not walk the workspace. The output still contains product intent and internal artifact IDs, so
send it only to an approved bank MCP endpoint.

Manifest version/digest order is: apply change → run local gates → obtain reconciliation receipt →
record user/owner acceptance → advance inventory. Advancing first hides drift.
