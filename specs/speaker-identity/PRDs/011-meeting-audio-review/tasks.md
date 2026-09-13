# Tasks — Toplantı metninden kaynak sesi inceleme

Kaynak: [Accepted PRD](PRD.md), [plan](plan.md).

- [x] T01 Gerçek dosya ve tenant/lifecycle/HTTP kırmızı testleri; önizleme adaptörü, servis ve API; [145 testlik dar kanıt](../../../../docs/evidence/2026-09-13-usability-improvement/audio-preview-backend-report.md).
- [x] T02 Ortak sınırlı ikili istemci, üretilmiş sözleşme/tip ve toplantı servisi; [auth/yanıt sınırı regresyonları](../../../../docs/evidence/2026-09-13-usability-improvement/audio-review-frontend-report.md), tam kapıda sözleşme/tip drift geçti.
- [x] T03 TR/EN erişilebilir tek oynatıcı ve satır bölümleme/iptal/temizlik; aynı ön yüz raporunda 64 dar test; [gerçek tarayıcıda](../../../../docs/evidence/2026-09-13-usability-improvement/browser-review-report.md) dört oynatma varyantı.
- [x] T04 [Gerçek normal rol HTTP](../../../../docs/evidence/2026-09-13-usability-improvement/live-preview-http-report.md), gerçek CUA tarayıcı, kalıcı `09-meeting-audio-review.mjs` ve iki dilde rehber tamamlandı; headless senaryo yürütümü ve fiziksel ses gözlenmediği açık kaydedildi.
- [x] T05 [Tam profil/güvenlik kapıları ve nihai rapor](../../../../docs/evidence/2026-09-13-usability-improvement/quality-report.md): 845 otomatik test başarılı; güvenlik kapısı `gitleaks` yokluğunda çıkış 2 verdi. Görev kapıların çalıştırılması ve engellerin raporudur; güvenlik kabulü tamamlanmış sayılmaz.

En yüksek gözlenen işlevsel kanıt L2. Eksik headless koşumu, tarayıcı dosya
seçme izni, fiziksel ses ve L3 kullanıcı kabulü raporda açık; 50 kişi hedefi
bu dar inceleme yeteneğiyle tamamlanmış değildir.
