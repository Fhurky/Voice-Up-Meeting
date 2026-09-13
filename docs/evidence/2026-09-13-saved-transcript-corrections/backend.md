# Koşum raporu — 2026-09-13 · Model önerilerinin kaynağa bağlı onay ve saklama sınırları

1. Sonuç: Son odaklı koşumda 59 gerçek PostgreSQL/HTTP testi ve 52 birim testi, ardından dört statik kontrol başarılı — birim 52 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows çalışma alanından mevcut `scripts/stack.sh` ile Python 3.13/FastAPI konteyneri; profil `kt-vibecoding-python-web-v2`, PostgreSQL 17 ve SQLAlchemy/Alembic.

   | Koşum | Komut / kapsam | Gözlenen sonuç |
   | --- | --- | --- |
   | Domain başlangıcı | `pytest -q tests/unit/test_transcript_suggestions.py` | Eksik domain modülü nedeniyle toplama hatası; ardından 16 başarılı |
   | İmzalı kanıt başlangıcı | `pytest -q tests/unit/test_correction_receipts.py` | Eksik imza modülü nedeniyle toplama hatası; ardından 7 başarılı |
   | API başlangıcı | `tests/integration/test_transcript_revisions.py` | Eksik bağımlılık sağlayıcısı nedeniyle toplama hatası; başarılı sayılmadı |
   | İlk PostgreSQL regresyonu | Yeni sürüm API dosyasındaki ilk dört test | 3 başarılı, 1 başarısız; ters sıradaki model önerileri kayıtta `[21, 5]` konum sırasıyla döndü |
   | Genişletilmiş PostgreSQL koşumu | Aşağıdaki altı dosya | 106 başarılı, 3 başarısız; 29,41 saniye; test veritabanı düşürüldü |
   | Son PostgreSQL/birim koşumu | Aşağıdaki altı dosya, `RUN_POSTGRES_INTEGRATION=1` | 111 başarılı, 0 atlanan; 27,88 saniye; `DROP DATABASE` başarılı |
   | Son suite dağılımı | `tests/integration/test_transcript_revisions.py` / `test_transcript_correction.py` / `test_meeting_cleanup.py` | Sırasıyla 32 / 20 / 7 başarılı |
   | Son suite dağılımı | `tests/unit/test_transcript_suggestions.py` / `test_correction_receipts.py` / `test_transcript_correction.py` | Sırasıyla 16 / 7 / 29 başarılı |
   | Migration üretimi | `scripts/db.sh generate meeting_transcript_revisions` | `8283cb0d9e4b` üretildi; SQL sırası ve geri alma gövdesi incelendi |
   | Yerel migration | `scripts/db.sh apply`, `scripts/db.sh validate`, `scripts/db.sh status` | Yerel uygulama veritabanında üçü başarılı; head `8283cb0d9e4b`, yeni yükseltme işlemi bulunmadı |
   | Sözleşme üretimi | `scripts/export-openapi.sh`, `scripts/generate-types.sh` | İkisi başarılı; 013 DTO ve işlem kimlikleri üretildi |
   | Statik kontrol ilk denemeleri | Tam `app`/`tests` kopyasında Ruff, Black, isort, mypy | Önce kullanılmayan eski import, sonra aynı dosyanın import sırası bulundu; bu iki deneme başarılı sayılmadı |
   | Son statik kontrol | `ruff check app tests`, `black --check app tests`, `isort --check-only app tests`, `mypy app` | Dördü başarılı; 149 Python dosyası biçimi, 93 uygulama dosyası tipi |

   Birleşik komut: `pytest -q tests/integration/test_transcript_revisions.py tests/integration/test_transcript_correction.py tests/integration/test_meeting_cleanup.py tests/unit/test_transcript_suggestions.py tests/unit/test_correction_receipts.py tests/unit/test_transcript_correction.py`.

   Her PostgreSQL test koşumu `voiceup_revisions_<benzersiz>_test` adlı kendi veritabanını oluşturdu, `scripts/db.sh apply` ile migrate etti ve `finally` içinde yalnız bu veritabanını düşürdü. Yerel uygulama migration'ı ayrı, açıkça yetkilendirilmiş bir işlemdi; testler uygulama verisini kullanmadı. Statik kontroller mevcut kapı yöntemiyle `/tmp/voiceup-review-static.*` kopyasında çalıştı; Windows kaynak dosya kipleri değiştirilmedi.

3. Maddeler:

   **KUSUR**

   M1 Ters model önerisi sırası, kaydedilmiş metnin yeniden kurulmasını bozuyordu; düzenlemeler imzadan ve saklamadan önce kaynak konumuna sıralandı, gerçek PostgreSQL kaydet/yeniden oku testiyle düzeltildi.

   M2 Tek başına Unicode surrogate içeren model önerisi 500 oluşturuyordu; yanıtın metin gösterimi kaçışlı ve sınırlı hale getirildi, eşlenemez öneri görünür kaldı ve kaydetme verilmedi; tek/64 karakter ve taşan ham yanıt testleri başarılı.

   M3 İki retention testi profil okuma izni olmayan fikstürle profil API'sini sorguluyordu; izinler genişletilmeden aynı tenant'ın gerçek profil satırlarının korunması doğrudan PostgreSQL'de doğrulandı.

   M4 Ortak kaynak okuyucusuna taşınan eski servisin kullanılmayan import ve import sırası düzeltildi; son tam Ruff/isort/Black/mypy kontrolü başarılı.

   **TUZAK**

   M5 `checked` işareti doğruluk kanıtı değildir; 012'nin anlamsal korumaları yeni politikada yalnız inceleme işareti üretir. Tam eşlenmiş fakat anlamı yanlış bir model önerisi kullanıcı açıkça onaylarsa kaydedilebilir.

   M6 Öneriler özgün kaynak üzerinde hesaplanır; en fazla üç öneri, alan başına 64 karakter ve 8192 karakter ham çıktı sınırı vardır. Tekrarlı/örtüşen/bulunamayan veya kesilmiş içerik gösterilir fakat kayıt kanıtı alamaz.

   M7 Aynı önizleme kanıtının tekrarı kendi önceki kaydını döndürür; arada daha yeni sürüm varsa onu geri almaz. Başka eski önizleme 409 üretir; kanıt 15 dakika sonra geçersizdir.

   **GÖZLEM**

   M8 Gerçek PostgreSQL/HTTP testleri normal izinleri, başka tenant/aktör/kaynak kanıtlarını, imza/süre bozulmasını, kullanıcı yetkisinin model sırasında ve kaydetmeden önce değişmesini kapsadı; model çağrısında açık DB işlemi bulunmadı.

   M9 Aynı kanıtın eşzamanlı iki kaydı tek sürüm üretti; farklı eski kanıtların yarışında yalnız biri kaydedildi. Sonraki sürümden sonra eski tekrar kendi gerçek kaydını, transcript okuması en son sürümü döndürdü.

   M10 Kaynak metin/zaman/konuşmacı ve profil korunması; saklama süresi dolumu/açık toplantı silme ile sürüm metni, düzenlemeler ve hash temizliği; birleşik tenant/kaynak FK, benzersizlik, sınırlar, yorumlar ve aktif indeks gerçek veritabanında doğrulandı.

   M11 Domain dosyaları gerçek model deneyinden sonra değişmedi: `transcript_suggestions.py` SHA-256 `f291be7d62af92c1f8144b8c7f2f39c432c9bb8fd8163288cadc3154209995df`; `transcript_correction.py` SHA-256 `9d26d67172afe04821f88d4e5861b9c8e9bdd208ef173d7d418236f889099d1f`.

   **AÇIK**

   M12 Bu raporun L1 kanıtı odaklı backend kapsamıdır; gerçek model isabeti, gerçek tarayıcı, son tam profil kapısı ve güvenlik taraması ana teslim raporunda ayrı kaydedilir. L3 kullanıcı kabulü bu testlerden çıkarılamaz.

   **YAN-ETKİ**

   M13 Ayrı eklemeli sürüm tablosu, amaç ayrımlı HMAC kanıtı, tenant/kaynak/sürüm bağlı servis ve API, nullable okuma DTO'su, kaynak okuyucusu ve retention genişletmesi eklendi; özgün transcript metnine düzeltme yazılmaz.

   M14 Üretilen migration'da kaynak birleşik benzersiz anahtarı çocuk FK'den önce oluşturulacak biçimde sıralandı; yıkıcı geri alma yerine mevcut açık veri incelemesi gerektiren `RuntimeError` yaklaşımı kullanıldı. Yerel şema head'e yükseltildi; eski satırların metni değiştirilmedi.

   M15 Ham model yanıtı ve imzalı kanıt kalıcı tabloda veya raporda tutulmadı; son Unicode düzeltmesi yalnız servis yanıtının gösterimini değiştirdi, model prompt'u ve domain politikası değişmedi.
