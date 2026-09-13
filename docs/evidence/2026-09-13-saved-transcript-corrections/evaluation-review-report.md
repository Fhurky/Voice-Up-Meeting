# Koşum raporu — 2026-09-13 · Seçili model deneyinin salt okunur puanlama ve gizlilik incelemesi

1. Sonuç: Kısmi yanıtın puanlaması ve ayrı durum sayaçlarının deftere aktarılması düzeltildi; ilgili regresyonlar geçti — birim 97 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows Python 3.12 araştırma ortamı. Denetleyici, puanlayıcı, defter, domain ve ilişkili testler incelendi; model üretimi çalıştırılmadı.

   | Komut / kapsam | Gözlenen sonuç |
   |---|---|
   | `python -m pytest tests/test_visible_correction_evaluation.py -q -o addopts=` | Sistem Python'unda pytest bulunmadığı için test başlamadı; mevcut `.venv` kullanıldı. |
   | `.venv/Scripts/python.exe -m pytest tests/test_visible_correction_evaluation.py -q -o addopts= --junitxml outputs/2026-09-13-saved-transcript-corrections/visibility-ledger-red.xml` | Eksik sayaç/sınır davranışı: 23 başarısız, 5 başarılı; 0,31 saniye. |
   | Aynı test, `visibility-ledger-green.xml` | 28 başarılı; 0,19 saniye. |
   | `.venv/Scripts/python.exe -m pytest tests/test_visible_correction_evaluation.py tests/test_experiment_ledger.py tests/test_transcript_review_evaluation.py tests/test_transcript_review_controller.py -q -o addopts= --junitxml outputs/2026-09-13-saved-transcript-corrections/visibility-ledger-regression.xml` | 97 başarılı; 1,72 saniye. |
   | Defter ve görünür sayaç testlerinde Ruff format/check | Başarılı. |
3. Maddeler:

   **KUSUR**

   M1 Eşlenen ve eşlenemeyen önerileri birlikte içeren ya da geçerli JSON ile kesilen yanıtta görünür kısmi metin WER hesabına giriyordu; `scoring_projection` ham metni puanlayıp görünür öneriyi özel satırda koruyacak şekilde düzeltildi ve iki regresyon vakası eklendi (`test_transcript_review_controller.py`).

   M2 `sanitize_result` güvenli sayaçları düşürüyordu; üç alan artık birlikte doğrulanıp korunuyor ve ulaştı/değişmedi/öneri/eşlenemedi/geçersiz durumları ayrı gösteriliyor (`experiment_ledger.py`, 23 yeni regresyonla DÜZELTİLDİ).

   **TUZAK**

   M3 Dört örneklik küme önceden yazılmış regresyondur; kör test veya Türkçe toplantı performansı için temsilî doğruluk tahmini değildir. Model yanıtının kaydedilebilir olması kullanıcı onayı anlamına gelmez.

   **GÖZLEM**

   M4 Modele yalnız kaynak ve komşu bağlam gönderilir; referans metni gönderilmez. Ham/model/referans metinleri `outputs/` altında kalır; defter sınırlı metrikleri, model digest'ini ve kaynak yapılandırması SHA-256 değerini taşır.

   M5 Seçilen model adı/digest'i ve üç üretim kaynak dosyasının birleşik SHA-256 değeri istek çevresinde doğrulanır; port/adaptör/domain bu incelemede değiştirilmedi. Domain'in ters sırada uyguladığı aralıklar ölçümde artan sıraya çevrilir; aralık yeniden oluşturma kontrolü korunur.

   **AÇIK**

   M6 12 özel model satırının yeniden puanlanması ve üç kamu kanıtı/defter kaydının yenilenmesi ana çalışmanın sorumluluğundadır; bu koşum gerçek model veya kullanıcı onayı doğruluğu iddia etmez.

   **YAN-ETKİ**

   M7 Defter ve sayaç testleri değişti; testler yalnız geçici defterler kullandı. Asıl `results.md`, eski kayıtlar, dondurulan model kaynakları, özel model çıktıları ve bağımlılıklar değiştirilmedi.
