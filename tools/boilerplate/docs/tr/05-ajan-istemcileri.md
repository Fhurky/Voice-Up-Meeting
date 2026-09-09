# Kodlama istemcileri ve Agent Platform

## Birbirinden ayrı iki projeksiyon katmanı

Ürünün kanonik yönetişimi paylaşan fakat artifact ve kanıt sınırları farklı iki istemci katmanı vardır.

### Mühendislik-yönetişimi projeksiyonları

Yerleşik temel, `rules/` ve operasyon skill'lerini dört kodlama ortamına yansıtır:

| Ortam | Repo içi yönerge yüzeyi | Kapalı ağ konumu |
|---|---|---|
| Claude Code | `CLAUDE.md`, `.claude/rules/`, `.claude/skills/` | Gerekli Anthropic servislerine izin verilen bölge |
| Codex | `AGENTS.md`, `.codex/config.toml`, `.codex/skills/` | Gerekli OpenAI servislerine izin verilen bölge |
| Cursor | `.cursor/rules/*.mdc` | Cursor servislerinin ve veri politikasının onaylandığı bölge |
| VS Code Local Agent | `AGENTS.md`, `.claude/rules/`, `.claude/skills/` | Tam kapalı ağ + banka içi Ollama/Qwen veya uyumlu gateway için varsayılan |

Bunlar dört ayrı standart değil, tek rule corpus'un teslim projeksiyonlarıdır. Claude Code, Codex ve
Cursor izinli bölge seçenekleridir. Bir provider endpoint'ini yerel modele yöneltmek istemcinin auth,
telemetri ve session davranışını otomatik olarak kapalı devre veya kabul edilmiş yapmaz.

### Agent Platform custom-agent projeksiyonları

Agent Platform compiler'ının dört native adapter hedefi vardır:

| Adapter hedefi | Inert çıktı biçimi | Yetkili activation sonrası canlı discovery kökü |
|---|---|---|
| Codex | TOML custom agent'lar | `.codex/agents/` |
| Claude Code | Markdown subagent'lar | `.claude/agents/` |
| VS Code içinde GitHub Copilot | `.agent.md` dosyaları | `.github/agents/` |
| Cursor | Markdown custom agent'lar | `.cursor/agents/` |

`kt-scaffold init --agent-client ...` ve `kt-scaffold render --agent-client ...` yalnız seçilen
custom-agent çıktılarını `.kt-scaffold/agent-projections/` altında derler. Bu store inert'tir.
Bir projeksiyon ancak ayrı transactional activation sınırı disposable conformance grant veya exact
client/model/tool/policy/environment tuple için imzalı, süreli admission receipt doğruladıktan sonra
discoverable olur.

Adapter implementasyonu runtime desteği değildir. Güncel sözleşme dört uygulanmış serializer ve 16
deterministik çıktı kaydeder; fakat hiçbir exact tuple admitted değildir. Gerçek istemci conformance'ı,
owner admission ve bağımsız certification ayrı durumlardır.

## Render ve drift

Mühendislik-yönetişimi projeksiyonları için `--client`, inert Agent Platform custom-agent çıktıları
için `--agent-client` kullanılır:

~~~sh
kt-scaffold render --target-dir . --mode check
kt-scaffold render --target-dir . --agent-client codex --mode check
~~~

Hiçbir generated biçimi tek başına elle düzeltmeyin. Kanonik kaynağı değiştirip yeniden render edin;
projection lock, conflict ve warning alanlarını inceleyin. Normal proje update'i kaydedilmiş Agent
Platform seçimini tekrarlar; bu immutable seçimin değiştirilmesi gelecekte ayrı bir governed migration
gerektirir.

## Yeni session başlatma

Konuşma geçmişi istemciye göre sürebilir veya sıfırlanabilir. Her yeni görevde ajan en az şunları
yeniden okumalıdır:

1. uygulanabilir root ve path-scoped yönergeleri;
2. `technology-profile.yml`;
3. `specs/<domain>/DOMAIN.md`;
4. kabul edilmiş `PRD.md`, `plan.md` ve `tasks.md`;
5. mevcut diff ve son bağımsız test kanıtını;
6. custom agent'lar aktifse activation receipt'i ve exact runtime kapsamını.

Örnek başlangıç isteği:

> İlgili repo yönergelerini, teknoloji profilini ve kabul edilmiş PRD/plan/tasks dosyalarını oku.
> Mevcut diff'i koru. Önce kapsam ve acceptance eşleşmesini özetle; sonra task sırasıyla uygula ve
> yalnızca gerçekten çalıştırdığın testleri kanıt olarak raporla.

## Kullanım öncesi gerekli kanıt

Bir mühendislik kodlama ortamında instruction discovery, Accepted-PRD enforcement, izlenebilir çok
dosyalı çalışma, tool ve test yürütme, ilgisiz değişiklikleri koruma, uygulanabildiğinde browser
acceptance ve çalıştırılmayan kontrollerin dürüst raporlanması doğrulanır.

Bir Agent Platform runtime tuple için ayrıca native custom-agent discovery ve doğrudan invocation,
instruction precedence, etkili tool ve permission sınırları, denial davranışı, delegation,
injection/exfiltration dayanımı, audit, drift, rollback ve başlangıç/bitiş exact sürüm-digest eşitliği
doğrulanır. Ancak bundan sonra sorumlu owner ayrı, süreli admission receipt düzenleyebilir.

Tarihli Local Agent PoC ve tarihsel dört ortamlı karşılaştırma
`mockups/03-kapali-devre-agentic-kodlama-raporu.html` içindedir. Bunlar dört hedefli Agent Platform
conformance matrisinin yerine geçmez ve gelecekteki istemci, model, donanım veya sürümlerin üretim onayı
değildir.

Devam: [CLI kullanım rehberi](06-cli-kullanim-rehberi.md).
