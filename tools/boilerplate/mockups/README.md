# Bilgi Notu — Bölüm Taslakları ve Birleşik Belge

Hedef kitle: veritabanı ve veri ambarı alanında uzmanlaşmış ekip. Yazılım mimarisi ve altyapı
terimleri varsayılmaz; anlatım veri dünyasının kavramlarına (kısıt, şema otoritesi, versiyonlu DDL,
tek doğruluk kaynağı, deterministik dönüşüm) yaslanır.

Her bölüm burada tek başına hazırlanır ve tarayıcıda tek başına açılabilir. Onaylanan bölümler
`bilgi-notu.html` içinde birleşir ve PDF'e basılır.

## Bölüm planı

| # | Bölüm | Taslak dosyası | Durum |
|---|---|---|---|
| — | Başlık ve künye | — | birleşik belgede yazıldı, numarasız |
| 01 | Teknoloji profili + tercihlerin gerekçesi | `01-teknoloji-profili.html` | **yeniden yazıldı** |
| 02 | Mimari çerçeve ve tek istisna | `02-cerceve-ve-istisna.html` | **yeniden yazıldı** |
| 03 | Ajan değişiklik sınırları | — | **eski notdan devralındı** |
| 04 | Uygulama Esası eşlemesi | — | **yeniden yazıldı** |
| 05 | Yaşam döngüsü ve sürüm bakımı (30 gün kuralı) | — | **eski notdan devralındı** |
| 06 | Kaynakça | `01-teknoloji-profili.html` sonundan taşındı | — |

"Ölçüm şeridi" ve "Yönetici özeti" bölümleri kaldırıldı; gövde 01'den başlar.

Bölüm 04 üç karttan oluşur ve içeriği depodaki gerçek yapıdan doğrulanmıştır:
Uygulama Esası eşlemesi, kural dosyası künyesinin 5N1K tablosu, ve bilgi düzlemi (MCP) ile
uygulama düzlemi (komut satırı) ayrımı + iki taşıyıcının eşleniklik şartları. MCP tarafı hâlâ
geliştirildiği için bu kartın sayıları her sürümde yeniden doğrulanmalıdır.

"Yeniden yazıldı": bölüm hedef kitleye göre baştan kaleme alındı.
"Eski notdan devralındı": içerik `standartlar-bilgi-notu.html` dosyasından taşındı; yalnız dil
kuralları uygulandı (yasak kelimeler, çerçeve dili, İngilizce terimlerin karşılıkları). Bu bölümler
3 ve 4'ün gördüğü tam yeniden yazımı **henüz görmedi**.

## Dosyalar

| Dosya | Ne |
|---|---|
| `bilgi-notu.html` | **Birleşik belge** — 6 bölüm, A4 PDF'e basılır |
| `bilgi-notu.pdf` | Birleşik bilgi notunun sürümlü A4 çıktısı |
| `01-teknoloji-profili.html` | Bölüm 01 taslağı, tek başına açılır |
| `02-cerceve-ve-istisna.html` | Bölüm 02 taslağı, tek başına açılır |
| `standartlar-bilgi-notu.html` | Birleştirmeden önceki not — devralınan bölümlerin kaynağı |
| `03-kapali-devre-agentic-kodlama-raporu.html` | Bilgi notunun parçası **değil**; ayrı bir Karar ve Kanıt Raporu |
| `03-kapali-devre-agentic-kodlama-raporu.pdf` | Karar ve Kanıt Raporu’nun sürümlü A4 çıktısı |

Karar raporunun iç bağlantıları, yerel varlıkları, sabit dört istemcisi, C01–C09 kabul sözleşmesi,
kanıt dili ve MCP bootstrap sınırı `tests/test_agent_portfolio_report.py` ile otomatik doğrulanır.

Başlık ve künye numarasızdır; gövde bölümleri 01'den başlar. Bölüm 06 kaynakçadır ve
bölüm 01'in göstergelerine aittir.

## Dil kuralları

- Kullanılmayacak kelimeler: *kanonik*, *korpus*, *yüzey*.
- **"Vibe coding" ayrı yazılır** — *vibecoding* değil. Cümle içinde küçük harfle
  (*vibe coding kapsamında*), başlıkta büyük harfle (*Kurumsal Vibe Coding…*). `kt-vibecoding-*`
  kimlikleri kod adıdır, olduğu gibi kalır.
- **Süs amaçlı chip ve badge kullanılmaz.** Rozet ancak taşıdığı değer metinle verilemiyorsa
  (ölçüm, sürüm, durum) kullanılır; künye bilgisi düz metin olarak yazılır.
- Yasak/kırmızı ton yerine çerçeve dili: teknoloji adı sayılmaz, kurumsal renk kullanılır.
- Her teknoloji tercihi bir gerekçeye, her gerekçe ölçülebilir bir kanıta bağlanır.

## Stiller ve varlıklar

Dosyaları doğrudan tarayıcıda açın.

- `_tokens.css` — kurumsal değerler ve ortak bileşenler. `globals.css`'in aynasıdır; belgeye özgü
  hiçbir kural buraya yazılmaz.
- `_note.css` — bilgi notu bileşenleri (künye, bölüm şeridi, katmanlar, akış).
- `_report.css` — rapor sınıfı belgelerin bileşenleri.
- `../assets/kuveyt-turk-logo.svg` — kurumsal wordmark, tek kaynak. Yeniden çizilmez,
  renklendirilmez, oranı değiştirilmez; yalnız yükseklik verilir.

Diğer simgeler HTML içindeki SVG'lerden gelir; hiçbir belge dış istek üretmez.

Ekran görüntüleri ve geçici PDF önizlemeleri depoya yazılmaz; oturumun geçici çalışma dizinine
üretilir. Bilgi Notu ile Karar ve Kanıt Raporu’nun nihai PDF’leri, HTML kaynaklarıyla birlikte
`mockups/` altında tutulur.
