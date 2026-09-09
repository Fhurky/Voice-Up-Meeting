# MCP tool reference

All schemas reject undeclared arguments. The local stdio and remote HTTP surfaces intentionally have
different authority.

## `project_start` / `proje_baslat` prompt

Local stdio only. It collects missing business purpose/domain/name, shows one summary, requests one
confirmation and then calls `project_create` / `proje_olustur`. It never asks for a target path,
technology, URL, archive, applicator, command or secret.

## `project_create` / `proje_olustur`

Local stdio only. Input contains product intent, primary domain, product name/slug, optional derived
prefixes, tenant header, locales, observability and optional `agent_clients`. The workspace root is
fixed at server startup and is not an input.

The installed generator creates the full tree in-process. The bounded result contains a
`local-mcp-observed` receipt, `created|unchanged` status, file/entry counts and equal expected/observed
tree digests. No source bodies, download references or shell commands are returned.

## `project_blueprint` / `proje_plani`

Available on both surfaces. Required inputs are `project_intent` and lowercase-hyphenated
`primary_domain`; product identity, prefixes, tenant header, locales and observability are optional.
The result is bounded metadata and creates no files.

## `governance_catalog` / `yonetisim_katalogu`

Lists artifact metadata without bodies. Optional filters are `kind`, `authority` and `scope`.

## `governance_artifacts_get` / `yonetisim_ogelerini_getir`

Accepts a unique non-empty `ids` list and returns only explicitly selected public bodies.

## `governance_update_check` / `yonetisim_guncellemelerini_kontrol_et`

Accepts bounded `.kt-scaffold/project-manifest.json` metadata and returns a deterministic
`GovernanceUpdateProposal`. It does not inspect the workspace.

## `reconciliation_validate` / `uyumlastirmayi_dogrula`

Validates one decision for every proposal item and returns a `local-agent-attested` decision receipt,
not workspace-execution evidence.

The Streamable HTTP surface exposes only the final five bilingual blueprint/governance pairs. It has
no prompt or creation tool. See the [MCP guide](../07-mcp-guide.md).
