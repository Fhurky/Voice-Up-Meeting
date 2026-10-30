# PRD — Kurumsal görsel tema

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [019 — institutional-visual-theme](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak (30 Ekim 2026): Kullanıcı arayüzün, ürünün hizmet vereceği kurumun güncel yeşil,
mavi ve turuncu renkleriyle yenilenmesini, metinlerin zenginleştirilmesini ve genel
görünümün güzelleştirilmesini istedi. Depo kuralı gereği kurumun adı, logosu ve marka
metinleri depoda yer almaz; renkler adsız anlamsal değişkenler olarak tanımlanır. Kabul
edilirse [008](../008-modern-workspace/PRD.md) Decision 2'deki mor vurgulu görsel dilin
yerini alır; 008'in diğer kararları korunur.
Kabul (30 Ekim 2026): Kullanıcı taslağı kabul etti ve Open Question 1'de kurum adı ile
logosunun gösterilmemesini (a) seçti.

## Amaç ve kapsam

Kullanıcı ürünü kurumun tanıdık renk dünyasında, daha sıcak ve güven veren bir arayüzle
kullanır. Mevcut sayfalar, akışlar, yetkiler, API ve veri değişmez; yalnız sunum,
anlamsal renk değişkenleri ve kullanıcı metinleri değişir.

## Renk kaynağı

Değerler 30 Ekim 2026'da kurumun kamuya açık web sitesinin logo SVG'si ve stil
dosyalarında gözlendi; resmi marka kılavuzu değildir (Open Question 2). Kontrast oranları
WCAG göreli parlaklık formülüyle hesaplandı.

| Rol | Gözlenen değer | Sitedeki kullanım | Beyaz üzerinde | Lacivert `#0D1B2A` üzerinde |
| --- | --- | --- | ---: | ---: |
| Marka yeşili | `#43B02A` | Logo dolgusu, varsayılan birincil | 2,81 | 6,20 |
| Koyu kurumsal yeşil | `#2D7864` | Kurumsal tema birincili | 5,27 | 3,30 |
| Koyu yeşil hover | `#0E503E` | Kurumsal tema hover | — | — |
| Mavi | `#2C7AA1` | Başlık gradyanı sonu, mavi kategori | 4,77 | 3,65 |
| Turuncu | `#ED6B2C` | Turuncu düğme kenarı ve metni | 3,12 | 5,58 |
| Lacivert metin | `#0D1B2A` | Başlık ve gövde metni | 17,39 | — |

## Kararlar

Decision 1: Anlamsal değişkenler `globals.css` içinde merkezi tanımlanır ve kurum adı
taşımaz (`--color-brand`, `--color-primary`, `--color-info`, `--color-accent` gibi).
Etkileşimli birincil renk ve küçük metin `#2D7864`, hover `#0E503E` kullanır. Parlak
marka yeşili `#43B02A` yalnız büyük veya dekoratif öğelerde (marka işareti, gradyan,
seçili gezinme çizgisi, odak halkası) ve lacivert zemin üzerinde metin olarak kullanılır.

Decision 2: Mavi `#2C7AA1` bağlantı, bilgi durumu ve ikincil vurgudur. Turuncu `#ED6B2C`
ölçülü vurgudur (yeni/dikkat rozeti, ince kenar, grafik öğe); beyaz üzerinde yalnız büyük
öğe veya 3:1 yeterli arayüz bileşeni olarak, lacivert üzerinde metin olarak kullanılır.
Hata (kırmızı) ve başarı durumları ayrı kalır; turuncu hata anlamına gelmez.

Decision 3: Gezinme alanı lacivert `#0D1B2A` tabanlıdır; sayfa başlık bandı yeşilden maviye
gradyan taşıyabilir. Gradyanın açık yeşil bölgesinin üzerine küçük beyaz metin konmaz;
metin lacivert olur veya yüzey kartı üzerinde durur.

Decision 4: Bütün metin çiftleri en az 4,5:1, büyük metin ve arayüz bileşeni sınırları
en az 3:1 kontrast sağlar. Renk değerleri yalnız `globals.css` içindeki `:root`
değişkenlerinde tanımlı kalır; bileşenler sabit renk değeri kullanmaz. Yeni dış bağımlılık, uzak yazı tipi, çalışma anında ağdan görsel veya kurum
logosu eklenmez (008 Decision 2 kısıtı sürer).

Decision 5: Kullanıcı metinleri zenginleştirilebilir (karşılama, sayfa açıklamaları, boş
durumlar, adım rehberi); TR/EN eşit anahtarlarla, kurum adı geçmeden yazılır. Ürün adı
`VoiceUp` kalır.

## Gereksinimler

Requirement 1: Giriş, ana sayfa, toplantı listesi/yükleme/sonuç, konuşmacılar, ses
tanıma ve iş sayfaları aynı palet ve değişkenleri kullanır; mor değerler kalmaz.

Requirement 2: Değişken çiftlerinin kontrastını hesaplayan otomatik test Decision 4
eşiklerini doğrular.

Requirement 3: Mevcut ön yüz testleri ve kalıcı tarayıcı senaryoları geçer; ana sayfalar
TR/EN, 1440 ve 390 px'te ekran görüntüsüyle incelenir ve yatay taşma oluşmaz.

## Katmanlar

Backend, API, şema, migration, worker, vektör sözleşmesi, gözlemlenebilirlik ve
Kubernetes: N/A — yalnız ön yüz sunumu ve kataloglar değişir; Open Question 1'de dağıtım
ayarı seçilmediği için yapılandırma ve chart etkisi yoktur.

## Kabul ölçütleri

- [ ] Palet değişkenleri ve kontrast testi tamamlanır; tam ön yüz kapısı geçer.
- [ ] Bütün ana sayfalar TR/EN dar/geniş görünümde gerçek tarayıcıda incelenir; tarayıcı senaryoları geçer.
- [x] Kullanıcı görsel sonucu kabul eder (L3). (30 Ekim 2026: kullanıcı inceledi, "şimdilik yeterli".)

Open Question 1 (kapandı, 30 Ekim 2026 — a): Kurum adı ve logosu arayüzde görünmeli mi? (a) Hayır; ürün adı ve
nötr metinler yeterli. (b) Evet, ama depoda değil: dağıtım ortamı isteğe bağlı görünen
ad ve logo dosyası verir; yeni ayar, yapılandırma eşitlemesi ve chart değişikliği gerekir.

Open Question 2: Renkler resmi marka kılavuzuyla teyit edilecek mi? Sitede iki turuncu
gözlendi (`#ED6B2C` düğmelerde, `#FF9500` grafiklerde); taslak `#ED6B2C` kullanır.
