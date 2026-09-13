# Koşum raporu — 2026-09-13 · Kullanılabilirlik değişikliklerinin tam profil kapısı

1. Sonuç: Tam kalite kapısı geçti; bağımsız güvenlik kapısı eksik araç nedeniyle çalışamadı — birim 590 başarılı / PostgreSQL bütünleşme 255 başarılı / tarayıcı 0 başarılı / atlanan 1; karar bekleyen: yok.
2. Koşulan: Windows → Git Bash → Docker; profil `kt-vibecoding-python-web-v2`. `scripts/quality-gate.sh all` çıkış 0; `scripts/security-gate.sh` çıkış 2. [Gerçek kapı işaretleri, çıktı ve kaynak karmaları](quality-summary.json).

   | Denetim | Gözlenen sonuç |
   | --- | --- |
   | Yapılandırma ve bağımlılık kabulü | Geçti; 211 kabul edilmiş koordinat, mevcut sabit profil |
   | Yapılandırma yüzeyleri | Geçti; 80 kaynak dosyası ve 39 tipli ayar |
   | Geçici PostgreSQL / migration | Yalnız benzersiz `_test` veritabanı oluşturuldu, migration uygulandı ve sonunda kaldırıldı |
   | Arka uç statik kontrolleri | Ruff, Black, isort ve mypy geçti; 128 format dosyası, 80 tip denetimi modülü |
   | `pytest` | 687/687: JUnit sınıf yollarından 432 birim + 255 gerçek PostgreSQL bütünleşme; 0 atlama |
   | Migration validate/status/drift | Geçti; `755327e73d5c` head, yeni upgrade işlemi yok |
   | Çevrimdışı OpenAPI / üretilmiş frontend tipi | Wrapper ile üretildi; iki drift kontrolü geçti |
   | Ön yüz | ESLint, TypeScript ve Vite üretim derlemesi geçti; 25 dosyada 158/158 Vitest |
   | Yönetişim | 93 projeksiyon ve 4 etkinleştirilmemiş ajan projeksiyonu güncel |
   | Dağıtım çizelgeleri | 46 ve toplantı için 47 kaynak × 2 fixture overlay geçti |
   | Güvenlik kapısı | `required offline security tool is unavailable: gitleaks`; çıkış 2, tarama başarısı yok |

   Ham yerel çıktılar `outputs/2026-09-13-usability-improvement/quality-gate.txt`
   ve `security-gate.txt` altındadır. Ara dar koşumlardaki aynı testler 845'e
   yeniden eklenmez. Önceki deney/research test sayıları bu koşumun sayısı değildir.

3. Maddeler:

   **KUSUR**

   M1 Türkçe sınır tekrarları, eksik ses inceleme ve seçim/yaşam döngüsü regresyonları düzeltildi; [Türkçe](turkish-stitch-report.md), [arka uç](audio-preview-backend-report.md) ve [ön yüz](audio-review-frontend-report.md) kırmızı/yeşil kanıtları mevcut.

   **TUZAK**

   M2 Windows bağlı dosyalarının izinleri için kapının mevcut geçici-kopya yöntemi kullanıldı; uygulama veritabanına migration uygulanmadı. PowerShell, stderr bilgilendirme satırlarını `NativeCommandError` olarak biçimlendirdi; gerçek kapı çıkışı 0'dır.

   M3 Kanonik exporter operation ID alanlarını kaldırır; frontend sorgu tipi üretilmiş `paths` GET sözleşmesinden türetildi. Exporter ve üretilmiş çıktılar elle değiştirilmedi.

   **GÖZLEM**

   M4 Profil, şema, bağımlılık, model tarifi, karar eşikleri ve doğruluk metriği sürümleri değişmedi. Bu 845 test bir model doğruluk yüzdesi değildir.

   **AÇIK**

   M5 Güvenlik kapısı için onaylı çevrimdışı `gitleaks` ve diğer tarayıcı materyallerinin bulunduğu ortam gerekli; kalite kapısının geçmesi bağımsız güvenlik kabulü sayılmaz.

   M6 Gerçek tarayıcı ve ağ kanıtı [ayrı raporlarda](browser-review-report.md); 50 kişilik doğal Türkçe toplantı, fiziksel ses çıkışı, Apple/Spark ve kullanıcı L3 kabulü bu kapıda ölçülmedi.

   **YAN-ETKİ**

   M7 Yalnız yeni kalite veritabanı oluşturulup kaldırıldı; mevcut kullanıcı değişiklikleri korundu. OpenAPI/tipler üretildi; rapor ve yerel test çıktıları eklendi. Commit/push yapılmadı.
