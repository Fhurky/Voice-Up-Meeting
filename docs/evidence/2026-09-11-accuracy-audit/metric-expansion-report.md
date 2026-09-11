# Koşum raporu — 2026-09-11 · Unicode dönüşümü kaynak sınırı ve elli kişilik skorun korunması

1. Sonuç: Dönüşüm sonrası karakter sınırı düzeltildi ve gerçek toplantı skoru korundu — birim 33 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows/Python 3.12, `kt-vibecoding-python-web-v2` araştırma aracı; iki metrik test dosyası → 33 test, gerçek dosya komutuyla 5.724 referans kelimeli A kaydının tekrar hesaplanması → 1 eşitlik denetimi. Ham kanıt: `outputs/2026-09-11-accuracy-audit/metric-expansion-{red,green}.xml` ve `capacity50/metric-expansion-parity.json`.
3. Maddeler:
   **KUSUR**
   M1 Tek bir Unicode karakterinin genişlemesi ham sınırı aşabiliyordu; 3 başarısız regresyondan sonra tek metin ve her taraftaki toplam dönüştürülmüş metin sınırlanıyor (DÜZELTİLDİ, `meeting_metrics.py` / `test_meeting_metrics.py`).
   **TUZAK**
   M2 İlk özel tekrar betiği Windows varsayılan kodlamasıyla UTF-8 metni bozdu ve 1 ek kelime hatası buldu; açık UTF-8 ile tekrar aynı 803/886 hata çıktı. Başarısız özel çıktı korunuyor.
   **GÖZLEM**
   M3 Normalizasyon kuralı değişmedi; standart ve belirsiz kişiyi ayrı cezalandıran skorların bütün alanları önceki gerçek A sonucu ile eşit. Bu eşitlik konuşmacı doğruluğu artışı değildir.
   **AÇIK**
   M4 Bu dar koşum son kaynak sürümünün tam profil kapısı veya gerçek model güvenlik düzeltmesinin kanıtı değildir.
   **YAN-ETKİ**
   M5 Ölçümün kaynak sınırı, üç regresyon ve kullanım belgesi güncellendi; özel metin girdileri yalnız ignore edilen kanıt dizinine yazıldı. Uygulama verisi ve model eşikleri değişmedi.
