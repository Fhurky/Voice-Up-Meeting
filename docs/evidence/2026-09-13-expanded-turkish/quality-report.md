# Koşum raporu — 2026-09-13 · Tam profil kapısı ve güvenlik aracı kontrolü

1. Sonuç: Tam profil kapısı geçti; güvenlik kapısı eksik araç nedeniyle tamamlanmadı — birim 738 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows/Git Bash üzerinden yerel Docker Linux/Python 3.13, PostgreSQL 17 ve React/Vite ortamı.

   | Komut | Sonuç | Kanıt |
   | --- | --- | --- |
   | `scripts/quality-gate.sh all` | Çıkış 0; 605 backend + 133 frontend test başarılı | Gerçek kapı günlüğü (Git dışı yerel çıktı: `../../../outputs/2026-09-13-expanded-turkish/quality-gate.txt`) |
   | `scripts/security-gate.sh` | Çıkış 2; `required offline security tool is unavailable: gitleaks` | Gerçek hata günlüğü (Git dışı yerel çıktı: `../../../outputs/2026-09-13-expanded-turkish/security-gate.txt`) |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Windows PowerShell, Alembic'in stderr bilgi satırlarını `NativeCommandError` başlığıyla gösterebilir; gerçek tam kapı çıkışı 0 ve bütün `KT_GATE_STEP` kayıtları başarılıdır.

   **GÖZLEM**

   M2 Bağımlılık kabulü, yapılandırma, migration, formatter/lint/type, canlı PostgreSQL entegrasyonu, şema drift, OpenAPI, frontend build/tip sözleşmesi, yönetişim ve chart kontrolleri geçti.
   M3 Benzersiz `_test` veritabanı oluşturulup migration/test yapıldı ve sonunda düşürüldü; uygulama veritabanına migration uygulanmadı.

   **AÇIK**

   M4 Gitleaks yok; Semgrep/Trivy aşamalarına ulaşılamadı. Güvenlik taramasına geçiş veya temiz güvenlik sonucu iddia edilmez.
   M5 Yeni değerlendirme araçlarının dar Python testleri ve gerçek model/HTTP skorları ayrı koşum kanıtlarıdır; tam profil kapısı bunların yerine geçmez.

   **YAN-ETKİ**

   M6 Yalnız kapıya ait geçici test veritabanı yaşam döngüsü ve yerel günlükler oluştu; mevcut uygulama kayıtları korunmuştur.
