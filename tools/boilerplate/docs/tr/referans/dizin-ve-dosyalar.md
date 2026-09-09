# Dizin ve dosya referansı

| Yol | Sahibi / amaç |
|---|---|
| `technology-profile.yml` | Platform sahibi; sabit teknoloji profili |
| `rules/` | Yönetişim kaynağı; client projeksiyonlarının girdisi |
| `agent-platform/` | Kanonik custom-agent sözleşmeleri, dört istemcili capability matrisi, şemalar ve tarihli conformance kayıtları |
| `src/kt_scaffold/` | Generator, CLI, MCP ve operation uygulaması |
| `src/kt_scaffold/templates/` | Üretilen depoya kopyalanan/render edilen içerik |
| `tests/` | Boilerplate'in çalıştırılabilir kabul/regresyon sözleşmesi |
| `packaging/` | Offline wheel/npm/browser/OCI bundle hazırlığı ve lock'lar |
| `docs/` | Boilerplate kullanıcı ve entegrasyon rehberleri |
| `mockups/` | Karar raporları ve sunum çıktıları; runtime kaynağı değil |
| `plans/` | Çalışma/tasarım kayıtları; ürün kullanım dokümanı değil |

Üretilen projede ayrıca:

| Yol | Sahibi / amaç |
|---|---|
| `.kt-scaffold/` | Generator state, bounded manifest ve evidence |
| `.kt-scaffold/agent-projections/` | Seçilmiş inert custom-agent çıktıları ve `PROJECTIONS.lock.json`; canlı discovery kökü değildir |
| `specs/` | Domain-first ürün sözleşmesi |
| `app/backend/` | Python/FastAPI katmanları |
| `app/frontend/` | React/Vite SPA |
| `schema/` | Desired-state persistence otoritesi ve migration'lar |
| `e2e/` | Kalıcı browser kabul senaryoları |
| `scripts/` | Ad-hoc komut yerine kullanılan operasyon girişleri |
| `.github/workflows/` | Egress-denied CI sözleşmesi |
| `docs/en/`, `docs/tr/` | Projeye özgü son kullanıcı dokümantasyonu |
| `.codex/agents/`, `.claude/agents/`, `.github/agents/`, `.cursor/agents/` | İstemci-native canlı custom-agent discovery kökleri; yalnız yetkili Agent Platform activation ile doldurulur |

Managed/client projection dosyasını düzenlemeden önce kaynak otoritesini bulun. `AGENTS.md`,
`CLAUDE.md`, `.claude/rules/`, `.claude/skills/`, `.codex/skills/` ve `.cursor/rules/` gibi
mühendislik-yönetişimi dosyaları `rules/` kaynağından gelir. Agent Platform custom-agent artifact'ları
kanonik sözleşme ve compiler'dan gelir, `.kt-scaffold/agent-projections/` içinde inert kalır ve ayrı
activation/admission sınırı gerektirir. Ürün gereksinimini generated çıktıda değil `specs/` içinde
değiştirin.
