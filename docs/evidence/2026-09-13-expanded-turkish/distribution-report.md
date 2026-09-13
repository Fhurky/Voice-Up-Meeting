# Koşum raporu — 2026-09-13 · Türkçe ASR hata dağılımı raporu

1. Sonuç: Toplam kelime hatası ve klip dağılımı bağımsız doğrulanıyor — birim 9 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows/Python 3.12, `tests/test_expanded_asr_report.py`: ilk 7 beklenen kırmızı/7 yeşil, inceleme sonrası tür doğrulamasında 1 kırmızı/1 mevcut geçiş ve son 9 yeşil; gerçek CLI/dosya, ağırlıklı toplama, yeniden hesaplanan metrik, tekrar kaynak, eksik durum, sınırlı metin ve çıktı koruması. İlk kırmızı (Git dışı yerel çıktı: `../../../outputs/2026-09-13-expanded-turkish/distribution-red.xml`), inceleme kırmızısı (Git dışı yerel çıktı: `../../../outputs/2026-09-13-expanded-turkish/distribution-hardening-red.xml`), son yeşil (Git dışı yerel çıktı: `../../../outputs/2026-09-13-expanded-turkish/distribution-hardening-green.xml`).
3. Maddeler:

   **KUSUR**

   M1 DÜZELTİLDİ: İç metrik alanı sözlük yerine liste olunca kontrolsüz hata oluşuyordu; açık tür doğrulaması eklendi. Bozuk aşırı metnin maliyeti skorlamadan önce 2.000 kelimeyle sınırlandı.

   **TUZAK**

   M2 Kelime hata oranı kelime sayısıyla ağırlıklıdır; klip oranlarının basit ortalaması değildir ve eklemeler nedeniyle %100'ü aşabilir.
   M3 %95 aralık 2.000 sabit tohumlu klip tekrar örneklemesine koşulludur; aynı kişi/oturum veya aynı cümle bağımlılığını gidermez, nüfus güven aralığı değildir.

   **GÖZLEM**

   M4 Özel metinlerden her klibin S/D/I ve kelime sayısı yeniden hesaplanır; rapor yalnız toplu sayılar, dağılımlar ve kanıt hashlerini içerir.

   **AÇIK**

   M5 Gerçek model dağılımları geniş koşumlar tamamlandıktan sonra ayrı toplu dosyalarda yayımlanacaktır.

   **YAN-ETKİ**

   M6 `scripts/report-expanded-turkish-asr.py` ve dokuz regresyon eklendi; bu testler gerçek günlük veya model çıktısını değiştirmedi.
