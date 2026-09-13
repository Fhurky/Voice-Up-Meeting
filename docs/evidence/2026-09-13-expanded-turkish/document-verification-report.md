# Koşum raporu — 2026-09-13 · Son belgeler ve sabit çıkarım kaynaklarının denetimi

1. Sonuç: 27 belgede 171 yerel bağlantı, 17 sabit rapor yapısı ve 8 kaynak hash'i doğrulandı; başarısız kontrol yok — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel Windows/Python üzerinde yeni kanıt klasöründeki mevcut Markdown dosyaları, 010 PRD/plan/görevleri, README, günlük, araç/veri rehberleri, araştırmalar ve roadmap salt okunur denetlendi. Sabit profil `kt-vibecoding-python-web-v2`; yeni model veya test paketi çalıştırılmadı.

   | Kontrol | Gözlenen sonuç |
   | --- | --- |
   | UTF-8 belge ve yerel dosya bağlantıları | 27 belge okunabildi; 171 hedef mevcut, eksik hedef 0 |
   | Sabit koşum raporu düzeni | 17 raporda 1–3 bölümleri, beş grup sırası ve kesintisiz M numaraları doğrulandı |
   | Çıkarım/test kaynakları | `runtime.json` içindeki 8 dosyanın SHA-256 değeri aynı; tamamlanmış deneylerden sonra kod/model manifesti değişmedi |
   | `git diff --check` | Çıkış 0; iki mevcut dosyada CRLF/LF uyarısı, boşluk hatası yok |

   [Makine kanıtı](document-verification.json) denetlenen belge hash'lerini ve kapsamı içerir.
   Bu rapor ile kanıt JSON'u denetimden sonra oluşturuldu; 27 belge sayısına eklenmedi.
   Model/otomatik test sonuçları [nihai raporda](README.md), tam profil ve dar paket sonuçları [önceki doğrulamada](post-performance-verification-report.md) kaydedilmiştir.

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Denetim yerel dosya hedeflerini kapsar; uzak URL ve Markdown başlık çapaları yeniden kontrol edilmedi. `outputs/` altındaki özel kanıt bağlantıları yalnız bu makinede mevcuttur, ham veriler yayımlanmaz.

   **GÖZLEM**

   M2 Sekiz çıkarım/model/ölçüm kaynağı kayıtlı hash'lerle aynı kaldı. Rapor şekli denetimi ve yerel bağlantı sayısı bağımsız ses veya başarılı birim testi sayısı değildir.

   M3 Git'in CRLF/LF uyarıları 002 PRD ve roadmap içindi; satır sonlarını değiştiren bir komut veya ilgisiz kullanıcı düzeltmesi uygulanmadı.

   **AÇIK**

   M4 Bu denetim güvenlik taraması değildir; eksik `gitleaks`, temsilî 50 Türkçe kişi, insan referansı ve cihaz kabulü sınırları nihai raporda açık kalır.

   **YAN-ETKİ**

   M5 Yalnız bu rapor ve `document-verification.json` eklendi. Veri, model, günlük ve kod değiştirilmedi; commit/push yapılmadı.
