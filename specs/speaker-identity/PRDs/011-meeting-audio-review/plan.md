# Plan — Toplantı metninden kaynak sesi inceleme

Kaynak: [Accepted PRD](PRD.md); profil `kt-vibecoding-python-web-v2`.

1. Requirement 1, 3: Backend gerçek dosya ve PostgreSQL/HTTP testlerini önce
   kırmızı çalıştır; `infrastructure/meeting_audio.py` inceleme çıkarımını ve
   `services/meeting_service.py` erişim/süre/lifecycle sınırını uygula.
2. Requirement 1, 2: `api/meetings/router.py` binary önizleme sözleşmesini
   bağla; çalışma zamanı operation ID `meeting_audio_preview`, sorgular `start_seconds` ve
   `end_seconds`. Mevcut şemayı değiştirme; OpenAPI'yi çevrimdışı üret.
3. Requirement 2, 3: Ortak API istemcisinde sınırlı Blob okuma ve
   `services/meetings.ts` tipli önizleme çağrısını ekle. Mevcut kanonik dışa
   aktarım operation ID alanlarını kaldırdığı için üretilmiş `paths` içindeki
   GET sorgu tipini kullan; kimlik/tenant ve 401 regresyonlarını koru.
4. Requirement 2, 3: `MeetingResults` içinde ayrı odaklı inceleme bileşeni,
   TR/EN katalogları, bir aktif oynatıcı ve uzun satırın 30 saniyelik bölümlerini
   uygula. Önce hata/iptal/sayfa değişimi için gözlenebilir frontend testleri.
5. Requirement 4: Geçerli örnekle ters proxy üzerinden canlı API/tarayıcı
   doğrulaması; `e2e/speaker-identity/` senaryosu ve manifest kaydı; Türkçe ve
   İngilizce kullanım belgeleri. Fiziksel hoparlör çıktısını varsayma.
6. Requirement 2–4: Dar kontroller, `scripts/quality-gate.sh all`, güvenlik
   kapısı ve sözleşme/tip drift; gerçek sonuçlar sabit biçimli kanıt raporuna.

002 Decision 25'in Türkçe parça düzeltmesi ayrı dosyalarda paralel yürütülür.
Kabul/çıktı kaynakları `docs/evidence/2026-09-13-usability-improvement/`;
özel dosya/kimlik bilgileri `outputs/` altında Git dışında kalır.
