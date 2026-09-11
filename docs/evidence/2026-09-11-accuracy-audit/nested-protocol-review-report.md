# Koşum raporu — 2026-09-11 · Kontrollü galeri protokolünün bağımsız ölçüm ve çok satırlı karar denetimi

1. Sonuç: Protokol incelemesinde ölçüm niyetini bozan yeni hata bulunmadı; çok satırlı karar kontrolleri ve final sonuçların bağımsız yeniden sayımı geçti — bağımsız CPU assertion 14 başarılı / sayaç ve oran karşılaştırması 48 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Yeni ses/model deneyi 0; bu kontroller ana 2.035 testlik süite eklenmez.
2. Koşulan: `kt-vibecoding-python-web-v2`, yerel Python 3.13; `outputs/2026-09-11-accuracy-audit/nested-gallery190-v6/` içindeki `protocol.json`, `client.py`, `score.py`, `run.py` ve `publish.py` salt okunur incelendi. Donmuş gerçek `score.py` fonksiyonları model çağırmadan çalıştırıldı; beklenen kararlar ve sayaçlar ayrı sabit örneklerle karşılaştırıldı. Final denetimde `nested-v6-final-consistency.py`, kaynak manifesti, 190 çıkarım önbelleği ve özel/kamusal sonuçları bağımsız yeniden saydı; `score.py` özet fonksiyonu kullanılmadı.

   | Denetim | Kapsam / sonuç |
   |---|---|
   | Çok satırlı klip kararı | 8 örnek: boş, bütün satırlar niteliksiz, kısmi kullanılabilir tanınmış/bilinmeyen, aynı veya farklı tanınmış kimlik, bütün satırlar bilinmeyen, tanınmış+bilinmeyen; tamamı beklenen sonucu verdi |
   | Kısmi kullanılabilirlik | 1 kontrol: kullanılabilir satırlar aynı kişiyi tanısa da kullanılamayan satır bulunan klip belirsiz kalır; tanınmış diye sayılmaz |
   | Ayrı kalıcılık çatışması tanısı | 5 örnek: aynı kazananlı yerel ayrım, yalnız değen aralıklar, pozitif zaman örtüşmesi, farklı kazananlar ve niteliksiz karşı satır; sayaçlar doğru, mevcut kararlar değişmedi |
   | Payda ve yanlış kimlik kuralları | Her aşamada 140 sorgu tutuluyor; planlı galeri içindeki yanlış kimlik FP+FN, başarısız kayıt sorgusu FN. Planlı galeri dışı ve hiçbir zaman kaydedilmeyen kişiler negatif gruplarda ayrı tutuluyor |
   | Sayısal ve model sınırı | Galeri/sorgu 192 vektörü gerçek `checked_vector` ardından float32; 256 vektörü ham kalite çıktısı ardından float32. Ayrı sıralamalar, gerçek `decide` ve `fuse_populations`; modellerin vektörleri birleştirilmiyor |
   | Referans ayrımı | Çıkarım istemcisine yalnız kaynak SHA, çerçeve sayısı, backend hashleri ve WAV gönderiliyor. Corpus kişi/rol bilgisi yalnız CPU ölçümüne giriyor; metin, dil veya kişi sayısı ipucu modele gitmiyor |
   | Yayıncı | Planlanan/gerçek galeri, bütün kayıt kabulleri, başarısız/niteliksiz klip durumları ve ayrı çatışma sayımları korunuyor; final kamusal aşamalar özel sonuçların tamamıyla eşleşti |
   | Final çıkarım | 190 tamamlanan klip, 194 yerel / 193 birleşik satır; 3 çok satırlı klip, 191 kullanılabilir / 2 yetersiz konuşmalı satır, 188 bütün satırları kullanılabilir klip; hiçbir satır atılmadı |
   | Final sayaç oracle'ı | 3 karar uzayı × 4 sorgu grubu × 4 galeri aşaması = 48 sayaç/oran özeti ayrı algoritmayla yeniden hesaplandı; 140 benzersiz sorgu her aşamada korundu |
   | Kaynak ve çalıştırma bağı | 190 önbelleğin kaynak SHA, protokol, 22 backend dosyası, model kimliği, çıkış kodu, satır sayısı ve vektör boyutları doğrulandı; kamusal çıktı, yayıncı ve tamamlanma kaydı hashleri eşleşti |

   | Planlanan / gerçek galeri | `fused` doğru / planlı bilinen sorgu | Yanlış pozitif | Kaçırılan bilinen | Hiç kaydedilmeyen 40 sorgu: bilinmeyen / belirsiz |
   |---|---:|---:|---:|---:|
   | 5 / 5 | 10 / 10 | 0 | 0 | 40 / 0 |
   | 10 / 10 | 20 / 20 | 0 | 0 | 39 / 1 |
   | 20 / 20 | 40 / 40 | 0 | 0 | 37 / 3 |
   | 50 / 49 | 95 / 100 | 0 | 5 | 30 / 10 |

   Son aşamada planlı galeri recall değeri `95/100 = %95`, gerçekten kabul edilmiş kişilerde `95/98 = %96,94`, precision `95/95 = %100`, planlı galeri F1 değeri `190/195 = %97,44` bulundu. Beş kaçırmanın ikisi başarısız profil kabulüne aittir; bunlar paydadan çıkarılmadı. Diğer üçü bir kısmen kullanılabilir çok satırlı sorgu, bir kullanılabilir satırlar arası anlaşmazlık ve bir düşük güvenli tek satırlı sorgudur. Bu son neden ayrımı ayrıca salt okunur yeniden sayıldı; ayrı ham kanıt dosyası veya hash iddiası yoktur.

   | Kanıt | SHA-256 |
   |---|---|
   | `nested-gallery190-v6/protocol.json` | `b424dc8e41f46a36fd7678d3df6dd96c2467fce71776627546033fb14ff1d7bc` |
   | `nested-gallery190-v6/client.py` | `de0ba2e67553bfc9417e039b25db4c3d0e1b1d9288a733e8637ec4746371e635` |
   | `nested-gallery190-v6/score.py` | `d5967cd3bd5ec96686a0b4e108e070acefc524dbafa1d266d584bb9ff080b3d0` |
   | `nested-gallery190-v6/run.py` | `6b42729d63147661cb394df97f3a7d39eaa87e25a936686565c112f61c72b30b` |
   | İlk incelenen publisher; korunan `nested-gallery190-v6/publish-reviewed-2026-09-11.py` | `5ee5a148760e143f56777b739486921f36a25560fb55424e9bc2920c5d37ca77` |
   | Tarihsel ara publisher sürümü; provenance eklemesi ayrıca incelendi | `4e7371eeed42cda8c0374ed7a9db98cd863b5a1331f482c462e1736ea64528ca` |
   | Final `nested-gallery190-v6/publish.py` | `e44d499a1e86d2df436ed2d6bc7b7fafaf91b82e580ca4b3b84d094d3cd3f4aa` |
   | `nested-v6-multitrack-review.json` | `557381c30fb436c1f96a3a9e7b00422d6b7bec88ec2cac7d3c93462bbd8e8dca` |
   | Önceki `nested-v3-independent-review.json` | `c218a772eccd35baa7087e3ed0093872770809951398858a8cefde1044ae00f6` |
   | `nested-v6-final-consistency.py` | `6cf4fdbe699cfc9eca8e5e2743f3f2faa1897f5e2f2717729983b739c48d9ff7` |
   | `nested-v6-final-consistency.json` | `dc4797718debc3acd1d7b7f2822c135ba44f1890683eb083c71c4258cd2ca67a` |
   | `nested-gallery190-v6/results.private.json` | `c8110658168a5cd9cd55825945975459b92d100ae627a11abd1371d74d999dec` |
   | `nested-gallery190-v6/completion-fence.json` | `ea8ce8bd09a729f42260732158aa0a2be996b15d284ad7eb087c419b8d2df841` |
   | [Kamusal sonuç](nested-gallery-results.json) | `a65133008b9bc695da7e222528ca7be2293ec6e8f3c564e05e0a8c006caa35f0` |
   | [Kamusal koşum raporu](nested-gallery-report.md) | `eacb681a399bc5334658ed527bef987b4318c9554f77c0c809fbbdc989e9a6e8` |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Dört aşamada aynı 140 benzersiz sorgu yeniden puanlanır: toplam 560 ilişkili `fused` karar vardır; aynı kişinin iki kaydı da bağımsız sayılmaz. Planlı bilinen oranı aşamalar arasında değiştiği için yalnız galeri büyüklüğünün nedensel etkisi ölçülmez; ECAPA192/Community256 ek birincil deney değildir.
   M2 Gözetimli galeri kabulü sıralı yeni kişi keşfini ölçmez. Gerçek `fuse_populations` sonucu son `MeetingMemory.conflicting_assignment` veya profil kalıcılığı sonucu değildir; çatışmalar ayrıca sayılır, kararlar bu tanıyla değiştirilmez.
   M3 Publisher protokolün `runner_sources` listesine dahil değildir; ara ve final sürümlerin provenance, tamamlanma kaydı, anonim kaçırma nedenleri ve kapsam yorumları ayrıca incelendi. Skor, payda ve model davranışı değişmedi; CPU kosinüsü PostgreSQL SIMD hesabıyla bit düzeyinde eşitlik iddiası taşımaz.

   **GÖZLEM**

   M4 Önceki bağımsız v3 payda oracle'ı tekrar çalıştırılmadı; yeni 14 kontrol yalnız çok satırlı karar ve çatışma tanısı boşluklarını kapsar. Yeni assertion çıktısı ignored `outputs/2026-09-11-accuracy-audit/nested-v6-multitrack-review.json` dosyasında korunuyor.
   M5 `client.py`, `score.py` ve `run.py` byte hashleri donmuş protokolle eşleşti; başarısız kayıt veya sorgular sessizce değiştirilmez, tamamlanan çıkarım her galeri aşamasında yeniden çalıştırılmaz.
   M6 Final 48 sayaç/oran karşılaştırması `outputs/2026-09-11-accuracy-audit/nested-v6-final-consistency.json` içinde kayıtlıdır; mevcut çıkarımlar yeniden sayıldı, yeni model doğruluk deneyi yapılmadı. Bütün 190 klip ve dört aşamanın özel/kamusal toplamları eşleşti.

   **AÇIK**

   M7 Gerçek veritabanı/profil kalıcılığı, tam toplantı ve Türkçe doğal ses kalitesi burada sınanmadı. Bu kaynaklar önceki toplantı incelemelerinde gözlendi; yeni kör doğrulama verisi veya eğitim verisinden kişi bağımsızlığı iddiası yoktur.

   **YAN-ETKİ**

   M8 Yalnız ignored kontrol çıktıları, final yeniden sayım yardımcısı ve bu kanıt raporu oluşturuldu/güncellendi; üretim/protokol/runner kaynakları, sesler, modeller ve veritabanı değiştirilmedi. GPU çağrısı, profil yazısı ve yeni model deneyi sıfırdır.
