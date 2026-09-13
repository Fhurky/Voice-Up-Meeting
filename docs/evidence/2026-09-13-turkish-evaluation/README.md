# Koşum raporu — 2026-09-13 · Türkçe deney altyapısı, veri taraması ve gerçek model karşılaştırması

1. Sonuç: Deney günlüğü, Türkçe ölçüm ve kaynak araçları doğrulandı; bilinen konuşmacı sayısı aynı küçük görüşme kümesinde hafızayı iyileştirdi — birim 1.127 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Gerçek GPU ve HTTP akışında L2 gözlendi; güvenlik kapısı çıkış 2 ile araç eksiğinde kaldı ve 50 kişi için temsilî L3 kabulü yoktur.
2. Koşulan: Sabit `kt-vibecoding-python-web-v2`; Windows/Python 3.12 araştırma araçları, Linux/Python 3.13 FastAPI/PostgreSQL 17 ve RTX 4060 Laptop 8.188 MiB. Mevcut doğrulanmış model imajı ve ağırlıklar kullanıldı; [ortam ve sürümler](runtime.json).

   | Koşum | Gerçek kapsam ve sonuç | Kanıt |
   |---|---|---|
   | Veri taraması | Görev, kişi/oturum etiketleri, referans niteliği, kapsam ve lisansa göre açık/kurumsal Türkçe kaynaklar karşılaştırıldı | [Araştırma](../../../plans/TURKISH_DATASET_RESEARCH.md) |
   | Real-TurnTurk hazırlama | 25 kaynak dosyası, 244.542.070 bayt; 6 × 180 saniye gerçek görüşme, 6 farklı kişi | [Hazırlama](preparation-report.md), [otomatik hizalama tanılaması](source-alignment.json) |
   | MediaSpeech Türkçe | Sabit arşivden 40 geliştirme + 40 ayrı test klibi; 80 farklı ses hash'i | [Seçim kararı](asr-selection.json), [dosya koruması](asr-wrapper-report.md) |
   | ASR geliştirme taban çizgisi | Sabit Türkçe: 40/40 klip, 182/1.140 kelime hatası = %15,96 | [Toplu sonuç](asr-dev-tr.json) |
   | ASR geliştirme adayı | Otomatik dil: aynı 40/40 klip, aynı 182/1.140 hata; 40 metnin tamamı aynı, kazanç yok | [Toplu sonuç](asr-dev-auto.json) |
   | Ayrılmış ASR testi | Seçimden sonra sabit Türkçe: 40/40 klip, 193/1.199 hata = %16,10 | [Toplu sonuç](asr-heldout-tr.json) |
   | Gerçek uygulama taban çizgisi | Altı görüşme gerçek giriş, parçalı yükleme, analiz ve kalıcı profillerle tamamlandı; galeri 2→2→2→4→5→6 | [Toplu sonuç](meeting-baseline.json) |
   | Gerçek uygulama sayısı bilinen aday | Aynı kaynaklar yeni boş tenant'ta, `expected_speakers=2` ve `participant_count=2`; altı görüşme tamamlandı, galeri 2→2→3→4→5→6 | [Toplu sonuç](meeting-count2.json), [eşlenmiş karşılaştırma](meeting-comparison.json) |
   | Son canlı kontrol | İki sıradan giriş, on iki başarılı toplantı, iki altışar profilli galeri ve gerçek sayı alanları doğrulandı | [16 HTTP kontrolü](live-final-report.md) |
   | Bağımsız günlük denetimi | 18 deneyde 676 içerik/hash/aritmetik/gizlilik kontrolü ve beş gerçek CLI yeniden yansıtması geçti | [Son denetim](ledger-final-audit-report.md) |
   | Son araştırma regresyonu | On ilgili test dosyasında 389 başarılı, sıfır başarısız/atlanan; etkilenen 17 Python dosyasında Ruff lint/format geçti | JUnit (Git dışı yerel çıktı: `../../../outputs/2026-09-13-turkish-evaluation/evaluation-tests-final.xml`) |
   | Tam profil kapısı | `scripts/quality-gate.sh all`: 605 backend + 133 frontend başarılı, çıkış 0 | Yerel tam günlük (Git dışı yerel çıktı: `../../../outputs/2026-09-13-turkish-evaluation/quality-gate.txt`) |
   | Güvenlik kapısı | `scripts/security-gate.sh`: gerçek kapı çıkışı 2, `required offline security tool is unavailable: gitleaks` | Yerel günlük (Git dışı yerel çıktı: `../../../outputs/2026-09-13-turkish-evaluation/security-gate.txt`) |

   Son araştırma komutu:

   ```text
   .venv/Scripts/python.exe -m pytest tests/test_experiment_ledger.py tests/test_public_speaker_metrics.py tests/test_public_speaker_report.py tests/test_public_speaker_evaluation.py tests/test_meeting_metrics.py tests/test_score_meeting_transcript.py tests/test_turkish_meeting_evaluation.py tests/test_run_meeting_evaluation.py tests/test_turkish_asr_dataset.py tests/test_prepare_turkish_meeting_evaluation.py -q --junitxml=outputs/2026-09-13-turkish-evaluation/evaluation-tests-final.xml
   ```

   **Aşağıdaki hafıza skorları zayıf referanslı tanılayıcı ölçümlerdir:** etkinlik
   otomatik, metinlerin insan doğrulaması ve kesin zaman hizası onaylanmış değildir.
   Altı kişiyle 50 kişilik veya genel nüfusta biyometrik doğruluk iddiası kurulmaz.
   İlk görünümlerden sonra altı planlı dönüş vardır; ilk kayıt başarısızlıkları
   sonraki bilinen kişi paydasından çıkarılmadı.

   | Ölçüm | Sayı verilmeden | İki konuşmacı bilgisiyle |
   |---|---:|---:|
   | Doğrulanan bilinen dönüş | 3/6 | 5/6 |
   | Kimlik precision | %100 | %100 |
   | Planlı recall | %50 | %83,33 |
   | Mikro F1 | %66,67 | %90,91 |
   | Makro F1 | %50 | %75 |
   | Bilinmeyen kişi F1 | %66,67 | %83,33 |
   | VoiceUp Score | 57,14 | 78,95 |
   | İlk görünümde profil kapsamı | 4/6 | 5/6 |
   | Zincir sonunda birikimli profil kapsamı | 6/6 | 6/6 |
   | Referansla kişi eşlemesi geçen görüşme | 5/6 | 6/6 |
   | Tanılayıcı kişi eşlemeli kelime hatası | 734/2.341 = %31,35 | 651/2.341 = %27,81 |

   İki koşumun altı kaynak hash'i ve altı zaman sıralı normalize kelime akışı
   aynıydı. Kişi eşlemeli 83 kelime hatası azalması yeni kelime üretiminden
   kaynaklanmadı. Aynı sesler iki kez işlendi; 12 bağımsız görüşme kaynağı veya
   12 farklı kişi sayılmaz. Üç ASR koşumu da 120 işlem fakat 80 farklı kliptir.

   Uygulama için karar, konuşanların kesin sayısı bilindiğinde mevcut sayısal
   girdiyi kullanmaktır. Katılanların üst sınırı ile kesin konuşan sayısı ayrı
   tutulur. Model ailesi, otomatik varsayılanlar, kimlik eşikleri ve 20 saniyelik
   kabul sınırı değişmedi. Türkçe büyük/küçük harf ölçümü sürümlü seçenekle
   düzeltildi; bu düzeltme model eğitimi olarak sunulmadı.

3. Maddeler:

   **KUSUR**

   M1 DÜZELTİLDİ: Türkçe `I/ı` ve `İ/i` ayrımı genel normalizasyonla hatalı ölçülebiliyordu; eski varsayılan korunarak `turkish-words-v1` ve 53 ilgili regresyon eklendi. [Dil ölçümü](normalization-report.md)
   M2 DÜZELTİLDİ: Kaynak WebM damgaları tekrar/sıçrama içeriyordu; veri hazırlama ilk denemede durdu, örnek sırasını kayıpsız koruyan kayıtlı politika ve 18 testle hazırlandı. [Hazırlama](preparation-report.md)
   M3 DÜZELTİLDİ: Yeni günlük bütünlük alanı eski kayıtları yanlışlıkla reddetti; otomatik dil koşumu 40/40 tamamlandıktan sonra yayınlama çıkışı 1 oldu. Kaydedilmiş sonuç model yeniden çalıştırılmadan standart komutla eklendi. [Günlük düzeltmesi](ledger-report.md)
   M4 DÜZELTİLDİ: İlk kayıt kapsamı ile zincir sonunda oluşan toplam galeri karışabiliyordu; eski kayıt korunup açıklama eklendi, yeni sonuçlarda iki oran ayrıldı. [Kapsam düzeltmesi](ledger-coverage-correction-report.md)
   M5 İYİLEŞTİRİLDİ: Üçüncü görüşmedeki belirsiz yeni kişi kaydı ve altıncı görüşmedeki bölünme, kesin iki konuşmacı girdisiyle bu geliştirme örneklerinde düzeldi; eşikler gevşetilmedi. [Tanı ve regresyon](known-count-candidate-report.md)

   **TUZAK**

   M6 Kaynak etkinliğiyle %96,42 kare uyumu bağımsız insan doğruluğu değildir; beş sınır aşan referans cümlesi hariç tutulurken ses/model sözleri korunur. Tanılayıcı metin skorunda bu sınır etkisi vardır.
   M7 MediaSpeech kişi/oturum kimliği sağlamaz; klip ayrımı bunların bağımsızlığını kanıtlamaz. Model `segment.text` ölçümü uygulamanın kelime zamanı/gruplama sonrası nihai transkriptiyle özdeş kabul edilmez.
   M8 İlk taban çizgisindeki üç kayıp üç yanlış kişiye eşleme değildir: iki önceki profil oluşmaması ve bir referans bölünmesidir. Doğrulanamayan bir kalıcı kabul gerçekleşirse değerlendirici bunu muhafazakâr biçimde başarısız sayar; kesin insan referansı eksiktir.
   M9 Geliştirme adayları aynı sesleri tekrar kullanır; yeni deney kimliği bağımsız yeni örnek anlamına gelmez. Eski günlüğün devam sürümleri ve yeniden yayımlanan kanıtlar da yeniden model koşumu değildir.

   **GÖZLEM**

   M10 Sayısı bilinen adayda kalan bir dönüş kaybı, ilk görüşmede yalnız 10,893 saniye kullanılabilir konuşması olan kişidir; daha sonra yeterli konuştuğunda ilk profili oluştu. Güvenli kısa konuşma kuralı korundu.
   M11 Günlük 13 geçmiş deney ile beş yeni Türkçe model koşumunu içerir; reddedilmiş İngilizce ASR adayları ve referanssız eski Türkçe deneme görünürdür. [Günlük](../../../results.md), [kullanım](../../EXPERIMENTS.md)
   M12 Tam kapı ayrı ve benzersiz `_test` veritabanında migrasyon/entegrasyon çalıştırıp veritabanını düşürdü; uygulama veritabanına migrasyon uygulanmadı. OpenAPI, frontend tipleri, yönetişim ve chart kontrolleri geçti.

   **AÇIK**

   M13 Gerçek 50 kişi, farklı gün/cihaz, geniş doğal örtüşme ve insan doğrulanmış Türkçe toplantı referansı ölçülmedi. 18 dakikalık kaynak dört saatlik toplantı veya Spark/Apple ortam kanıtı değildir.
   M14 Güvenlik taraması `gitleaks` eksik olduğu için başlayamadı; Semgrep/Trivy aşamalarına ulaşılamadı. Bu eksik geçiş gibi gösterilmedi.

   **YAN-ETKİ**

   M15 Yeni Accepted 009 spesifikasyonu, araştırma/kullanım belgeleri, atomik günlük ve veri/değerlendirme araçları eklendi. Ham veri, metinler, özel kimlik eşlemeleri ve kimlik bilgileri ignore edilen `data/` ve `outputs/` içindedir.
   M16 İki ayrı sıradan değerlendirme hesabı/tenant, toplam 12 toplantı ve iki ayrı altışar profillik deney galerisi oluşturuldu. Mevcut kullanıcı kayıtları ve ilk başarısız deney silinmedi; uygulama yerel modda açık bırakıldı.
   M17 Önceki arayüz/mikrofon değişiklikleri korundu; bu görevde commit veya push yapılmadı. Yeni paket/model ağırlığı kurulmadı; mevcut imaj kullanıldı. Sonradan yalnız kanıt ve dokümantasyon tamamlandı.
