# Koşum raporu — 2026-09-13 · Yeni görünür öneri politikasının deney kimliği

1. Sonuç: Yeni protokol için beklenen eksik davranış gözlendi — birim 4 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows Python 3.12 araştırma ortamı; `pytest tests/test_visible_correction_evaluation.py -q -o addopts=`; 1 başarısız, 4 başarılı, 0,11 saniye.
3. Maddeler:

   **KUSUR**
   M1 `test_visible_protocol_is_bound_to_its_new_policy` yeni görünür protokolü kabul edemedi; `invalid_review_protocol` beklenen kırmızı kanıttır.

   **TUZAK**
   M2 Bu bir model veya uygulama testi değildir; eski filtreli deneylerle yeni öneri görünümünün birbirine karışmasını önleyen günlük sözleşmesidir.

   **GÖZLEM**
   M3 Eski sonuç biçimi ve üç yanlış politika reddi başarılı.

   **AÇIK** — yok

   **YAN-ETKİ**
   M4 Beş sözleşme testi eklendi; gerçek model ve deney günlüğüne yazılmadı.
