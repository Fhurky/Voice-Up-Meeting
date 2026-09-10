# Koşum raporu — 2026-09-09 · Değerlendiricide zorunlu ön işleme kaydı ve güvenli toplu sayımlar

1. Sonuç: İsteğe bağlı sürüm zorunluluğu eski koşum uyumunu koruyor; yeni kaynak bölümü ve güvenli sürüm sayımı raporlanıyor — birim 72 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Kontrol | Ortam / komut | Sonuç |
   | --- | --- | --- |
   | Kırmızı | Windows Python 3.13.14; `pytest tests/test_public_speaker_evaluation.py tests/test_public_speaker_report.py -k 'provenance or preprocessing or fresh_train_clean' -q -o addopts=` | 15 beklenen hata / 1 eski uyum kontrolü başarılı; [çıktı](evaluator-provenance-red.txt), [JUnit](evaluator-provenance-red.xml) |
   | Son iki paket | Aynı Python; `pytest tests/test_public_speaker_evaluation.py tests/test_public_speaker_report.py -q -o addopts=` | Değerlendirici 59, raporlayıcı 13 başarılı; toplam 72; [çıktı](evaluator-provenance-tests.txt), [JUnit](evaluator-provenance-tests.xml) |
   | Statik kontrol | Mevcut Ruff ile dört değişen dosyada `check` ve `format --check`; `git diff --check` | Başarılı; [çıktı](evaluator-provenance-static.txt) |

3. Maddeler:

   **KUSUR**
   M1 Yeni holdout'un `train-clean-100` bölümü sabit rapor katmanlarından eksikti. Başarılı ve başarısız sorguların paydasıyla birlikte eklendi; kaynak katmanı regresyonu geçti. DÜZELTİLDİ.

   **TUZAK**
   M2 `--require-preprocessing-provenance`, iki kabul edilen sürümü `binding.required_preprocessing_versions` içine sabitler; mevcut koşumda açılıp kapatılamaz. Argüman verilmezse tarihsel binding birebir korunur.
   M3 Zorunlu modda eksik/bozuk başarılı sonuç `frozen_inference_contract_changed` üretir; ret sonrası operasyon başarıya geçirilmez. Devam ederken saklanan başarılı sonuçlar da kontrol edilir; başarısız işler için sürüm şartı aranmaz.

   **GÖZLEM**
   M4 Toplu sürüm sayımı yalnız başarılı operasyonları sayar; iki bilinen etiket ve `unreported_or_unsupported` alanı kullanır. Serbest metadata, adlar veya tanımsız sürüm metinleri bu sayaca kopyalanmaz.
   M5 Bu değişiklik 16 değerlendirici ve 2 raporlayıcı olmak üzere 18 yeni vaka ekledi. Testler ayrı loopback HTTP fikstürü kullanır; gerçek model doğruluğu veya Spark dağıtım kanıtı değildir.

   **AÇIK**
   M6 Yeni seçenekle gerçek uygulama doğrulaması ve son tam kalite kapısı ana görevdedir; bu rapor L1 otomatik kanıttır.

   **YAN-ETKİ**
   M7 Yalnız iki değerlendirme/raporlama betiği, iki ilgili test dosyası ve bu kanıtlar değişti. Gerçek uygulama, Spark, veri setleri ve eski koşum dosyaları bu testlerde kullanılmadı veya değiştirilmedi.
