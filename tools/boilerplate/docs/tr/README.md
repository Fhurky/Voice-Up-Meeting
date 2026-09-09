# kt-scaffold — Türkçe kullanım rehberi

`kt-scaffold`, kapalı ağda çalışmaya uygun, spec-first bir uygulama deposunu boş bir dizinden
üretir. Üretilen başlangıç noktası yalnızca klasör şablonu değildir: sabit teknoloji profili,
mimari kurallar, ajan yönergeleri, yerel çalışma ortamı, kalite kapıları ve kanıt sözleşmesi birlikte
gelir.

Bu rehber üç soruya yanıt verir:

- **Ne?** Ürünün kapsamı, sabit kararları ve kanıt modeli.
- **Nerede?** Kaynak kuralların, PRD/plan/task belgelerinin, ajan projeksiyonlarının ve çalışma
  betiklerinin konumu.
- **Nasıl?** İlk scaffold'dan kabul edilmiş bir iş kabiliyetine ve doğrulanmış teslim raporuna giden
  akış.

## Başlangıç sırası

1. [Genel bakış](01-genel-bakis.md): ürünü, sınırlarını ve bileşenlerin sorumluluklarını okuyun.
2. [Hızlı başlangıç](02-hizli-baslangic.md): ilk projeyi üretin ve spec-first akışı deneyin.
3. MCP kullanacaksanız [global MCP sözleşmesini](../global-mcp.md) inceleyin. MCP, çalışma alanını
   okuyan ya da scaffold'u uzaktan kuran bir dosya sistemi servisi değildir.

## Rehberler

- [Mimari ve sorumluluklar](03-mimari-ve-sorumluluklar.md)
- [Spec, PRD, plan ve task yaşam döngüsü](04-spec-prd-plan-task.md)
- [Ajan istemcileri](05-ajan-istemcileri.md)
- [CLI kullanım rehberi](06-cli-kullanim-rehberi.md)
- [MCP kullanım rehberi](07-mcp-kullanim-rehberi.md)
- [Güncelleme ve uyumlaştırma](08-guncelleme-ve-uyumlastirma.md)
- [Kalite, kanıt ve E2E](09-kalite-kanit-ve-e2e.md)
- [Kapalı devre operasyon](10-kapali-devre-operasyon.md)
- [Sorun giderme](11-sorun-giderme.md)

## Referans

- [Komutlar](referans/komutlar.md)
- [MCP araçları](referans/mcp-araclari.md)
- [Dizin ve dosyalar](referans/dizin-ve-dosyalar.md)
- [Manifestler](referans/manifestler.md)
- [Kanıt seviyeleri](referans/kanit-seviyeleri.md)
- [Sözlük](referans/sozluk.md)
- [Doğrulama kayıtları](../evidence/README.md)

## Sabit ilkeler

- Kanonik mühendislik kuralları corpus'unun Claude Code, Codex, Cursor ve VS Code Local Agent için
  yerleşik projeksiyonları vardır. Bu dört ortamlı temel, Agent Platform runtime kabulünden ayrıdır.
- Agent Platform compiler'ının dört inert adapter hedefi vardır: Codex, Claude Code, VS Code içinde
  GitHub Copilot ve Cursor. Seçilmiş çıktı
  `.kt-scaffold/agent-projections/` altında kalır; üretim, conformance veya admission anlamına gelmez.
- Tam kapalı ağda yerel model kullanan varsayılan mühendislik ortamı VS Code Local Agent'tır. Diğer
  yerleşik mühendislik ortamları yalnızca gerektirdikleri servislerin onaylandığı ağ bölgelerinde
  kullanılır.
- Backend ve persistence profili sabittir: Python/FastAPI, async SQLAlchemy, asyncpg, Alembic ve
  PostgreSQL.
- İş kodu ancak `specs/<domain>/PRDs/<capability>/PRD.md` belgesinin durumu `Accepted` olduktan
  sonra başlar.
- Ajanın “tamamlandı” mesajı kanıt değildir. Yerel testler, kalite kapıları ve onay kayıtları
  yetkindir.
- CLI ve MCP aynı yüzey değildir: CLI ve trusted local stdio creation aynı deterministik byte'ları
  üretir; HTTP MCP yalnız workspace-blind blueprint/yönetişim sözleşmelerini sunar.

## Dil eşleşmesi

Bu dizindeki numaralı her belgenin `docs/en/` altında aynı numaralı İngilizce karşılığı bulunur.
Komut ve MCP araçlarının Türkçe takma adları aynı uygulamaya gider; JSON alan adları ve makine
sözleşmesi çevrilmez.
