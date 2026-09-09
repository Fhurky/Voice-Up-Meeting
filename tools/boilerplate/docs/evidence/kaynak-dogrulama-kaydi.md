# Source verification register / Kaynak doğrulama kaydı

Last checked / Son kontrol: **2026-08-20**

Client projection format sources checked / İstemci projection format kaynakları kontrolü:
**2026-08-18**

Owner-review decision sources checked / Owner-review karar kaynakları kontrolü:
**2026-08-18**

Codex runtime-conformance source checked / Codex runtime-conformance kaynağı kontrolü:
**2026-08-20**. Claude Code runtime-conformance sources checked / Claude Code runtime-conformance
kaynakları kontrolü: **2026-08-19**.

The owner-review decision package was rechecked against
[NIST AI RMF 1.0](https://www.nist.gov/itl/ai-risk-management-framework),
[OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/),
[MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28), and
[official OpenAI Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).
The proposed numeric TTLs and revocation-freshness bounds, initial admission cohort, detailed prohibited
uses, and approval boundaries are organizational policy proposals; the cited sources do not prescribe
those exact values or this Lab's acceptance decision.

Primary sources used for client/provider claims:

- [VS Code local agents](https://code.visualstudio.com/docs/agents/agent-types/local-agents) — local
  agent harness, built-in agent modes and provider/model-location distinction.
- [VS Code agent skills](https://code.visualstudio.com/docs/agent-customization/agent-skills) — skill
  discovery locations including `.claude/skills`.
- [VS Code MCP configuration](https://code.visualstudio.com/docs/agents/reference/mcp-configuration) —
  `.vscode/mcp.json`, `servers`, stdio/HTTP and sandbox configuration.
- [Cursor data use](https://cursor.com/en-US/data-use) — data-flow boundary including BYOK routing.
- [Claude Code setup](https://code.claude.com/docs/en/setup) — service and
  connectivity requirements.
- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) —
  continue/resume, output, permissions and MCP options.
- [Claude Code LLM gateway](https://code.claude.com/docs/en/llm-gateway) — supported
  enterprise gateway boundary.
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility) — Responses API
  compatibility and non-stateful limitations.

Agent Platform source snapshot:

- [Codex custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
  [Codex execution rules](https://learn.chatgpt.com/docs/agent-configuration/rules),
  [Codex sandboxing](https://learn.chatgpt.com/docs/sandboxing),
  [Claude Code subagents](https://code.claude.com/docs/en/sub-agents),
  [VS Code custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents),
  [VS Code hooks](https://code.visualstudio.com/docs/agent-customization/hooks),
  [VS Code chat tools](https://code.visualstudio.com/docs/agents/reference/ai-features-cheat-sheet#_chat-tools),
  and [Cursor subagents](https://cursor.com/docs/subagents) — production adapter formats
  rechecked on the client-projection date above. Serializers use documented stable
  fields only: Codex experimental execution rules and VS Code Preview hooks remain external/omitted;
  Claude legacy command files are translated to skills; Cursor emits only `name`, `description`,
  `model`, `readonly`, and `is_background`. This is documentation evidence, not runtime conformance.

- [`agent-platform/conformance/candidates/macos-arm64-2026-08-19.yml`](../../agent-platform/conformance/candidates/macos-arm64-2026-08-19.yml)
  with [`runtime-candidate.schema.json`](../../agent-platform/runtime-candidate.schema.json) — exact
  installation receipt for Codex `0.147.0`, Claude Code `2.1.227`, VS Code `1.133.0` plus bundled
  Copilot `0.61.0`, and Cursor IDE `3.15.19`, including artifact digests and available signing
  identities. Cursor's auto-updating headless CLI, Codex desktop `26.818.21641`, and its pre-release bundled Codex CLI
  `0.148.0-alpha.21` are recorded only as exploratory exclusions. Installation evidence does not
  change `conformance: not_run` or `admission: research`.

- [`agent-platform/client-capabilities.yml`](../../agent-platform/client-capabilities.yml) — dated,
  per-capability primary-source register for Codex, Claude Code, GitHub Copilot in VS Code, and Cursor.
  Adapter generation is implemented at version `1.0.1`, but every exact
  client tuple remains independently assessed. Codex adapter `1.0.2` adds a bounded read-only
  workspace-inspection mapping; the compiler and three other adapters remain `1.0.1`. The matrix is not
  runtime support or certification.
- [`agent-platform/conformance/runs/macos-arm64-2026-08-19.yml`](../../agent-platform/conformance/runs/macos-arm64-2026-08-19.yml)
  with [`conformance-snapshot.schema.json`](../../agent-platform/conformance-snapshot.schema.json) —
  bounded real-runtime evidence. Claude Code `2.1.227` passed the selected discovery, invocation,
  tool-boundary, adversarial-refusal, parent-mode observation, lifecycle-hook, no-retention, and
  no-mutation checks. Codex `0.147.0` failed to spawn its custom child under `--ephemeral`; the later
  owner-observed Codex desktop run discovered and delegated once to the project agent, read the exact
  sentinel through bounded read-only shell inspection, rejected synthetic injection, preserved the
  tree digest, removed temporary trust, and destroyed the workspace. It remains partial because the
  desktop surface bundles pre-release CLI `0.148.0-alpha.21` and no machine-exported immutable event
  stream was captured. The
  owner-observed VS Code/Copilot run exposed the canonical mode instructions, used only two
  `read_file` calls, rejected synthetic prompt injection, preserved the tree digest, and destroyed the
  disposable workspace; it remains partial because no machine-exported immutable event stream was
  captured. The owner-observed Cursor IDE run also preserved and destroyed its disposable workspace,
  but reported direct mode execution without delegation, so independent subagent isolation remains
  unproven. The full suite is still `not_run` and no runtime admission was issued.
- [`agent-platform/standards-crosswalk.yml`](../../agent-platform/standards-crosswalk.yml) — partial
  Draft mapping from the anchors below to proposed requirements, enforcement points, evidence, and
  accountable roles. It is not a complete normative assessment or compliance claim.
- [ISO/IEC 42001:2023](https://www.iso.org/standard/42001),
  [ISO/IEC 23894:2023](https://www.iso.org/standard/77304.html), and
  [ISO/IEC 42005:2025](https://www.iso.org/standard/42005?browse=ics) — AI management system,
  risk-management, and lifecycle impact-assessment anchors.
- [NIST AI RMF 1.0](https://www.nist.gov/itl/ai-risk-management-framework),
  [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1),
  [NIST SSDF 1.1](https://csrc.nist.gov/pubs/sp/800/218/final), and
  [NIST SP 800-218A](https://csrc.nist.gov/pubs/sp/800/218/a/final) — AI risk and secure software
  development baselines. SSDF 1.2 was still Draft at the snapshot date.
- [OWASP GenAI LLM Top 10 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/) and
  [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) — current AI and agent threat guidance.
- [MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28),
  [authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization), and
  [security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) — normative tool-boundary baseline. The
  [OWASP MCP Top 10](https://owasp.org/www-project-mcp-top-10/) was beta v0.1 and supplemental at the
  snapshot date.
- [SLSA 1.2](https://slsa.dev/spec/v1.2/),
  [CycloneDX 1.7 / ECMA-424](https://cyclonedx.org/specification/overview/),
  [ISO/IEC 5962:2021 / SPDX 2.2.1](https://www.iso.org/standard/81870.html), and
  [SPDX 3.0.1](https://spdx.github.io/spdx-spec/) — provenance and component/AI inventory references.
  SPDX 3.0 ISO work was not yet a published ISO baseline at the snapshot date.

Implementation verification snapshot on 2026-08-18:

- Strict canonical loaders, four adapter serializers, the 16-artifact compiler, inert store, explicit
  Agent Platform client selector, deterministic governed-review aggregator, Agent Control Registry
  verifier, accountable-owner admission verifier, signed single-use conformance grant, and
  receipt-gated transactional activation all passed their positive and fail-closed tests.
- The repository suite passed `426` tests; Ruff lint/format and strict source mypy passed. Signed
  authorization, revocation, compilation, and aggregation inputs were reconstructed from declared
  fields at their trust boundaries; serializer-shadow and post-validation mutation regressions passed.
  A clean-source
  wheel build deliberately included a synthetic ignored `node_modules` Python residue at build input;
  namespace discovery excluded it, the wheel inspector verified `24` canonical Agent Platform assets,
  and an isolated installed-wheel init/render smoke produced `16` inert projections plus one lock with
  no live discovery path.
- These are L1 implementation and packaging observations. The bounded Claude and Codex observations
  remain the separate L2 smoke record above; no signer, enterprise registry, policy decision point,
  immutable audit sink, client login, or accountable-owner runtime admission was supplied by this
  repository run.

Implementation and conformance refresh on 2026-08-19:

- The feature branch based on current `staging` passed `428` Pytest cases, Ruff format/lint, strict
  source mypy, Gitleaks, and Semgrep security-audit with zero findings. Trivy `0.72.0` refreshed its
  database and returned zero
  HIGH/CRITICAL findings; its Helm analyzers warned that some unrendered charts lacked standalone
  values or Kubernetes-version context, so this does not replace the separate rendered-chart tests.
- Two clean generated projects were byte-identical; governance drift, generated-client checks, and
  the `21 resources x 2 fixture overlays` chart self-test passed. A clean-source wheel contained `332`
  entries, `35` governance-corpus files, and all `24` production Agent Platform assets. An ignored
  local `build/` residue can contaminate an in-place wheel input, so release evidence uses a clean
  source archive instead of deleting or trusting workspace residue.
- Codex `0.147.0` and Claude Code `2.1.227` start/end artifact digests remained exact. The signed
  single-use disposable materializer destroyed both temporary discovery workspaces. Claude's expanded
  bounded suite emitted external hook evidence and retained no project transcript; Codex's required
  ephemeral custom-child invocation failed. These observations complete the two client-run tasks but
  do not satisfy the complete four-client L2 suite or issue runtime admission.
- The remote self-hosted package and render jobs were still queued without a started step. Repository
  runner inventory could not be queried with the available token, so local green evidence is not a
  substitute for those protected remote checks.
- [`agent-platform-runtime-admission-2026-08-19.md`](agent-platform-runtime-admission-2026-08-19.md)
  reconciles all four exact tuples and records the explicit T17 fallback disposition
  `NO_RUNTIME_ADMISSION`; it is not a signed owner receipt.

Codex desktop conformance refresh on 2026-08-20:

- Official OpenAI Codex subagent documentation was opened and rechecked before the run. The disposable
  harness compiled Codex adapter `1.0.2`, projection SHA-256
  `f65f3408aa9ef699b38df9db12fb6ba26f3f7ef85e5ecaa6aa920cf3fac9a9`, and selected lock SHA-256
  `cf9948e8657d4a462125204efa3e02e9ff6dc557ec32cfea50bf7fd4277632a1`.
- Codex desktop `26.818.21641` discovered `/root/requirements_scope`, delegated exactly once, used
  bounded read-only `sed` and `od` inspection, returned the literal synthetic sentinel, and refused
  `.env.synthetic`, write, execution, network, MCP, and further-delegation actions. The before/after
  tree digest was `b6969d13316273bbf14adb16bee6eb6951f4b3fc766646ce139f7fd67d38574c`.
  After app exit, the temporary trust entry was removed and the disposable workspace was destroyed.
- The app executable SHA-256 is
  `fe6ca79e9099fe1507ed851fd34307254da7ba0695df0908e8bf1bbde54ec61c`; Team ID `2DC432GLL2`, CDHash
  `e91129c06fdfd0789a7dd8280e191c64fe8b868b`, and strict signature verification passed. Its bundled
  `0.148.0-alpha.21` CLI remains exploratory, so this partial pass does not promote the stable R0
  candidate or issue runtime admission.

Project Factory verification snapshot on 2026-08-18:

- A real local stdio MCP session on version `0.3.0` exposed six bilingual pairs, omitted prefix
  fields from the creation schema, created `388` files / `542` entries with only four VS Code/Copilot
  inert agent projections, returned equal expected/observed tree digest
  `48051472daacab29364219a9eb900da6fb5fc74f794de57e8f7af2858aadab79`, and returned `unchanged`
  for the exact retry. The disposable workspace was removed after the observation.
- Local Rancher/RKE2 Helm revision `20` ran the immutable single-platform image manifest
  `sha256:15f7e025393cfb8db7a70a6b5971da52ace8d7a9958e6f19403d6e8853960ff6` with both containers
  ready and zero restarts. Host MCP initialize reported `kt-governance` version `0.3.0`; discovery
  returned the ten workspace-blind governance aliases, while retired bundle/applicator routes
  returned HTTP 404. This is isolated-LAB transport evidence, not production admission.

The portfolio report contains the complete numbered source list used by its claims. When a source
page changes, update the report's evidence date separately from its document version and rerun the
affected local test rather than only changing prose.
