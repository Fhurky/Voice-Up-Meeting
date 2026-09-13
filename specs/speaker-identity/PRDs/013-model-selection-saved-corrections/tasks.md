# Tasks — Model seçimi ve kaydedilen düzeltmeler

Kaynak: [PRD](PRD.md), [plan](plan.md).

- [x] T01 Model liste/seçim ve sınırlı görünür yanıt adapter/port testleri — [kanıt](../../../../docs/evidence/2026-09-13-saved-transcript-corrections/adapter-report.md).
- [x] T02 Domain, imzalı kanıt, yetkili öneri/save API, revision authority/repository ve retention; migration ve gerçek DB testleri — [111 test ve migration](../../../../docs/evidence/2026-09-13-saved-transcript-corrections/backend.md).
- [x] T03 Tipli frontend, TR/EN yeşil öneriler, kayıt/özgün görünüm, otomatik testler ve kalıcı tarayıcı senaryoları — [207 test](../../../../docs/evidence/2026-09-13-saved-transcript-corrections/frontend-report.md). Senaryo scriptlerinin doğrudan yürütümü açık; akışları T04'te canlı çalıştırıldı.
- [x] T04 Gerçek model/normal rol HTTP ve gerçek tarayıcı deneyi; results.md ve toplu raporlar — [model](../../../../docs/evidence/2026-09-13-saved-transcript-corrections/model-report.md), [HTTP](../../../../docs/evidence/2026-09-13-saved-transcript-corrections/live-http-report.md), [tarayıcı](../../../../docs/evidence/2026-09-13-saved-transcript-corrections/browser-report.md). Dar görsel yakalama zaman aşımı açıkça kayıtlıdır.
- [x] T05 Tam kalite kapısı, migration/güvenlik/özel veri kontrolü ve eksik araç/ortam kanıtlarının raporlanması — [1.084 test](../../../../docs/evidence/2026-09-13-saved-transcript-corrections/quality-report.md), [özel veri incelemesi](../../../../docs/evidence/2026-09-13-saved-transcript-corrections/publication-audit.md). Eksik güvenlik tarayıcısı başarılı sayılmadı.
- [x] T06 Kullanıcı talimatındaki commit/push ve uzak commit doğrulaması — `5d47874e6d3eb6ce60da4bf5f83b1f2ef8d94512` uygulama commit'i GitHub `main` ile eşleşti; [kanıt](../../../../docs/evidence/2026-09-13-saved-transcript-corrections/publication-report.md).

T05 ve T06, planın Requirement 4'e bağlı son adımının ayrı doğrulanabilir
parçalarıdır. En yüksek canlı kapsam L2'dir; temsilî Türkçe doğruluk ve L3
kullanıcı kabulü bu dört regresyon veya sentetik kayıt akışından çıkarılmaz.
