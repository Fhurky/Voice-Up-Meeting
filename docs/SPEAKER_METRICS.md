# Konuşmacı doğruluğu ölçüm protokolü

Protokol: `voiceup-open-set-v1` · Tarih: 9 Eylül 2026

Yetki: [001 / Decision 9](../specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md).
Bu protokol tek konuşmacılı pilotun çevrimdışı değerlendirmesidir. Toplantı içindeki
konuşmacıları ayırma veya konuşmayı yazıya çevirme doğruluğunu ölçmez.

## Neyi ölçeceğiz?

Sistem iki ayrı işi yapmalıdır: kayıtlı kişinin doğru kimliğini bulmak ve kayıtlı
olmayan kişinin yeni olduğunu fark etmek. Bir sesi güvenle yanlış kişiye atamak,
kararsız kalmaktan farklıdır. Her sonucu aşağıdaki tabloda görünür tutarız.

| Gerçek kişi | Sonuç | Kimlik hesabı | Bilinmeyen hesabı |
| --- | --- | --- | --- |
| Bilinen | Doğru kimlik | Doğru pozitif (TP) | Doğru negatif |
| Bilinen | Başka kimlik | Atanan kişide yanlış pozitif (FP), gerçek kişide yanlış negatif (FN) | Doğru negatif; kimlik hatası ayrı sayılır |
| Bilinen | `unknown` | FN | FP |
| Bilinen | `ambiguous` veya başarısız iş | FN | Başarılı bilinmeyen kararı değildir |
| Bilinmeyen | `recognized` | Atanan kişide FP | FN |
| Bilinmeyen | `unknown` | Kimlik TP/FP/FN'sine girmez | TP |
| Bilinmeyen | `ambiguous` veya başarısız iş | Kimlik TP/FP/FN'sine girmez | FN |

Kalite hatası, sessizlik ve teknik hata kendi nedenleriyle ayrıca sayılır. Bir işin
başarıyla sonlanması, kimlik kararının doğru olması anlamına gelmez. Benzerlik
değeri de doğruluk yüzdesi veya kalibre edilmiş olasılık değildir.

Anonim hata dökümü yalnız `insufficient_speech`, `inconsistent_audio`, `clipped_audio`,
`invalid_audio`, `audio_limit` ve `unsupported_audio` kalite kodlarını adlarıyla
gösterir. Diğer veya eksik kodlar `unreported_or_unsupported` altında toplanır;
kalite dışı/sınıflandırılmamış grup olarak sayılır. Bu grup kesin teknik hata
tanısı değildir. Serbest hata metni rapora taşınmaz.

## Kimlik precision, recall ve micro F1

`C`: doğru kimliğe bağlanan bilinen sorgu sayısı. `W`: başka kimliğe bağlanan
bilinen sorgu sayısı. `A`: bir kimliğe bağlanan bilinmeyen sorgu sayısı.
`K`: planlanan bütün bilinen sorguların sayısı.

```text
TP = C
FP = W + A
FN = K - C

Precision = TP / (TP + FP)
Recall    = TP / (TP + FN) = C / K
Micro F1  = 2 × TP / (2 × TP + FP + FN)
```

Precision, “bir kişiye atadığım seslerin ne kadarı doğru?” sorusudur. Recall,
“tanımam gereken seslerin ne kadarını tanıdım?” sorusudur. F1 ikisini birlikte
değerlendirir. Yanlış kimlik aynı anda hem FP hem FN oluşturur; bu iki farklı
kimlik iddiasının hatasıdır, muhasebe tekrarı değildir.

## Kişilere eşit ağırlık: kimlik macro F1

Her planlı bilinen kişi için ayrı TP/FP/FN ve F1 hesaplanır. O kişiye ait başka
kayıtlar kaçırıldığında FN, başka kişilerin sesleri ona atandığında FP artar.
Kimlik macro F1, bu kişi F1'lerinin aritmetik ortalamasıdır. Sorgu sayısı çok olan
bir konuşmacı daha fazla ağırlık kazanmaz. Bu, precision ve recall ortalamalarından
sonradan hesaplanan F1 değildir.

İlk profil kaydı başarısız olan kişi planlı bilinen kişi olarak kalır; sorguları
ve sıfır F1'i ortalamadan çıkarılmaz. Planlı bilinen kişinin sorgu desteği yoksa
protokolün kişi karşılaştırması geçersizdir; yalnız başarılı kişiler seçilerek skor
üretilmez. Kimlikler hesap sırasında yerelde kullanılır, yayımlanan rapora yazılmaz.

## Bilinmeyen precision, recall ve F1

`U`: planlı bilinmeyen sorgu sayısı. `T`: bunlardan açıkça `unknown` sonucunu alanlar.
`B`: bilinen olduğu halde `unknown` sonucunu alanlar.

```text
TP_unknown = T
FP_unknown = B
FN_unknown = U - T

Precision_unknown = T / (T + B)
Recall_unknown    = T / U
F1_unknown        = 2 × T / (2 × T + B + U - T)
```

Her sesi bilinmeyen ilan eden sistem yüksek recall elde edebilir, fakat bilinen
kişileri kaçırdığı için bilinmeyen precision ve kimlik F1 düşer. `ambiguous` veya
kalite hatasını doğru bilinmeyen saymak bu hesabı haksız yükseltir; bunu yapmayız.

## Projeye özgü özet: VoiceUp Score

```text
I = kimlik macro F1
U = bilinmeyen F1

VoiceUp Score = 100 × 2 × I × U / (I + U)
```

Bu, iki göreve eşit ağırlık veren 0–100 arası **özel bir bileşik skordur**; standart
micro/macro F1 veya yüzde doğruluk değildir. İki bileşenden biri sıfırsa skor
sıfırdır. Bir bileşen ölçülemiyorsa skor `null` olur. Zayıf bileşen sonucu aşağı
çeker; skor her zaman iki bileşeni ve yanlış kabul sayılarını gösteren tabloyla
birlikte okunmalıdır. Yanlış kimlik için kabul edilebilir risk sınırının yerine
geçmez ve tek başına dağıtım/kabul kararı vermez.

İlk kayıt kapsamı = başarılı ilk profil kayıtları / planlı ilk profil kayıtları.
Bu oran ayrı gösterilir; kimlik kaçırmalarında etkisi bulunduğu için bileşik skor
tekrar kayıt kapsamıyla çarpılmaz. Karar kapsamı bütün planlı sorgular içindeki
başarılı `recognized` veya `unknown` kararlarının oranıdır; `ambiguous` ve başarısız
işler bu kapsama girmez. Karar verilmiş olması, kararın doğru olduğu anlamına gelmez.

## Sıfır, eksik sonuçlar ve doğrulama

- Sıfır paydalı precision/recall `null` olur; yüzde 100 veya sıfır uydurulmaz.
- Planlı desteği olan bir sınıfta hiç doğru sonuç yoksa sayımlardan F1=0 olur.
- Bilinmeyen sorgu olmayan deneyde bilinmeyen F1 ve VoiceUp Score ölçülemez.
- Açıkça boş bilinen galeride kimlik macro F1 ve VoiceUp Score ölçülemez;
  pozitif büyüklükteki galeride planlı sorgusu olmayan kişi sessizce atılmaz.
- Bir aşamada planlı ilk kayıt veya sorgu eksik/bekliyorsa skorlar `null`, aşama
  eksik olarak raporlanır; eksik/bekleyen sayılar gösterilir. Terminal başarısız
  işler tamamlanmış ölçüme dahildir ve yukarıdaki FN kurallarına uyar.
- Kaynak koşucunun kendisi de hatasız `complete` bildirmelidir. Son iş bitse bile
  koşucunun son galeri doğrulaması başarısız olabilir; bu durumda işlem sayıları
  korunur, bütün skorlar boş kalır. İşlerin terminal olması koşucunun son
  tutarlılık kontrolünü geçtiği anlamına gelmez; serbest koşucu hata metni yayımlanmaz.
- Hesap manifestte planlanan kişiler, roller ve sorgular üzerinden yapılır.
  Raporun canonical manifest SHA-256 bağı, kayıt kimliği/rolü/kişisi/kaynak özeti,
  aşaması ve karar yapısı doğrulanır. Yinelenen veya beklenmeyen işlem reddedilir.
  Bir `recognized` kararı o aşamada gerçekten oluşturulmuş bir profile bağlanmalıdır.
- İç içe 5/10/20/50 kişilik galeriler aynı sorguları yeniden kullanabilir; puanları
  ayrı tutulur. Aynı sorgu tek galeri içinde iki kez sayılamaz.
- Yeni kişinin ilk kaydı ve sonraki dönüşü ayrı kalır; donmuş galeri puanına katılmaz.
- Tarihsel kota sürümünde yeni kişinin kaydı `profile_limit` ile reddedilmişse bu ayrı
  deneyin başarısız kaydı olarak tutulur; ses kalitesi hatası veya başarılı
  bilinmeyen kararı sayılmaz. Ana galeri sorguları ve son tutarlılık kontrolü
  tamamlandıysa ana skorlar korunur; skor formülleri kapasite nedeniyle değişmez.
  Raporlardaki mevcut `job_status_counts` alanı değerlendirme işlemlerini sayar;
  sunucu işi oluşmadan reddedilen işlem için iş veya işlem süresi uydurulmaz.
- Güncel uygulamada 50 kayıt kotası yoktur; yaklaşık 50 kişi doğruluk hedefidir.
  Ölçüm aracı 100/200 kişilik deney girdilerini de destekler; bu, o ölçekte gerçek
  veriyle başarılı sonuç elde edildiği anlamına gelmez.

## Elle kontrol edilebilen örnek

İki bilinen kişi için ikişer sorgu ve iki bilinmeyen sorgu planlandığını varsayalım:
A→A, A→B, B→B, B→unknown, yeni kişi→B, yeni kişi→unknown.

| Ölçü | Sayım / hesap | Sonuç |
| --- | --- | ---: |
| Kimlik precision | TP=2, FP=2 → 2/4 | %50 |
| Kimlik recall | TP=2, FN=2 → 2/4 | %50 |
| Kimlik micro F1 | 4/(4+2+2) | %50 |
| A kişisi F1 | TP=1, FP=0, FN=1 → 2/3 | %66,67 |
| B kişisi F1 | TP=1, FP=2, FN=1 → 2/5 | %40 |
| Kimlik macro F1 | (2/3+2/5)/2 | %53,33 |
| Bilinmeyen F1 | TP=1, FP=1, FN=1 → 2/4 | %50 |
| VoiceUp Score | 100×2×(8/15)×(1/2)/(8/15+1/2) | **51,61/100** |

## Tekrarlanabilir kullanım ve yorum

Mevcut raporlama aracının eski kullanımı korunur. Yeni ölçüler açıkça seçilir:

```powershell
.venv/Scripts/python.exe scripts/report-public-speakers.py `
  --input outputs/quality-improvement/fresh-results.json `
  --manifest data/public-speaker-holdout-v2/test.json `
  --metrics-protocol voiceup-open-set-v1 `
  --output outputs/speaker-metrics/fresh-summary.json
```

Çıktı dosyası önceden varsa araç üzerine yazmayı reddeder. Model çalıştırılmaz,
internete ses gönderilmez ve uygulama kayıtları değişmez. Rapor; protokol sürümü,
kaynak rapor ve manifest özeti, sabit model/eşik bilgisi, planlı sayılar ve anonim
ölçüler taşır. Yeni protokolde çıktı şeması 2, eski kullanımda 1 olarak kalır.

Mevcut üç veri grubuna uygulanması **sonradan yeniden puanlamadır**. Aynı ses/model
kararlarından farklı ve daha açık ölçüler üretir; yeni model başarısı değildir.
İlk sonuçlar bir başlangıç çizgisidir. Görülmüş sonuçlara göre geçme sınırı seçilmez.
Önceki kabul kriterleri değişmez. Türkçe doğal toplantı, farklı gün/mikrofon ve
çok konuşmacılı ses henüz bu skorlarla doğrulanmış sayılmaz. Sıfır gözlenen yanlış
kabul gerçek hayatta sıfır risk garantisi değildir. Mevcut recall aralıkları bu
yeni F1/bileşik skora aktarılmaz; bunlar için güven aralığı hesaplanmış değildir.

Standart precision/recall/F1 ve micro/macro tanımları
[scikit-learn birincil dokümantasyonuyla](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html)
uyumludur. `VoiceUp Score`, hata/çekimserlik sayımı ve manifest doğrulaması bu
projeye ait protokol tercihleridir; scikit-learn bağımlılığı eklenmez.
