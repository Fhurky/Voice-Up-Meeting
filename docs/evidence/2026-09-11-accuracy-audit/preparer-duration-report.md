# Koşum raporu — 2026-09-11 · Veri hazırlayıcının tam cümle süre sözleşmesi

1. Sonuç: Geçerli uzun cümleler kabul edilen 60 saniye sınırına uygun işlendi — birim 20 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows/Python 3.12; `pytest tests/test_prepare_meeting_identity_evaluation.py` → ilk koşum 5 başarısız/15 başarılı, düzeltmeden sonra 20 başarılı. Ruff lint ve biçim denetimi geçti. Ham kanıt: `outputs/2026-09-11-accuracy-audit/preparer-duration-{red,green}.{xml,log}`.
3. Maddeler:
   **KUSUR**
   M1 Belgelenmeyen 40 saniyelik tek cümle sınırı, 45/60 saniyelik geçerli kaynakları reddediyordu; seçim ve gerçek WAV doğrulaması kabul edilen toplam sınırına bağlandı (DÜZELTİLDİ, hazırlayıcı ve 5 regresyon).
   **TUZAK**
   M2 60 saniyeyi aşan cümle, aynı kişinin sıradaki uygun cümlesine geçilerek deterministik atlanır; farklı kişi seçilmez, ses kesilmez.
   **GÖZLEM**
   M3 Mevcut 190 ses örneği ve 3 toplantı değişmedi; kaynak cümleleri 40 saniyeyi aşmıyordu. Bu kusur mevcut 50 kişilik model hatasının nedeni değildir.
   **AÇIK**
   M4 Bu dar koşum yeni model kalitesini veya bütün uygulama kapısını doğrulamaz.
   **YAN-ETKİ**
   M5 Hazırlayıcı ve testleri güncellendi; tarihsel manifestlerin hazırlayıcı hashleri yenilenmedi. Geçici test sesleri test ortamında üretildi.
