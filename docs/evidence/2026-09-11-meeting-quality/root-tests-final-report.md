# Koşum raporu — 2026-09-11 · Kök araç paketinin bütün durumları uygun gerçek ortamlarda geçti.

1. Sonuç: Yerel tam paket ve ayrı koşullu kapsam başarılı — birim 1.078 başarılı / tarayıcı 0 başarılı / atlanan 15 yerel, ek koşumlarda 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut | Gözlenen sonuç |
   |---|---|
   | Yerel Windows PowerShell, Python 3.12, mevcut `C:/Users/furko/bin` PATH'te; `.venv/Scripts/python.exe -m pytest tests -q --tb=short --junitxml=...` | 1.078 toplam: 1.063 başarılı, 0 başarısız, 15 atlanan; 314,977 saniye |
   | Aynı son kaynakta `RUN_DOCKER_TRANSPORT=1`, ayrı görev sahibinin gerçek Docker koşumları | 9 + 4 aktarım testi başarılı, 0 atlanan; 34,891 ve 20,346 saniye |
   | Ayrı görev sahibinin gerçek Linux dosya sistemi koşumu | Windows'ta atlanan 2 sembolik bağlantı durumu başarılı, 0 atlanan; 0,712 saniye |
   | [Arşiv uyumu](archive-compatibility-report.md), [PowerShell yardımcısı](native-startup-helper-report.md), [Spark kaynak özeti](../2026-09-10-meeting-delivery/spark-reviewed-template-report.md) | Ayrı RED/GREEN ve dar statik kanıtlar başarılı; tümü tam yerel tekrarda mevcut |

3. Maddeler:

   **KUSUR**

   M1 İlk tam paketteki gerçek Python sürüm ve Spark kaynak özeti kusurları düzeltildi; test yardımcısı kurulu PowerShell motorunu seçiyor. Önceki 80 başarısızlık [teşhis raporunda](root-tests-investigation-report.md) korunur; son pakette başarısızlık yoktur.

   **TUZAK**

   M2 Tek yerel komut hâlâ 15 skip üretir: 13 aktarım testi açık bayrak ister, iki bağlantı testi Windows hesabının sahip olmadığı yetkiyi gerektirir. Bu kayıt değiştirilmedi; aynı durumların ek koşumlarda geçmesi ayrı sayılır.

   M3 Dış Git Bash'teki ilk çalıştırma yerel PowerShell ile eşdeğer değildi. Son tam koşum Windows PowerShell kullandı ve yalnız mevcut Helm dizinini kendi süreç PATH'ine ekledi; yeni araç veya sürüm kurulmadı.

   **GÖZLEM**

   M4 Tam yerel [ham çıktı](../../../outputs/2026-09-11-meeting-root-native-095205/root-tests-latest.txt) ve [XML](../../../outputs/2026-09-11-meeting-root-native-095205/root-tests.xml) korunur; 1.078 başarılı birleşik sayı 1.063 yerel + 15 ayrı kapsamdan oluşur.

   M5 Ayrı platform koşumlarının gerçek yöntem ve sınırları [kapanış raporunda](../2026-09-10-meeting-delivery/remaining-platform-coverage-report.md) bulunur; [9 aktarım](../../../outputs/2026-09-10-meeting-delivery/linux-skip-coverage/transport-nine.xml), [4 aktarım](../../../outputs/2026-09-10-meeting-delivery/linux-skip-coverage/transport-four.xml) ve [2 bağlantı](../../../outputs/2026-09-10-meeting-delivery/linux-skip-coverage/linux-symlink.xml) XML'leri incelendi.

   **AÇIK**

   M6 Bu paket model doğruluğu, gerçek Spark toplantısı, Kubernetes ortamı, 50 kişilik kabul veya eksik çevrimdışı güvenlik araçları için kanıt oluşturmaz. Yardımcı düzeltmelerinden sonraki tam uygulama kapısı ayrı raporlanır.

   **YAN-ETKİ**

   M7 Düzeltmeler kabul edilmiş hazırlayıcı, test yardımcısı ve sabit incelenmiş proxy özeti sınırında kaldı; ana uygulama veya GPU servisi yeniden başlatılmadı. Ek Docker koşumları kendi geçici fixture'larını temizledi.
