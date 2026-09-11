# Koşum raporu — 2026-09-11 · Kök araç paketindeki sürüm ve kabuk hataları ayrıştırıldı.

1. Sonuç: İlk tam kök koşumu ve yerel kabuk tekrarı kusurları ortaya çıkardı — birim 975 başarılı / tarayıcı 0 başarılı / atlanan 15; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut | Gözlenen sonuç |
   |---|---|
   | Dış Git Bash, Windows Python 3.12, `.venv/Scripts/python.exe -m pytest tests -q --tb=short --junitxml=...` | 1.070 toplam: 975 başarılı, 80 başarısız, 15 atlanan; 290,462 saniye |
   | Yerel Windows PowerShell, aynı Python ve mevcut Helm dizini PATH'e ekli; `pytest tests/test_spark_startup.py tests/test_spark_tunnel.py tests/test_local_configuration.py` | 108 toplam: 98 başarılı, 10 başarısız, 0 atlanan; 99,126 saniye |
   | Hazırlayıcının eksik API regresyonu ve iki Python sürümü | [Ayrı arşiv raporunda](archive-compatibility-report.md) 6 RED, Python 3.12 ve 3.13'te aynı 40 GREEN |

3. Maddeler:

   **KUSUR**

   M1 Arşiv hazırlayıcıdaki Python 3.13'e özgü `ntpath.isreserved`, beyan edilmiş 3.12 ortamında yedi mevcut testi bozuyordu; API uyumlu geri dönüş ve iç cihaz adı regresyonları eklendi.

   M2 Hazırlanmış Spark runtime yardımcısının sabit Nginx kaynak özeti kabul edilmiş toplantı yollarından sonra eskimişti; 36 test hatası gerçek koruma uyuşmazlığıdır, kabuk hatası değildir. Ayrı sahip dar düzeltme/kanıtını kaydeder.

   M3 Başlatıcı test yardımcısı makinede bulunmayan `pwsh` motorunu varsayıyordu; yerel PowerShell tekrarındaki on hata alt süreç `executable=None` sonucudur. Üretim başlatıcısı bu hatanın kaynağı değildir.

   **TUZAK**

   M4 Dış Git Bash'teki 27 tünel hatası yerel PowerShell tekrarında oluşmadı; bütün kök paket mevcut Helm PATH'i eklenmiş yerel PowerShell'de yeniden çalıştırılmalıdır. Kabuklar eşdeğer çalışma ortamı varsayılamaz.

   **GÖZLEM**

   M5 İlk [ham çıktı](../../../outputs/2026-09-11-meeting-root-tests-093416/root-tests-latest.txt) ve [XML](../../../outputs/2026-09-11-meeting-root-tests-093416/root-tests.xml), yerel tekrarın [çıktısı](../../../outputs/2026-09-11-meeting-native-tests-094252/native-tests-latest.txt) ve [XML](../../../outputs/2026-09-11-meeting-native-tests-094252/native-tests.xml) korunur.

   **AÇIK**

   M6 Bu tarihsel teşhis koşumu kök paketin geçtiği anlamına gelmez; on test yardımcısı hatası ve incelenmiş Spark özet düzeltmesinden sonra tam yerel tekrar gerekir. Atlanan 15 test başarılı sayılmadı.

   **YAN-ETKİ**

   M7 Arşiv düzeltmesi ayrı kayıtlıdır; teşhis koşumları yeni sürüm kurmadı, ana uygulamayı veya gerçek Spark cihazını yeniden başlatmadı. Geçici test fixture'ları ve korunmuş çıktı dizinleri oluşturuldu.
