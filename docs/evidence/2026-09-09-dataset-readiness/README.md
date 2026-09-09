# Koşum raporu — 2026-09-09 · uzun kayıt kararı ve veri hazırlık kiti entegrasyonu

1. Sonuç: Uygulama kalite kapısı geçti; boş veri kiti beklenen biçimde hazır sayılmadı — birim 65 başarılı / PostgreSQL 15 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Kapsam | Ortam ve kanıt | Gözlenen sonuç |
   | --- | --- | --- |
   | Tam uygulama kapısı | `kt-vibecoding-python-web-v2`; Windows/Git Bash → kilitli Linux Python 3.13 ve Node 22 konteynerleri, PostgreSQL 17/pgvector; `scripts/quality-gate.sh all` | 59 backend (44 birim + 15 PostgreSQL), 21 frontend; 0 hata, 0 atlanan. [Ham çıktı](application-quality-gate.txt), [pytest XML](application-backend.xml), [Vitest JSON](application-frontend.json). |
   | Diğer uygulama adımları | Aynı kapı | Config/bağımlılık kabulü, biçim/lint/tip, migrasyon/şema, OpenAPI/istemci türleri, build, governance ve chart 46 kaynak × 2 fixture geçti. |
   | Hazırlanmış yerel kit | Python 3.13; `validate-speaker-dataset.py --manifest data/speaker-pilot/dataset.json --audio-root data/speaker-pilot --output outputs/speaker-dataset-readiness.json` | Beklenen çıkış 1 / `not_ready`; 32 eksik dosya + 32 doğrulanmamış insan beyanı, 0 incelenmiş dosya. Her iki aşama false. [Kişisel veri içermeyen özet](prepared-kit-check.json). |
   | Doküman bağlantıları | Sekiz değişen belge/PRD/README için yerel Markdown hedefleri ve UTF-8 kontrolü | Eksik hedef 0; kullanıcı veri klasörü ve 32 satırlı manifest var, ses dosyası 0. |
   | Doğrulayıcı regresyonları | Ayrı, salt okunur veri hazırlık aracı | Dar kırmızı/yeşil koşumlar, kök referans testleri ve bağımsız inceleme [kit raporunda](dataset-kit-run-report.md). Uygulama sayılarına eklenmedi. |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 İlk kapı başlatıcısındaki `MSYS_NO_PATHCONV=1`, Windows Python için Git Bash yol dönüşümünü engelledi; başlatıcıdan kaldırılarak kapı çalıştırıldı. [İlk hata](application-quality-gate-launch-failure.txt) korundu; depo betiği değiştirilmedi.

   M2 Başarılı kapı exit 0 verdikten sonra dış başlatıcının son logu ekrana basması CP1254 karakter hatası verdi; ham UTF-8 log, 59/21 sonuç dosyaları ve test veritabanı temizliği ayrıca doğrulandı. Bu konsol hatası kapı sonucunu değiştirmedi.

   **GÖZLEM**

   M3 Seçilen sıra gerçek kişi doğruluğu → uzun kayıt analizi → canlı analizdir. [Mimari karar](../../LONG_RECORDING_STRATEGY.md), [veri rehberi](../../DATA_COLLECTION.md) ve 002/003 Draft gereksinimleri yazıldı; uzun dosya/canlı özellik uygulanmış sayılmadı.

   M4 Veri hazırlık kontrolünün `ready` sonucu yalnız dosya ve beyan kontrolleridir; konuşmacı saflığı, farklı oturum gerçeği ve tanıma doğruluğu anlamına gelmez. Model çalıştırılmadı; yeni doğruluk veya GPU hız skoru üretilmedi.

   **AÇIK**

   M5 T09 için gerçek ayrı oturum kayıtları yok; toplu uygulama doğruluk koşucusu ve temsilî seslerle model ölçümü tamamlanmadı. 5/10/20/50 kişi başarısı, uzun toplantı belleği ve canlı gecikme ölçülmedi.

   M6 Bu koşum yeni tarayıcı/GPU senaryosu veya dağıtım çalıştırmadı. Önceki kabul kanıtındaki eksik onaylı güvenlik tarayıcı ortamı ve kalıcı Playwright paketi devam ediyor; [önceki pilot kanıtı](../2026-09-08-local-speaker-pilot/README.md).

   **YAN-ETKİ**

   M7 Yeni doğrulayıcı/test/şablon, plan/PRD/rehber ve kanıt dosyaları eklendi; Git dışındaki `data/speaker-pilot` klasörü boş ses dizinleriyle hazırlandı. Uygulama kapısı yalnız kendisinin oluşturduğu geçici `_test` veritabanını temizledi; teknik profil ve kaynak sesler değiştirilmedi.
