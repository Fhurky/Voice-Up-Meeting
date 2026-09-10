# Koşum raporu — 2026-09-10 · Tam profil kapısı ve ortam giriş noktaları.

1. Sonuç: Tam kalite kapısı geçti; ayrı güvenlik ve kalıcı tarayıcı giriş noktaları ortam eksikliğiyle durdu — birim/entegrasyon 133 başarılı / tarayıcı 0 başarılı / atlanan 2 ortam kapısı; karar bekleyen: yok.
2. Koşulan: Yerel Windows Git Bash, Docker Compose; sabit `kt-vibecoding-python-web-v2`. Süre 63,437 saniye.

   | Komut | Gözlenen sonuç |
   | --- | --- |
   | `scripts/quality-gate.sh all` | Çıkış 0; backend 96, frontend 37 başarılı, testlerde atlanan 0. [Ham çıktı](quality-gate-all.txt). |
   | Tam kapının diğer adımları | Bağımlılık kabulü, config, geçici PostgreSQL migrasyonu/doğrulaması, format/lint/türler, OpenAPI/tip farkı, 93 yönetişim çıktısı ve iki ortamda 46 chart kaynağı geçti. |
   | `scripts/security-gate.sh` | Çıkış 2: `required offline security tool is unavailable: gitleaks`. [Çıktı](security-gate.txt). |
   | `scripts/e2e.sh speaker-identity` | Çıkış 2: `KT_SCAFFOLD_OFFLINE_BUNDLE must point to an admitted, platform-matched bundle`. [Çıktı](browser-entrypoint.txt). |
   | `git diff --check` | Çıkış 0; mevcut CRLF/LF uyarıları hata değildir. |

3. Maddeler:

   **KUSUR** — yok
   **TUZAK**
   M1 Windows'ta Git Bash kullanıldı; `MSYS2_ARG_CONV_EXCL=/tmp;/workspace`, yerel Helm yolu ve normal Windows Python yol dönüşümü korundu.
   **GÖZLEM**
   M2 Tam kapı kendine ait benzersiz `_test` veritabanını oluşturdu, migrasyon uyguladı ve başarıda düşürdü; uygulama veritabanına migrasyon uygulamadı.
   M3 `KT_GATE_SCOPE`, `KT_GATE_STEP`, `KT_GATE_TESTS` kayıtları değiştirilmeden ham çıktıda korunur; odaklı test tekrarları 133 sayısına eklenmez.
   **AÇIK**
   M4 Gitleaks bulunmadığından güvenlik taraması ve sonraki güvenlik denetimleri çalışmadı; güvenlik geçişi iddia edilmez.
   M5 Kabul edilmiş Playwright paketi yok; kaydedilmiş tarayıcı takımı çalışmadı. Ayrı [canlı CUA kanıtı](live-browser-report.md) bu koşumun yerine geçirilmez.
   **YAN-ETKİ**
   M6 Geçici test veritabanı ve frontend üretim çıktısı kapı tarafından üretildi; veritabanı düşürüldü, çıktı uygulamanın mevcut derleme dizinindedir.
