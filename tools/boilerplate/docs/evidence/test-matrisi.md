# Test matrix / Test matrisi

Last repository revalidation / Son repo doğrulaması: **2026-08-20**

| Surface / Yüzey | Evidence / Kanıt | Current result / Güncel sonuç | Scope note / Kapsam notu |
|---|---|---|---|
| Generator, CLI, rules, templates | `.venv/bin/pytest -q` | 435 passed | Boilerplate regression suite after the Turkish user/developer onboarding README, bilingual reference, semantic documentation-contract alignment, and four-client Agent Platform cohort update; generated-project full gate is separate |
| Agent Platform exact-client conformance | `agent-platform/conformance/runs/macos-arm64-2026-08-19.yml` | Codex desktop, Claude, VS Code/Copilot, and Cursor partial pass | Codex stable CLI remains failed; the passing desktop surface is exploratory because it bundles a pre-release CLI. Disposable real-client evidence grants no runtime admission |
| C01 policy pressure contract | `tests/test_agent_policy_contract.py`, `agent-evals/policy-pressure.yml` | Passed in full suite | Ten bilingual direct, override, laundering, spec-bypass and positive-control cases; deterministic checks cover every forbidden technology and governance projection, while live client/model responses remain separately observed evidence |
| MCP schema and aliases | `tests/test_mcp_stdio.py`, `tests/test_mcp_streamable_http.py`, `tests/test_operations_contract.py` | Passed in full suite | Local stdio validates six bilingual pairs including trusted creation; HTTP validates five bilingual workspace-blind governance pairs |
| Trusted local MCP creation E2E | Real `ClientSession` plus `tests/test_mcp_streamable_http_scaffold_e2e.py` | L2 passed | Version 0.3.0 created 388 files / 542 entries with four VS Code agent projections, equal expected/observed tree digest, no other client projection and exact-retry `unchanged`; no shell or executable download |
| Rancher RKE2 MCP release | `helm/kt-scaffold-mcp`, live `kt-lab-rke2` revision 20 | L2 passed | RKE2 v1.33.13; pod 2/2 ready with zero restarts; immutable MCP image `sha256:15f7e025...`; initialize reported 0.3.0; ten governance tool aliases passed through the host port-forward; creation tools were absent and retired executable routes returned 404 |
| MCP Helm and image security | Semgrep 1.170.0; Trivy 0.72.0 DB dated 2026-08-10 | Stale for 0.3.0; not release-eligible | The prior 0.2.x scan is retained as historical evidence only. The 0.3.0 digest is admitted solely to the isolated local LAB for transport verification; a current image/SBOM/signature/security scan is required before any broader release claim |
| Report structure and claim guards | `tests/test_agent_portfolio_report.py` | Passed in full suite | Fixed four-client portfolio, evidence labels and overstatement guards |
| VS Code Local Agent + Ollama/Qwen PoC | `mockups/03-kapali-devre-agentic-kodlama-raporu.html` | 3/3 recorded | Dated local PoC; VS Code UI was not rerun in the 2026-08-07 repository revalidation |
| Cross-client acceptance C01–C09 | Portfolio report checklist | Designed, not a complete executable client suite | Must be rerun for each admitted client/model/version/hardware combination |

## Revalidation rule / Yeniden doğrulama kuralı

Rerun the affected row when the generator, MCP SDK, client UI, model, quantization, hardware,
offline bundle or security policy changes. Record exact versions and distinguish automated,
local-observed and design-only evidence.

Generator, MCP SDK, istemci UI, model, quantization, donanım, offline bundle veya güvenlik politikası
değiştiğinde ilgili satırı yeniden çalıştırın. Tam sürümleri kaydedin; otomatik, yerelde gözlenen ve
yalnız tasarlanmış kanıtı birbirinden ayırın.
