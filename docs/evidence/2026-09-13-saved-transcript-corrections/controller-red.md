# Koşum raporu — 2026-09-13 · Seçili model ve görünür çıktı deney yürütücüsü

1. Sonuç: Yeni görünür model yolu için beklenen eksik davranışlar gözlendi — birim 8 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows Python 3.12; `pytest tests/test_transcript_review_controller.py -q -o addopts=`; 3 başarısız, 8 başarılı, 0,36 saniye.
3. Maddeler:

   **KUSUR**
   M1 Yeni model kimliği, ham cevap ve görünür öneri politikası için üç test eski kaynak karma yolunda durdu; yeni mod henüz uygulanmamıştı.

   **TUZAK**
   M2 HTTP/model sınırı imza kısıtlı subprocess taklidiyle test edilir; gerçek Ollama başarısı bu koşumdan çıkarılmaz.

   **GÖZLEM**
   M3 Eski sekiz özel çıktı, kaynak ve metadata regresyonu başarılı.

   **AÇIK** — yok

   **YAN-ETKİ**
   M4 Yeni mod için üç sözleşme testi eklendi; gerçek model veya uygulama verisine dokunulmadı.
