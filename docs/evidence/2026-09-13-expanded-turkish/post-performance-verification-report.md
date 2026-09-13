# Koşum raporu — 2026-09-13 · Ön kontrol performans düzeltmesinden sonra son doğrulama

1. Sonuç: Son değerlendirme kodunda kök regresyonları ve tam profil kapısı geçti — birim 1.231 başarılı / tarayıcı 0 başarılı / atlanan 2; karar bekleyen: yok.
2. Koşulan: Sabit `kt-vibecoding-python-web-v2`; kök değerlendirme testleri Windows/Python 3.12, tam profil Git Bash üzerinden yerel Docker Linux/Python 3.13, PostgreSQL 17 ve React/Vite ortamında çalıştı. Bu tekrar GPU kullanmadı ve model koşumuna müdahale etmedi.

   | Koşum | Gözlenen sonuç | Kanıt |
   | --- | --- | --- |
   | 13 dosyalık kök değerlendirme paketi | 495 test: 493 başarılı, 0 başarısız/hata, 2 atlanan; 121,151 saniye; çıkış 0 | Yeni JUnit (Git dışı yerel çıktı: `../../../outputs/2026-09-13-expanded-turkish/evaluation-tests-post-performance.xml`) |
   | 12 etkilenen Python dosyasında Ruff lint ve biçim kontrolü | İkisi de başarılı; biçim kontrolü 12 dosyayı değiştirmeden kabul etti | Aşağıdaki tam komutlar |
   | `scripts/quality-gate.sh all` | Çıkış 0; backend 605/605 ve frontend 133/133 başarılı, bu kapıda atlanan yok | Yeni tam kapı günlüğü (Git dışı yerel çıktı: `../../../outputs/2026-09-13-expanded-turkish/quality-gate-post-performance.txt`) |
   | Aynı iki sembolik bağ durumunun ayrı Linux kanıtı | Kaynak dosya ve kaynak üst dizininde gerçek sembolik bağlar reddedildi; 2/2 denetim başarılı | [Önceki ayrı Linux kanıtı](preflight-performance.json), [yürütücü raporu](expanded-asr-runner-report.md) |

   Kök paket komutu:

   ```text
   .venv/Scripts/python.exe -m pytest tests/test_experiment_ledger.py tests/test_public_speaker_metrics.py tests/test_public_speaker_report.py tests/test_public_speaker_evaluation.py tests/test_meeting_metrics.py tests/test_score_meeting_transcript.py tests/test_turkish_meeting_evaluation.py tests/test_run_meeting_evaluation.py tests/test_turkish_asr_dataset.py tests/test_prepare_turkish_meeting_evaluation.py tests/test_expanded_turkish_asr.py tests/test_expanded_asr_report.py tests/test_prepare_fleurs_turkish.py -q --junitxml=outputs/2026-09-13-expanded-turkish/evaluation-tests-post-performance.xml
   ```

   Statik kontrol komutları:

   ```text
   .venv/Scripts/python.exe -m ruff check scripts/experiment_ledger.py scripts/prepare-turkish-meeting-evaluation.py scripts/run-turkish-meeting-evaluation.py scripts/evaluate-expanded-turkish-asr.py scripts/report-expanded-turkish-asr.py scripts/prepare-fleurs-turkish.py tests/test_experiment_ledger.py tests/test_prepare_turkish_meeting_evaluation.py tests/test_turkish_meeting_evaluation.py tests/test_expanded_turkish_asr.py tests/test_expanded_asr_report.py tests/test_prepare_fleurs_turkish.py
   .venv/Scripts/python.exe -m ruff format --check scripts/experiment_ledger.py scripts/prepare-turkish-meeting-evaluation.py scripts/run-turkish-meeting-evaluation.py scripts/evaluate-expanded-turkish-asr.py scripts/report-expanded-turkish-asr.py scripts/prepare-fleurs-turkish.py tests/test_experiment_ledger.py tests/test_prepare_turkish_meeting_evaluation.py tests/test_turkish_meeting_evaluation.py tests/test_expanded_turkish_asr.py tests/test_expanded_asr_report.py tests/test_prepare_fleurs_turkish.py
   ```

   Tam kapının çalıştırıldığı PowerShell sarmalayıcısı:

   ```powershell
   $env:MSYS2_ARG_CONV_EXCL='/tmp;/workspace'
   $env:Path="$env:USERPROFILE\bin;C:\Program Files\Git\bin;"+$env:Path
   & 'C:\Program Files\Git\bin\bash.exe' scripts/quality-gate.sh all 2>&1 | Tee-Object -FilePath outputs/2026-09-13-expanded-turkish/quality-gate-post-performance.txt
   exit $LASTEXITCODE
   ```

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Windows hesabında sembolik bağ oluşturma yetkisi olmadığı için `test_linked_source_path_is_refused[source_file]` ve `[source_parent]` atlandı. Aynı iki durumun Linux başarısı Windows JUnit sonucunu değiştirmez; 1.231 toplamına ayrıca eklenmedi.

   M2 PowerShell, Alembic'in stderr bilgi satırlarını `NativeCommandError` başlığı altında gösterebilir. Gerçek kapı çıkışı 0, tüm `KT_GATE_STEP` durumları başarılı ve test sayaçları 605/133'tür.

   **GÖZLEM**

   M3 Denetimin başında ve sonunda değerlendirici SHA-256 aynıydı: `c6df5fa1c158db423df324f50900bd495a9ddef6ab54b7dbd606d259e5821310`. Kaynak koduna veya model ayarlarına bu koşumda dokunulmadı.

   M4 Bağımlılık kabulü, yapılandırma eşlemesi, migration, formatter/lint/type, canlı PostgreSQL entegrasyonu, şema drift, OpenAPI ve frontend tip sözleşmeleri, üretim derlemesi, yönetişim ve chart denetimleri geçti. Geçici test veritabanı oluşturulup migration/test yapıldı ve sonunda `database-test-drop` başarılı oldu.

   **AÇIK**

   M5 Güvenlik kapısı bu tekrarın kapsamına alınmadı; önceki koşumdaki `required offline security tool is unavailable: gitleaks` engeli ve Semgrep/Trivy aşamalarına ulaşılamaması [güvenlik raporunda](quality-report.md) açık kalır. Güvenlik taraması başarılı sayılmaz.

   M6 Bu rapor otomatik L1 kanıtıdır; model doğruluğu veya 50 kişi başarısı değildir. Gerçek toplantı HTTP doğrulaması [ayrı L2 raporundadır](meeting-live-report.md); geniş ASR model sonuçları ayrıca kaydedilir.

   **YAN-ETKİ**

   M7 Yeni JUnit, yeni kapı günlüğü ve bu rapor oluşturuldu; önceki raporlar korunmuştur. Pytest geçici dosyaları ve yalnız kapıya ait geçici veritabanı yaşam döngüsü kullanıldı; uygulama galerileri, gerçek günlük, ham veri ve model ağırlıkları değiştirilmedi.
