# Plan — Model seçimi ve kaydedilen düzeltmeler

Kaynak: [Accepted PRD](PRD.md); `kt-vibecoding-python-web-v2`.

1. Requirement 1: Kurulu model DTO/port ve Ollama `/tags` + `/show` doğrulaması;
   eski 012 adaptör/deney davranışını koruyan yeni görünür yanıt yolu.
2. Requirement 1, 2: Domain öneri eşleme ve amaç ayrımlı imzalı kanıt; kaynak,
   model, tenant/aktör ve sürüme bağlı yeni öneri/kaydetme hizmet/API'si.
3. Requirement 2: SQLAlchemy revizyon authority ve repository; üretilmiş
   migration, yerel apply/validate/status; retention scrub ve gerçek DB testleri.
4. Requirement 3: Üretilmiş OpenAPI/tipler, model dropdown/explicit kontrol,
   yeşil inline diff, bütün önerilerin ayrıntısı, save ve orijinal/saved geçişi;
   TR/EN, frontend testleri, kalıcı ve canlı tarayıcı senaryosu.
5. Requirement 4: Yeni model/API deneyleri ve günlüğü; runtime iki önizleme
   yolu timeout regresyonu; tam kapı/güvenlik ve rapor, bütün mevcut yetkili
   değişikliklerin sır/özel veri kontrolü sonrası commit/push doğrulaması.

Özel cevaplar yalnız Git dışı `outputs/2026-09-13-saved-transcript-corrections/`;
toplu kanıtlar `docs/evidence/2026-09-13-saved-transcript-corrections/`.
