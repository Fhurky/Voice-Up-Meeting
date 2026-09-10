# Koşum raporu — 2026-09-10 · Gereksinim güncellemesinden sonra mevcut pilotun kalite kapısı.

1. Sonuç: Mevcut uygulamanın tam kalite kapısı geçti; yeni toplantı özelliği test edilmedi — birim/entegrasyon 136 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel Windows/Git Bash/Docker, `kt-vibecoding-python-web-v2`.

   | Kontrol | Gözlenen sonuç |
   | --- | --- |
   | `scripts/quality-gate.sh all` | Çıkış 0; backend 97, frontend 39 başarılı. [Ham çıktı](quality-gate-all.txt). |
   | Tam kapının diğer adımları | Ayar/bağımlılık kabulü, gerçek geçici PostgreSQL migrasyonu ve drift, statik/tip, OpenAPI ve istemci türleri, yönetişim ve chart başarılı. |
   | Sekiz değişen kaynak belge | Yerel bağlantı hatası 0, `git diff --check -- <eight document paths>` çıkış 0; [dosyalar ve hashlar](source-manifest.json). |

   Komut `C:\Program Files\Git\bin\bash.exe` ile çalıştı;
   `MSYS2_ARG_CONV_EXCL=/tmp;/workspace`, `outputs/local-tools` PATH başında ve
   `MSYS_NO_PATHCONV` tanımsızdı. Özgün `KT_GATE_*` kayıtları korunur.

3. Maddeler:

   **KUSUR** — yok
   **TUZAK**
   M1 136 test mevcut tek konuşmacılı pilot içindir; yeni diarization, transkript, mikrofon veya otomatik hafıza özelliğinin kanıtı değildir.
   **GÖZLEM**
   M2 Bağımsız belge incelemesinde canlı transkriptin yanlışlıkla 003'e atfedilmesi ve zorunlu örnek ilişkisi ifadesi düzeltildi; 003 hâlâ yalnız canlı kimlik taslağıdır.
   **AÇIK**
   M3 Yeni sağlayıcı erişimi/ARM64 uyumu, uygulanacak T02–T11, gerçek çok kişi/mikrofon/Türkçe ve kaynak testleri [keşif raporunda](README.md) açıktır. Yeni kod olmadığı için güvenlik ve tarayıcı senaryoları bu belge değişikliği için yeniden çalıştırılmadı.
   **YAN-ETKİ**
   M4 Kapı kendine özel `_test` veritabanını oluşturdu, mevcut migrasyonları uyguladı ve düşürdü; frontend derlemesini yineledi. Uygulama veritabanına veya yeni model paketlerine işlem yapılmadı.
