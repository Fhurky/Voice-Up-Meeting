# Mimari ve sorumluluklar

## İki düzlemli model

`kt-scaffold` iki ayrı düzlemi bilinçli olarak ayırır:

1. **Yerel uygulama düzlemi:** CLI, kodlama istemcisi ve üretilen repo. Dosya değişiklikleri, test,
   veritabanı, browser senaryosu ve kanıt burada kalır.
2. **Merkezi yönetişim düzlemi:** Kurum içi Streamable HTTP MCP. Bounded blueprint ve sürümlü
   yönetişim bilgisini sağlar; çalışma alanı içeriği veya ilk-proje byte'larını almaz.

Bu ayrım kapalı ağ güvenliği için temel sınırdır. Yerel MCP yalnız bounded cevapları ve başlangıçta
sabitlenen kökü alır; source, patch, secret, veritabanı içeriği ve dependency tree uzak MCP
sözleşmesinin dışındadır.

## İki bootstrap biçimi

| Biçim | Araç | Sonuç iddiası |
|---|---|---|
| Deterministik bootstrap | Yerel stdio `project_create` veya onaylı pinlenmiş CLI/OCI paketi | Tree digest doğrulamasından sonra aynı girdi ve generator sürümüyle dosyalar byte-identical olur |
| Intent bootstrap | Çalışan bir yerel ajan + MCP `project_blueprint` | Ajan mimari niyeti yerel araçlarıyla uygular; generator ile byte-equivalent olduğu iddia edilmez |

Boş dizinde henüz `AGENTS.md`, rules veya skills yoktur. Trusted local MCP kurulu transactional
generator'ı doğrudan çağırır. Intent bootstrap özel bir entegrasyon yoludur ve normal drift/kalite
kapılarıyla ayrıca kanıtlanır.

## Üretilen depo haritası

| Yol | Amaç |
|---|---|
| `technology-profile.yml` | Sabit teknoloji kararlarının insan ve makine tarafından okunabilen özeti |
| `.kt-scaffold/answers.yml` | Secret içermeyen scaffold girdileri |
| `.kt-scaffold/project-manifest.json` | MCP'ye gönderilebilen sınırlı proje/yönetişim metadatası |
| `.kt-scaffold/managed-manifest.json` | CLI'nin yerel managed-file durumu; MCP'ye gönderilmez |
| `.kt-scaffold/agent-projections/` | Seçilmiş inert Agent Platform çıktıları ve projection lock; canlı istemci ayarı değildir |
| `specs/<domain>/` | Domain context, roadmap, PRD, plan ve tasks |
| `rules/` | Sürümlü kaynak mühendislik kuralları |
| `AGENTS.md`, `CLAUDE.md`, `.claude/rules/`, `.claude/skills/`, `.codex/skills/`, `.cursor/rules/` | Aynı kuralların mühendislik-yönetişimi projeksiyonları |
| `app/backend/`, `app/frontend/` | Uygulama katmanları |
| `schema/` | Persistence desired state ve migration sözleşmesi |
| `e2e/` | Browser senaryoları ve kalite manifesti |
| `scripts/` | Onaylı yerel operasyon girişleri |

## Güven sınırları

- CLI yalnızca açıkça verilen hedef dizinde çalışır. Bir kalite kapısı project-owned betik
  çalıştıracaksa `--allow-project-code-execution` ile açık güven beyanı ister.
- MCP uygulaması Streamable HTTP'de loopback dışına doğrudan bind etmeyi reddeder. Kurumsal erişim
  OAuth 2.1/TLS gateway sidecar üzerinden sağlanır.
- MCP request gövdesi kaynak taşıma amacıyla büyütülmez; bounded metadata sözleşmesi korunur.
- Secret ve mTLS malzemesi repo ya da MCP kayıt dosyasına commit edilmez.
- Bağımlılık ve scanner materyali yalnızca banka tarafından kabul edilmiş, digest ile bağlanmış
  offline envanterden gelir.

## Otorite ve drift

Kaynak rules corpus'u istemciye özgü dosyalara render edilir. Bir geliştirici projeksiyon dosyasını
elle değiştirirse `scripts/check-governance-drift.py` ve render check bu farkı görünür kılar.
Ürün ihtiyacı ise merkezi kuralı ezmek yerine kabul edilmiş PRD'de tanımlanır.

Agent Platform custom-agent çıktılarının compiler, lock ve activation sınırı ayrıdır.
`.kt-scaffold/agent-projections/` altındaki inert çıktı, aktive edilmiş discovery dosyası veya kabul
edilmiş client/runtime tuple ile karıştırılmamalıdır.

Yönetişim güncellemesinde artifact otoritesi üç sınıftır:

- `mandatory`: zorunlu davranış korunur; yerel ifade veya daha güçlü kısıt eklenebilir;
- `recommended`: gerekçeyle kabul, adaptasyon, erteleme veya ret mümkündür;
- `project-owned`: merkezi servis yerel içeriği değiştirmez.

Devam: [Spec, PRD, plan ve task yaşam döngüsü](04-spec-prd-plan-task.md).
