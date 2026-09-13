# Tasks — Bağlama göre konuşma sözcüklerini gözden geçirme

Kaynak: [PRD](PRD.md), [plan](plan.md).

- [x] T01 Domain/hizmet/adaptör/API ve kaynak değişmezliği; [52 birim + 20 gerçek PostgreSQL testi](../../../../docs/evidence/2026-09-13-contextual-transcript-review/backend.md), kırmızı/yeşil kanıt mevcut.
- [x] T02 Tipli ayarlar, bütün yüzeyler ve yerel kapalı köprü; [runtime raporu](../../../../docs/evidence/2026-09-13-contextual-transcript-review/runtime-report.md), [65 saniyelik proxy regresyonu ve chart kanıtı](../../../../docs/evidence/2026-09-13-contextual-transcript-review/runtime-timeout-report.md).
- [x] T03 Üretilmiş sözleşme/tip, TR/EN tek panel ve kalıcı senaryo; [frontend raporu](../../../../docs/evidence/2026-09-13-contextual-transcript-review/frontend-report.md), [StrictMode kırmızı/yeşil regresyonu](../../../../docs/evidence/2026-09-13-contextual-transcript-review/frontend-strictmode-report.md); son tam kapıda tip drift yok.
- [x] T04 Gerçek Qwen3.5 27B ile 59 tamamlanmış eşlenmiş istek; [kalite/süre raporu](../../../../docs/evidence/2026-09-13-contextual-transcript-review/model-report.md), [64 deney/ölçüm/ledger testi](../../../../docs/evidence/2026-09-13-contextual-transcript-review/evaluation-audit-report.md), `results.md` kaydı mevcut. Gerçek veride doğruluk artışı kanıtlanmadı.
- [x] T05 [30 normal rol HTTP isteği](../../../../docs/evidence/2026-09-13-contextual-transcript-review/live-http-report.md), [dört canlı TR/EN varyantı](../../../../docs/evidence/2026-09-13-contextual-transcript-review/browser-report.md), iki dil rehberi ve [967 testlik tam kapı](../../../../docs/evidence/2026-09-13-contextual-transcript-review/quality-handoff-report.md). Güvenlik kapısı eksik `gitleaks` ile çıkış 2 verdi; görev gerçek çalıştırma/engelleri raporlama olarak tamamlandı, güvenlik kabulü değildir.

[Teslim kanıtı](../../../../docs/evidence/2026-09-13-contextual-transcript-review/README.md)
işlevsel gerçek HTTP/tarayıcı gözlemlerini ve sınırlarını birleştirir. Eksik
güvenlik tarayıcıları, dar ekran görsel yakalama, canlı öneri/reddetme dalları,
headless senaryo yürütümü, Spark/Apple, canlı Kubernetes ve eşzamanlı ağır
ses/metin kapasitesi açık kanıtlardır. Bütün kontrollerin geçtiğine dair
koşulsuz L1/L2 veya L3 kullanıcı kabulü iddiası yoktur. Kalıcı otomatik
düzeltme bu PRD'nin kabul edilmiş geçici önizleme davranışına eklenmedi.
