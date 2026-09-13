# Koşum raporu — 2026-09-13 · Metin inceleme deney denetleyicisinin kırmızı regresyonu

1. Sonuç: Kanıt hesaplama ve kaynak bağlama açıkları yeniden üretildi — birim 6 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows Python 3.12 araştırma ortamı, `.venv/Scripts/python.exe -m pytest tests/test_transcript_review_evaluation.py tests/test_transcript_review_controller.py`; 18 test, 12 başarısız, çıkış 1. Model veya çalışan uygulama çağrısı yok; subprocess sınırı imza kısıtlı test doubles ile temsil edildi.
3. Maddeler:

   **KUSUR**
   M1 Çift gözlem sayısında medyan yerine üst orta değer hesaplanıyor.
   M2 Öneri metni değişikliklerden yeniden kurulmuyor; örtüşen ve bilinmeyen alanlı değişiklikler kabul ediliyor.
   M3 Özel çıktı dizini `outputs/` ile sınırlandırılmıyor; kaynak/metadata ve worker kimlik uyuşmazlıkları engellenmiyor.
   M4 Koşum sırasında değiştirilen metadata dosyası bitişte yeniden okunup gerçek deneyi başka bir kimliğe bağlayabiliyor veya kaydı engelliyor.

   **TUZAK**
   M5 Önceki model koşumları bu testte yeniden çalıştırılmadı; eski günlük blokları değişmedi.

   **GÖZLEM**
   M6 Başarısız istek paydası, sözcük normalizasyonu ve Unicode için altı kontrol geçti.

   **AÇIK**
   M7 Düzeltmelerden sonra gerçek özel sonuçlardan yeniden hesaplama ve append-only günlük sürümü ortak teslimde kaydedilecek.

   **YAN-ETKİ**
   M8 İki test dosyası güncellendi/eklendi; yalnız geçici pytest dosyaları ve bu rapor üretildi.
