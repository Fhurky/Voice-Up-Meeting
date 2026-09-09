# Genel bakış

## Ürün neyi çözer?

`kt-scaffold`, yeni bir kurumsal uygulamanın ilk gününde tekrar tekrar tartışılan altyapı
kararlarını tek, sürümlü bir başlangıç noktasına bağlar. Amaç “ajan bir şeyler üretsin” değil;
gereksinimden koda, testten teslim kanıtına kadar aynı sözleşmenin izlenebilmesidir.

Üretilen depoda şunlar hazır gelir:

- PostgreSQL üzerinde Python/FastAPI backend ve Alembic migration otoritesi;
- ayrık React/Vite SPA, JWT/RBAC ve uygulama seviyesinde `super_admin` temeli;
- yerel container, deployment chart, bağımlılık kabulü ve kapalı ağ betikleri;
- spec, plan, task, şema, browser senaryosu ve Definition of Done akışı;
- dört yerleşik kodlama ortamı için aynı kurallardan türetilmiş yönergeler ve skills;
- dört Agent Platform adapter hedefi için seçilmiş inert custom-agent projeksiyonları.

Örnek iş nesnesi özellikle üretilmez. İş kapsamı ancak kabul edilmiş bir PRD ile depoya girer.

## Bileşenlerin sorumlulukları

| Bileşen | Yaptığı iş | Yetkisi dışında kalan |
|---|---|---|
| `kt-scaffold` CLI | Deterministik ilk üretim, yerel dosya işlemleri, client projeksiyonları ve kalite/evidence yardımcıları | Uzak bir model ya da merkezi kodlama servisi olmak |
| Yerel stdio MCP | Kurulu generator'ı başlangıçta sabitlenen tek workspace'te çağırmak | Modelden hedef almak, executable kod indirmek veya proje komutu çalıştırmak |
| HTTP governance MCP | Blueprint, kanonik envanter, güncelleme niyeti ve reconciliation sunmak | Kaynak ağacı almak veya workspace yetkisi kazanmak |
| Kodlama istemcisi | Workspace registration'ı seçmek, sonraki dosyaları değiştirmek ve test kanıtı sunmak | İlk scaffold'u prose'dan yeniden yazmak veya başarı mesajını test yerine geçirmek |
| Banka gateway'i | OAuth 2.1, TLS/mTLS, scope, oran limiti ve denetim kimliği | Açık ya da kimliksiz trafiği MCP uygulamasına geçirmek |
| Üretilen depo | Ürün gereksinimini, kabul edilmiş kararları, kodu ve yerel kanıtı kalıcı tutmak | Geçici sohbet geçmişine güvenmek |

CLI ve MCP aynı yetki yüzeyi değildir. CLI ile trusted local stdio creation aynı digest'i üretir.
Streamable HTTP workspace-blind kalır ve yalnız blueprint/governance taşır.

## Sabit teknoloji profili

Çağıran kullanıcı veya ajan alternatif backend/persistence seçmez. Doğrulanmış profil:

- Python/FastAPI;
- async SQLAlchemy ve asyncpg;
- Alembic'in yönettiği PostgreSQL desired state;
- vector/embedding sözleşmesini kabul edilmiş bir PRD'nin sahiplenmesi koşuluyla aynı PostgreSQL
  veritabanındaki PGVector;
- ayrık React/Vite SPA.

PGVector alternatif bir persistence engine değil, opsiyonel bir PostgreSQL yetkinliğidir. Kabul
edilmiş capability; embedding provider/model sürümünü, boyutu, uzaklık metriğini, indeks stratejisini,
retrieval eşiklerini, tenant kapsamını, veri işleme ve re-embedding yaşam döngüsünü sabitler. Embedding
üretimi runtime internet erişimi veya model indirme olmadan, onaylı kurum içi ya da on-premise adapter
üzerinden yapılır.

Tamamı prompt, sohbet ve geçmişten oluşan sınırlı ürünlerde ancak
`technology-profile.yml` tarafından izin verilen Streamlit istisnası kullanılabilir. SSR ve Next.js
varsayılan profil değildir.

## İki istemci katmanı, tek yönetişim kaynağı

Mühendislik yönetişimi katmanı kanonik `rules/` corpus'unu dört yerleşik kodlama ortamına yansıtır:

- **Claude Code:** `CLAUDE.md`, `.claude/rules/` ve `.claude/skills/`.
- **Codex:** `AGENTS.md`, `.codex/config.toml` ve `.codex/skills/`.
- **Cursor:** path-scoped `.cursor/rules/*.mdc` dosyaları.
- **VS Code Local Agent:** `AGENTS.md` ile `.claude/rules/` ve `.claude/skills/` projeksiyonlarını
  keşfeder; kapalı ağ profilinde banka içi Ollama/Qwen ya da uyumlu LLM gateway kullanır.

Bunlar dört ayrı standart değildir. Kaynak kurallar sürümlüdür; projeksiyonlar aynı corpus'tan
üretilir ve drift kontrolüyle karşılaştırılır.

Agent Platform katmanı ayrıca dört kanonik custom agent'ı Codex, Claude Code, VS Code içinde GitHub
Copilot ve Cursor için native-shaped artifact'lara derler. Seçilen çıktılar
`.kt-scaffold/agent-projections/` altında inert kalır. Üretilmiş bir artifact, ayrı activation sınırı
disposable conformance grant veya exact-tuple admission receipt doğrulamadan canlı istemci ayarına
dönüşmez. Üretim, gerçek istemci conformance'ı ve runtime admission birbirinin yerine kullanılamaz.

## Context, session ve kalıcı hafıza

Bir kodlama oturumunda dört kavramı ayırmak gerekir:

- **Model context window:** modele tek istekte taşınabilen geçici içerik sınırı.
- **İstemci session/history:** konuşmayı yeniden açma veya sürdürme özelliği; istemciye özgüdür.
- **Provider/API state:** model sağlayıcısının konuşma kimliği gibi sunucu tarafı durumu. Örneğin
  Ollama'nın OpenAI Responses uyumluluğu stateful conversation garantisi vermez.
- **Depo hafızası:** `AGENTS.md`, kurallar, skills, spec/PRD/plan/task belgeleri, manifest ve test
  kanıtları. Uzun süreli çalışma için dayanıklı ve denetlenebilir kaynak budur.

Bu nedenle proje devamlılığı sohbet geçmişine değil, depoya yazılmış kararlara dayanır. Yeni bir
session, aynı kabul edilmiş PRD'yi, planı, task listesini ve kuralları okuyarak güvenli biçimde devam
edebilir.

## Yetkin kaynak sırası

Bir anlatım ile davranış çelişirse şu kaynakları kullanın:

1. `technology-profile.yml` — sabit teknoloji kararları;
2. `rules/` — mühendislik ve kalite ilkeleri;
3. `src/kt_scaffold/` — gerçek CLI, MCP ve üretim davranışı;
4. `src/kt_scaffold/templates/` — üretilen depo içeriği;
5. `tests/` — çalıştırılabilir kabul ve regresyon sözleşmesi;
6. `docs/` — bu sözleşmeleri açıklayan kullanım rehberi;
7. `mockups/03-kapali-devre-agentic-kodlama-raporu.html` — portföy kararı ve kanıt özeti.

Bir sonraki adım: [Hızlı başlangıç](02-hizli-baslangic.md).
