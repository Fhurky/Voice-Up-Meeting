# Koşum raporu — 2026-09-13 · Eşlenmiş metin düzeltme ölçümü ve deney günlüğü

1. Sonuç: Eksik ölçüm modülü için kırmızı koşumdan sonra ilgili testler geçti — birim 49 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam | Komut | Gözlenen |
   |---|---|---|
   | Windows Python 3.12 araştırma ortamı | `.venv/Scripts/python.exe -m pytest tests/test_transcript_review_evaluation.py` | İlk koşum: eksik modül nedeniyle 5 kurulum hatası |
   | Aynı ortam | `.venv/Scripts/python.exe -m pytest tests/test_transcript_review_evaluation.py tests/test_experiment_ledger.py` | 49 başarılı |

3. Maddeler:

   **KUSUR**
   M1 Metin düzeltmesinin ayrı ölçümü/günlük türü eksikti; `transcript_review_evaluation.py` ve günlük aritmetik denetimleri eklendi, 5 yeni sözleşme testi geçti.

   **TUZAK**
   M2 Düzeltme isabeti, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insanın anlamsal onayı sayılmaz.

   **GÖZLEM**
   M3 Başarısız istek ham metniyle paydada kaldı; noktalama değişimi sözcük başarısı veya temiz metin bozması sayılmadı.

   **AÇIK**
   M4 Bu koşum gerçek model doğruluğu veya `kt-vibecoding-python-web-v2` tam uygulama kapısı değildir; model ve profil kanıtları ayrıca raporlanır.

   **YAN-ETKİ**
   M5 Yeni ölçüm, günlük türü ve sabit Türkçe deney fikstürü oluşturuldu; testler geçici günlük kullandı, eski `results.md` blokları değiştirilmedi.
