# Koşum raporu — 2026-09-13 · Normal kullanıcıyla canlı öneri ve açık kayıt akışı

1. Sonuç: Canlı uygulamada 16 HTTP isteğinin beklenen durumları gözlendi; gerçek 27B önerisi bir kez kaydedildi, tekrar aynı sürümü döndürdü ve özgün kaynak korundu — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; çalışan yerel nginx/FastAPI/PostgreSQL/Ollama yığını, sıradan uygulama rolü ve ayrı test kaynağı. Ana yürütücünün `outputs/2026-09-13-saved-transcript-corrections/live-http.private.json` kanıtından yalnız toplu gözlemler alındı; bu rapor üretimi HTTP veya model çağrısını tekrarlamadı.

   | Gözlem | Sonuç |
   |---|---|
   | HTTP yöntemi ve yanıt kodu | POST 200: 5; GET 200: 7; POST 422: 2; GET 401: 1; GET 404: 1; toplam 16. |
   | Kurulu model listesi | Üç yerel model görüldü; liste okuma üretim başlatmadı. |
   | Gerçek model çağrısı | `qwen3.5:27b` ile bir çağrı; `suggested`, kesilmemiş yanıt, beklenen düzeltme sürümü 0. |
   | Açık kayıt ve tekrar | Bir yeni düzeltme sürümü: 1; aynı kanıtla tekrar aynı kayıt sonucunu döndürdü. |
   | Kaynak ve yaşam döngüsü | Özgün transcript değişmedi; mevcut iş verilerinin korunduğu kaydedildi; tekrar okumada kayıt görünür. |
   | Erişim sınırı | Başka tenant kaynağı gizli kaldı; doğrulama ve kimlik doğrulama hataları beklenen HTTP durumlarını verdi. |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 16 HTTP isteği, 16 model çağrısı veya 16 kayıt değildir; bu akışta gerçek model bir kez çağrıldı ve bir yeni sürüm kaydedildi. HTTP 401/404/422 yanıtları sınır doğrulama adımlarıdır.

   **GÖZLEM**

   M2 Özel kanıtta `business_data_unchanged`, `source_unchanged`, `idempotent` ve `foreign_tenant_hidden` gözlemleri true; kaydedilen model adı/digest'i önerideki seçilen çiftle aynıdır.

   M3 Akış uygulama düzeyinde normal rolle gerçekleştirildi; gerçek HTTP, model ve PostgreSQL sınırları için L2 kanıtıdır. Tarayıcı akışı bu raporun parçası değildir.

   **AÇIK**

   M4 Bu tek kaynak kaydetme/idempotency/erişim akışını doğrular; temsilî Türkçe düzeltme doğruluğu, eşzamanlı yük ve kullanıcı kabulü iddia etmez. Ayrı [model regresyon raporu](model-report.md) doğruluk sınırlarını belirtir.

   **YAN-ETKİ**

   M5 Ayrı test kaynağında bir düzeltme revizyonu oluşturuldu. Token, kullanıcı/tenant/toplantı/satır kimlikleri ve özel kaynak/model metinleri bu kamu raporuna aktarılmadı.
