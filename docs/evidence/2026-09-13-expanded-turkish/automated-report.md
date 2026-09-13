# Koşum raporu — 2026-09-13 · Geniş Türkçe değerlendirme son regresyonu

1. Sonuç: Mevcut ve genişletilmiş değerlendirme davranışları birlikte geçti — birim 492 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows/Python 3.12 değerlendirme ortamı, sabit `kt-vibecoding-python-web-v2`; 13 Python test dosyasında 492 başarılı, 0 başarısız, 0 hata, 0 atlanan; 131,163 saniye. Etkilenen 12 Python dosyasında Ruff lint ve biçim kontrolü geçti. JUnit (Git dışı yerel çıktı: `../../../outputs/2026-09-13-expanded-turkish/evaluation-tests-final.xml`).

   ```text
   .venv/Scripts/python.exe -m pytest tests/test_experiment_ledger.py tests/test_public_speaker_metrics.py tests/test_public_speaker_report.py tests/test_public_speaker_evaluation.py tests/test_meeting_metrics.py tests/test_score_meeting_transcript.py tests/test_turkish_meeting_evaluation.py tests/test_run_meeting_evaluation.py tests/test_turkish_asr_dataset.py tests/test_prepare_turkish_meeting_evaluation.py tests/test_expanded_turkish_asr.py tests/test_expanded_asr_report.py tests/test_prepare_fleurs_turkish.py -q --junitxml=outputs/2026-09-13-expanded-turkish/evaluation-tests-final.xml
   ```

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Dar alt koşumlardaki testler burada tekrar bulunur; 492'ye alt koşum sayıları tekrar eklenmez. Tam profilin ayrı 605 backend + 133 frontend testiyle toplam 1.230 testtir.

   **GÖZLEM**

   M2 Eski kimlik metrikleri/günlük aktarımı, eski Türkçe ASR, yeni kaynak doğrulaması, kesinti/devam, sabit pencereler ve anonim dağılım aynı koşumda geçti.

   **AÇIK**

   M3 Birim testleri gerçek model doğruluğu veya 50 kişi başarısı değildir; canlı model/HTTP ölçümleri ayrıca raporlanır.

   **YAN-ETKİ**

   M4 Geçici pytest dosyaları ve JUnit kanıtı oluştu; ham kaynaklar, model ağırlıkları, uygulama galerileri ve gerçek günlük bu testlerle değiştirilmedi.
