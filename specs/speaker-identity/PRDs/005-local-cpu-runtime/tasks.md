# Görevler — Yerel CPU çalışma ortamı

- [x] T01 CPU runtime/backend kabulü; 119 inference testi ve 104 testli backend kapısı.
- [x] T02 İki mimaride 47 artifact/hash/65 bağımlılık kenarı ve bağımsız kaynak incelemesi.
- [x] T03 CPU Compose ve kurulum/günlük başlatıcı; 30 başlangıç testi ve iki mimari Compose kontrolü.
- [x] T04 Model ilk indirme/atomik paketleme/tekrar; 18 test ve 3 gerçek hazırlık kontrolü; Mac rehberi.
- [ ] T05 Gerçek CPU model/HTTP testi, kalite/güvenlik kapıları; koşum raporu.
- [ ] T06 Gerçek Mac kurulumu ve kayıt/tanıma; cihaz yoksa açık kanıt maddesi.
- [x] T07 Temiz GitHub kopyasında Windows/Linux başlangıç doğrulaması regresyonu;
  aynı içerikte aynı sonuç, gerçek içerik değişikliğinde ret ve değişmeyen üretim kilidi.
- [x] T08 Ayrı boş Docker motorunda ilk CPU kurulumu, yönetici oluşturma, ayrı kamu
  kayıtlarıyla kayıt/tanıma/bilinmeyen kişi ve yeniden başlatmada profil kalıcılığı;
  mevcut NVIDIA ortamını koruyan komutlar ve gözlenen sonuçlarla koşum raporu.

10 Eylül kanıtı: [Koşum raporu](../../../../docs/evidence/2026-09-10-local-cpu-runtime/README.md).
T05'in kalite kapısı 104 backend + 39 frontend, ayrı gerçek CPU/PostgreSQL uygulama
entegrasyonu 1 test ile geçti. x86_64 ve gerçek Linux ARM64 CPU üzerinde ayrı ayrı
9 HTTP kontrolü geçti; güvenlik kapısı Gitleaks
olmadığı için çalışmadı. T06 için fiziksel MacBook'a erişim yok; Linux CPU başarısı
Mac kabulü sayılmaz. Bu iki açık görev gizlenerek tam kabul iddiası yapılmaz.

T07–T08 kanıtı: [Temiz kurulum raporu](../../../../docs/evidence/2026-09-10-fresh-cpu-install/README.md).
6 sıralama regresyonu, 153 backend + 59 frontend testi ve 20 canlı CPU kontrolü geçti;
RTX 4060 üzerinde 3 gerçek iş tamamlandı. Yeniden başlatmada profil, örnek, iş,
tekrar anahtarı ve model korundu. T05 güvenlik aracı eksikliği, T06 fiziksel Mac
erişimi nedeniyle açık kalır.
