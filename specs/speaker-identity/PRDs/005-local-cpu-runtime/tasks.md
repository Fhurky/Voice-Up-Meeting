# Görevler — Yerel CPU çalışma ortamı

- [x] T01 CPU runtime/backend kabulü; 119 inference testi ve 104 testli backend kapısı.
- [x] T02 İki mimaride 47 artifact/hash/65 bağımlılık kenarı ve bağımsız kaynak incelemesi.
- [x] T03 CPU Compose ve kurulum/günlük başlatıcı; 30 başlangıç testi ve iki mimari Compose kontrolü.
- [x] T04 Model ilk indirme/atomik paketleme/tekrar; 18 test ve 3 gerçek hazırlık kontrolü; Mac rehberi.
- [ ] T05 Gerçek CPU model/HTTP testi, kalite/güvenlik kapıları; koşum raporu.
- [ ] T06 Gerçek Mac kurulumu ve kayıt/tanıma; cihaz yoksa açık kanıt maddesi.

10 Eylül kanıtı: [Koşum raporu](../../../../docs/evidence/2026-09-10-local-cpu-runtime/README.md).
T05'in kalite kapısı 104 backend + 39 frontend, ayrı gerçek CPU/PostgreSQL uygulama
entegrasyonu 1 test ile geçti. x86_64 ve gerçek Linux ARM64 CPU üzerinde ayrı ayrı
9 HTTP kontrolü geçti; güvenlik kapısı Gitleaks
olmadığı için çalışmadı. T06 için fiziksel MacBook'a erişim yok; Linux CPU başarısı
Mac kabulü sayılmaz. Bu iki açık görev gizlenerek tam kabul iddiası yapılmaz.
