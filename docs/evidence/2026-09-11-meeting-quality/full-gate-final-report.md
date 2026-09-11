# Koşum raporu — 2026-09-11 · Yardımcı araç düzeltmeleri sonrası son tam profil kapısı geçti.

1. Sonuç: Son tam kapı başarılı, çıkış 0 — birim 567 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut | Gözlenen sonuç |
   |---|---|
   | Windows Git Bash → mevcut Linux servisleri, `scripts/quality-gate.sh all`, profil `kt-vibecoding-python-web-v2` | Yapılandırma, 211 koordinatlı bağımlılık kabulü, 77 kaynak/39 typed ayar eşlemesi başarılı |
   | Benzersiz geçici PostgreSQL 17 veritabanı | Altı migrasyon uygulandı; son başlık `755327e73d5c`; uygulama veritabanına migrasyon yapılmadı |
   | Python 3.13 arka uç Ruff/Black/isort/Mypy | Başarılı; 115 biçim dosyası değişmedi, 77 kaynakta tip hatası yok |
   | Gerçek PostgreSQL entegrasyonları açık arka uç paketi | 478 başarılı, 0 başarısız, 0 atlanan; 178,88 saniye |
   | Aynı test veritabanında migrasyon validate/status/drift ve çevrimdışı OpenAPI sözleşmesi | Başarılı; yeni upgrade işlemi veya sözleşme farkı yok |
   | React 19/Vite 8 ön yüz lint, tip kontrolü, üretim derlemesi, Vitest ve üretilmiş tip farkı | 20 dosyada 89 başarılı, 0 başarısız, 0 atlanan; sözleşme farkı yok |
   | Yönetişim ve deployment render | 93 yönetişim + 4 etkinleştirilmemiş projection güncel; pilot 46 × 2, toplantı 47 × 2 kaynak başarılı |
   | Kapı sonu temizliği | `database-test-drop` başarılı; benzersiz geçici veritabanı kaldırıldı |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Bu son koşum [önceki başarılı kapıdan](full-gate-report.md) sonra arşiv uyumu, PowerShell test yardımcısı ve incelenmiş Spark proxy özeti düzeltmelerini içerir. Eski başarısız/başarılı raporlar korunur.

   M2 567 sayısı yalnız uygulama kapısının arka uç ve ön yüz testleridir; [1.063 yerel kök testi ve ayrı 15 kapsam testi](root-tests-final-report.md), model/tarayıcı koşumları veya güvenlik taraması bu sayıya eklenmez.

   **GÖZLEM**

   M3 Son [ham kapı çıktısı](../../../outputs/2026-09-11-meeting-quality-final-095733/full-gate-latest.txt), [arka uç XML](../../../outputs/2026-09-11-meeting-quality-final-095733/backend-tests.xml) ve [ön yüz JSON](../../../outputs/2026-09-11-meeting-quality-final-095733/frontend-tests.json) korunur; sayılar gerçek `KT_GATE_TESTS` kayıtlarından alınmıştır.

   M4 Bu L1 otomatik kanıt yerel CLI çalıştırmasıdır; fixture render gerçek küme dağıtımı, test vektörleri model doğruluğu veya tarayıcı kapsamı olarak sayılmadı.

   **AÇIK**

   M5 Kabul edilmiş çevrimdışı güvenlik paketi eksiktir: [araç denetimi](security-toolchain-audit.md) ve önceki güvenlik kapısının `gitleaks` yokluğu/çıkış 2 kaydı geçerlidir. Bu son uygulama kapısı güvenlik geçişi değildir.

   M6 Gerçek lab/cluster dağıtım girdileri, native Spark toplantı modeli, 50 kişilik kalite ve sahip kabulü bu koşumla kanıtlanmaz; kendi açık kapsam ve ortam kayıtları korunur.

   **YAN-ETKİ**

   M7 Kapı yalnız kendi geçici veritabanını oluşturup kaldırdı; ana backend/worker/GPU yeniden başlatılmadı. XML/JSON mevcut `scripts/stack.sh cp` sarmalayıcısıyla yeni çıktı dizinine alındı; önceki kanıtların üzerine yazılmadı.
