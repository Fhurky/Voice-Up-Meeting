# Koşum raporu — 2026-09-10 · Profil kotasının kaldırılmasından sonra tam kalite kapısı.

1. Sonuç: Tam profil kapısı geçti — birim/entegrasyon 136 başarılı / tarayıcı 0 başarılı / atlanan 0; iki ayrı ortam kapısı çalışamadan durdu; karar bekleyen: yok.
2. Koşulan: Yerel Windows üzerinden Git Bash ve çalışan Docker yığını; `kt-vibecoding-python-web-v2`, backend Python 3.13, PostgreSQL 17, React/Vite.

   | Komut | Gözlenen sonuç | Kanıt |
   | --- | --- | --- |
   | `scripts/quality-gate.sh all` | Çıkış 0; backend 97/97, frontend 39/39 | [Ham çıktı](quality-gate-all.txt) |
   | Aynı kapının statik/sözleşme adımları | Bağımlılık kabulü, ayar eşleşmesi, lint/format/tip, migrasyon, OpenAPI, frontend tipleri, yönetişim ve chart başarılı | Aynı ham çıktı |
   | `scripts/security-gate.sh` | Çıkış 2; `required offline security tool is unavailable: gitleaks` | [Ham çıktı](security-gate.txt) |
   | `scripts/e2e.sh speaker-identity` | Çıkış 2; `KT_SCAFFOLD_OFFLINE_BUNDLE must point to an admitted, platform-matched bundle` | [Ham çıktı](e2e.txt) |
   | Son belge/kaynak incelemesi | 42 kaynak hashı, 18 ajan hashı yeniden eşleşti; 41 kanıt dosyasında özel fikstür değeri/anahtar örüntüsü eşleşmesi 0, bozuk yerel bağlantı 0; `git diff --check` çıkış 0 | [Özet](handoff-check.json), [diff çıktısı](diff-check.txt), [kaynaklar](source-manifest.json) |

   Komutlar `C:\Program Files\Git\bin\bash.exe` ile çağrıldı;
   `MSYS2_ARG_CONV_EXCL=/tmp;/workspace`, `outputs/local-tools` PATH başında ve
   `MSYS_NO_PATHCONV` tanımsızdı. Kapının özgün `KT_GATE_*` kayıtları korundu.

3. Maddeler:

   **KUSUR** — yok
   **TUZAK**
   M1 Tam kapı ayrı değerlendirme betiklerinin testlerini içermez; [234 başarılı/1 platform atlamalı Python 3.13 koşumu](evaluator-run-report.md) ayrıca kayıtlıdır, Windows tekrarları toplamı büyütmez.
   **GÖZLEM**
   M2 Kapı yalnız kendine özel `_test` veritabanına iki migrasyon uyguladı; şema farkı bulmadı ve veritabanını düşürdü. Uygulama veritabanına migrasyon uygulanmadı.
   **AÇIK**
   M3 Güvenlik taraması ve kabul edilmiş paketle kalıcı Playwright senaryosu çalışmadı; bunlara geçiş sonucu verilmez. [Gerçek tarayıcı geçişi](live-report.md) ayrı L2 davranış kanıtıdır.
   Son belge taraması yalnız bilinen özel fikstür değerlerini ve token/özel anahtar örüntülerini denetledi; eksik güvenlik tarayıcılarının yerine geçmez.
   **YAN-ETKİ**
   M4 Kapı geçici veritabanı ve frontend derleme çıktısı üretti; model, bağımlılık, migrasyon ve ayar otoriteleri bu değişiklik için değiştirilmedi.
