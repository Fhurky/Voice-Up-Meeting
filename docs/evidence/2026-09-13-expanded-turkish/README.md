# Koşum raporu — 2026-09-13 · Daha geniş Türkçe veride metin ve kişi hafızası değerlendirmesi

1. Sonuç: 3.176 yeni Türkçe kısa kayıt ve 12 yeni toplantı kesiti gerçek yerel modelle tamamlandı; kaynak bazlı skorlar günlüğe kaydedildi — birim 1.231 başarılı / tarayıcı 0 başarılı / atlanan 2; karar bekleyen: yok.
2. Koşulan: Sabit `kt-vibecoding-python-web-v2`; Windows üzerindeki yerel RTX 4060, çevrimdışı Docker çıkarımı ve çalışan FastAPI/PostgreSQL uygulamasının gerçek HTTP akışı. Kod için L1, tamamlanan model/HTTP akışları için L2 gözlendi; L3 veya temsilî 50 kişilik Türkçe başarı iddiası yoktur.

   | Kaynak / görev | Bu turdaki yeni kapsam | Gözlenen sonuç | Kanıt |
   | --- | --- | --- | --- |
   | MediaSpeech Türkçe, konuşmayı metne çevirme | Önceki 80 kayıt hariç 2.433/2.433 klip; 34.852,10 saniye | 71.767 referans kelimede 10.137 hata; kelime hata oranı (WER) **%14,1249** | [Dağılım](mediaspeech-distribution.json), [deney günlüğü](../../../results.md) |
   | FLEURS Türkçe resmî test bölümü | 743/743 klip; 9.380,22 saniye | 12.914 referans kelimede 840 hata; WER **%6,5046** | [Dağılım](fleurs-distribution.json), [kaynak denetimi](fleurs-source-report.md) |
   | Real-TurnTurk `[300,600)` | 6 yeni beş dakikalık kesit, ayrı boş tenant | Yeni kişi görünümü 6/6, bilinen dönüş 6/6; precision/recall/mikro F1/makro F1 %100; VoiceUp Score 100 | [Canlı doğrulama](meeting-live-report.md) |
   | Real-TurnTurk `[600,900)` | 6 yeni beş dakikalık kesit, ikinci boş tenant | Yeni kişi görünümü 6/6, bilinen dönüş 6/6; precision/recall/mikro F1/makro F1 %100; VoiceUp Score 100 | [Toplu karşılaştırma](meeting-comparison.json) |
   | Kaynak kapsamı | Yeni 3.176 klip ve eski 80 klip; toplam 3.256 dosya | 19.544/19.544 denetim; dosya ve çözülen ses örneklerinde tam kopya yok | [Veri denetimi](dataset-coverage-report.md) |
   | MediaSpeech bağımsız sonuç denetimi | 2.433 klibin kaynağı, metni, kontrol noktası ve günlük bağı; ayrı sözcükleme/hata hesabı | 39.004/39.004 kontrol; hata sayıları ve 2.000 tekrar örnekleme aynı | [Bağımsız rapor](mediaspeech-independent-report.md) |
   | FLEURS bağımsız sonuç denetimi | 743 klibin kaynağı, metni, kontrol noktası ve günlük bağı; ayrı sözcükleme/hata hesabı | 12.736/12.736 kontrol; hata sayıları ve 2.000 tekrar örnekleme aynı | [Bağımsız rapor](fleurs-independent-report.md) |
   | Son otomatik paket ve profil kapısı | Kök 493 başarılı / 2 atlanan; backend 605 ve frontend 133 başarılı | Tam kapı çıkış 0; iki bağ sınırı Linux'ta ayrıca 2/2 başarılı | [Son doğrulama](post-performance-verification-report.md) |
   | Güvenlik kapısı | Mevcut çevrimdışı tarayıcı ortamı | Çıkış 2: `required offline security tool is unavailable: gitleaks`; sonraki tarayıcı aşamalarına ulaşılamadı | [Gerçek kapı çıktısı](quality-report.md) |

   Yeni kısa kayıtlar toplam **12,29 saat**, yeni toplantı kesitleri **1 saat** ses sağlar.
   Önceki 80 kısa kayıt korunur; yeni toplam 3.256 Türkçe kısa kayıttır.
   MediaSpeech aynı haber kaynağının kullanılmamış bölümüdür; FLEURS ayrı bir okunmuş konuşma kaynağıdır.
   On iki yeni toplantı kesiti aynı altı kişi ve altı kaynak görüşmenin farklı zaman aralıklarıdır.

   | Metin tanısı | MediaSpeech 2.433 klip | FLEURS 743 klip |
   | --- | ---: | ---: |
   | Yerine koyma / silme / ekleme | 5.303 / 3.224 / 1.610 | 676 / 56 / 108 |
   | Sıfır kelime hatalı klip | 148 | 321 |
   | Klip WER medyanı / yüzde 90 noktası / yüzde 95 noktası | %12,50 / %26,32 / %32,14 | %4,76 / %17,65 / %24,90 |
   | WER > %50 / WER > %100 olan klip | 15 / 0 | 1 / 0 |
   | Klip tekrar örneklemeli %95 aralık | %13,70–%14,56 | %5,90–%7,14 |

   WER, kliplerin hata oranlarının ortalaması değildir: bütün yerine koyma, silme ve eklemeler toplanıp bütün referans kelimelerine bölünür.
   Dağılım raporları ham metinden yeniden hesaplanır; Türkçe normalizasyon `turkish-words-v1` olarak sabittir.
   Tekrar örnekleme aralığı 2.000 sabit tohumlu klip örneklemesine koşulludur; bağımsız kişi/oturum veya Türkçe nüfus güven aralığı değildir.
   İki toplantı zincirinin konuşmacı etiket eşlemesi sonrası kelime hata oranı (cpWER), sırasıyla **1.208/4.032 = %29,9603** ve **1.261/4.143 = %30,4369** kaldı.
   Kimlik F1'in %100 olması, metnin veya konuşmacı zamanlarının kusursuz olduğu anlamına gelmez.
   FLEURS'te daha düşük kelime hatası gözlendi; kaynaklar aynı kişi, içerik ve kayıt koşullarına sahip olmadığından bu farkın tek nedeninin veri türü olduğu söylenemez.

   [Düzeltilmiş tam MediaSpeech hata incelemesi](mediaspeech-error-analysis-v2-report.md), 617 klipte 1.014 sayı temsili adayı,
   242 klipte 267 birleşik/ayrı yazım bloğu ve klip sınırlarında 1.387/3.224 silme (%43) saptadı.
   Bunlar bağımsız ya da birbirini dışlayan hata sınıfları değildir; ses dinlenmeden sayıların anlamca eşit olduğu veya sınırdaki silmenin nedeni kesinleştirilemez.
   Sonraki kalite incelemesinin önceliği sayı/yazım sözleşmesi ile sınırdaki ses–referans kapsamını insan denetimiyle doğrulamaktır; bu tanılar mevcut WER'den çıkarılmadı.
   [FLEURS hata incelemesinde](fleurs-error-analysis-v2-report.md) 42 klipte 51 sayı temsili adayı bulundu;
   aynı sabit hizalama altında klip başı/sonu silmesi yok, 56 silmenin tamamı içerideydi.
   Kaynak referansının yazım biçimi de farklıdır: FLEURS'te 134 referans klibi rakam içerirken MediaSpeech'te hiçbiri içermez.

   Günlükte **24 ayrı deney kaydı** vardır: 18 tamamlanmış, 4 tarihsel skorsuz ve 2 eksik başlangıç girişimi.
   Bu turdaki altı yeni kimliğin dördü tamamlanmış model deneyidir; iki eksik başlangıç 0/2.433 kapsamlıdır.
   Eklenen açıklama paragrafı yalnız bellekte çıkarılarak eski 18 kaydın 48.155 baytlık metni önceki hash ile birebir doğrulandı; gerçek dosya değiştirilmedi. [Koruma kanıtı](ledger-preservation-audit.json).

   Yeniden üretim komutları [Türkçe değerlendirme rehberinde](../../TURKISH_EVALUATION.md),
   model ve kod hashleri [çalışma ortamı kaydında](runtime.json),
   kapsam ve görevler [010 PRD](../../../specs/speaker-identity/PRDs/010-expanded-turkish-benchmark/PRD.md) ve [görevlerinde](../../../specs/speaker-identity/PRDs/010-expanded-turkish-benchmark/tasks.md) tutulur.

3. Maddeler:

   **KUSUR**

   M1 Windows–Docker bağında yinelenen yol çözümlemesi ön kontrolü yavaşlatıyordu; kaynak korumaları korunarak düzeltildi. İlk iki girişim model çalışmadan 0/2.433 kapsamla durduruldu; skorları boş ve ayrı deney kimlikleriyle günlüktedir. [Düzeltme ve test](expanded-asr-runner-report.md).

   M2 PowerShell üzerinden taşınan geçici denetçi kodunda Türkçe harfler bozuldu; bağımsız hesap ve açıklayıcı kategoriler Unicode kaçışlarıyla doğrulandı. Eski tanı raporları işaretlenip v2 ile düzeltildi; model metinleri, WER ve günlük skorları değişmedi. [Tanı düzeltmesi](mediaspeech-error-analysis-v2-report.md).

   **TUZAK**

   M3 FLEURS'ün 743 satırı MALE etiketlidir; 329 cümle kimliği vardır, kalıcı kişi/oturum kimliği yoktur. Bu veri kişi hafızasını, kadın seslerini veya 743 farklı kişiyi sınamaz. [Kaynak](fleurs-source-report.md).

   M4 Toplantı referansının konuşma etkinliği otomatik, metin/zaman doğrulaması eksiktir; sonuç tanısaldır. Her kesitte gerçekten konuşan iki kişi bilgisi verilmiştir; aynı altı kişiyi iki tenant'ta kaydetmek 12 insan değildir. [Sınırlar](meeting-live-report.md).

   M5 Tam kopya denetimi yaklaşık tekrarları, ortak cümleleri, bağımsız oturumları veya modelin ön eğitim verisiyle örtüşmeyi dışlamaz. Kaynaklar birleştirilerek tek başarı yüzdesi üretilmedi. [Kapsam](dataset-coverage-report.md).

   **GÖZLEM**

   M6 Yeni verilerde aynı sabit yerel Whisper large-v3 paketi ve mevcut kimlik/konuşmacı ayarları kullanıldı; üretim eşiği, model ağırlığı ve normalizasyon değiştirilmedi. Önceki küçük örnekle farklı WER çıkması model iyileşmesi değildir. [Sabit ortam](runtime.json).

   M7 Değerlendirici, kaynak/model/ayar/deney/günlük bağıyla klip kontrol noktalarını korur; kesinti sonrası aynı girdilerle devam eder ve tamamlanmış klipleri yeniden modele göndermez. Başarısız veya eksik kayıtlar sessizce paydadan çıkarılmaz. [Regresyonlar](expanded-asr-runner-report.md).

   **AÇIK**

   M8 Doğrulanmış farklı oturumlardan 50 Türkçe kişi, insan denetimli toplantı metin/zaman referansı ve temsilî cihaz/ortam kapsamı tamamlanmadı. [Ek altı kaynak incelemesi](../../../plans/TURKISH_SPEAKER_MEMORY_SOURCES_ADDENDUM.md) erişim ve etiket sınırlarını kaydeder.

   M9 Bağımsız güvenlik taraması eksik araç nedeniyle tamamlanmadı. Bu tur Spark/Apple veya fiziksel mikrofon/tarayıcı çalıştırması yapılmadı; Windows'taki iki atlama Linux başarısıyla silinmedi. [Kapı kanıtı](post-performance-verification-report.md).

   **YAN-ETKİ**

   M10 Yeni kaynak manifestleri, değerlendirme/hazırlama/dağılım araçları, regresyonlar ve toplu kanıtlar eklendi. On iki test toplantısı, iki sıradan deney hesabı/tenant ve altışar profillik iki galeri oluştu; önceki kullanıcı verileri korundu.

   M11 Ham ses, transkript, kimlik eşlemeleri ve hesap bilgileri Git dışındaki `data/` ve `outputs/` altında yereldir. Yeni paket/model indirilmedi; yeni API, şema, migration veya ürün ekranı eklenmedi. Commit/push yapılmadı.
