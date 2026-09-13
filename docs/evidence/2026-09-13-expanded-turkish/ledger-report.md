# Koşum raporu — 2026-09-13 · Geniş deneylerin günlük kapsamı

1. Sonuç: Yeni kaynak ve pencere kapsamı günlükte doğrulanıyor — birim 44 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows/Python 3.12, `kt-vibecoding-python-web-v2`; `tests/test_experiment_ledger.py`: ilk dar kırmızı koşumda 9 beklenen başarısızlık, uygulama sonrası tüm 44 test başarılı; iki etkilenen dosya Ruff ile biçimlendirildi. Kırmızı (Git dışı yerel çıktı: `../../../outputs/2026-09-13-expanded-turkish/ledger-red.xml`), yeşil (Git dışı yerel çıktı: `../../../outputs/2026-09-13-expanded-turkish/ledger-green.xml`).
3. Maddeler:

   **KUSUR**

   M1 DÜZELTİLDİ: Tamamlanmamış ASR deneyleri gözlenen/planlı klip sayısını göstermiyordu; alan doğrulaması ve görünür kapsam eklendi, başarı skoru üretilmiyor.
   M2 DÜZELTİLDİ: Yeni Türkçe ASR kaynak protokolleri ve toplantı zaman penceresi günlükte kayboluyordu; açık izin listesi ve süre/protokol tutarlılık kontrolleri eklendi.

   **TUZAK**

   M3 Yeni görüşme pencereleri aynı altı kişi ve oturuma aittir; bu uyarı pencere kapsamıyla birlikte görünür. Fazla gözlenen ses veya değiştirilmiş pencere reddedilir.

   **GÖZLEM**

   M4 Geçmiş tamamlanmış MediaSpeech v1 kanonik sonuç biçimi ve 13 geçmiş deney aktarımının tekrar güvenliği korundu.

   **AÇIK**

   M5 Bu dar koşum gerçek model veya HTTP testi değildir; geniş deneylerin kanıtı ayrı kaydedilecektir.

   **YAN-ETKİ**

   M6 `scripts/experiment_ledger.py` ve ilgili testlere dokuz regresyon eklendi; bu koşum kök `results.md` dosyasını değiştirmedi.
