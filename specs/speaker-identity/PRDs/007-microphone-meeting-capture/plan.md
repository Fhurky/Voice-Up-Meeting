# Plan — Mikrofon kaydından toplantı analizi

Kaynak: [Accepted PRD](PRD.md). Sabit profil: `kt-vibecoding-python-web-v2`.
Bu plan uygulanmış mikrofon özelliği veya 002 dosya akışı kabulü değildir.

1. Decision 1–2 / Requirement 3: 002'nin gerçek kaynak/API sözleşmesini ve hedef
   tarayıcıların kapsayıcı çıktısını incele; çevrimdışı decoder, lisans/hash ve
   bağımlılık kabulünü doğrula. 002 örüntüsünü kullan; ikinci model/veri otoritesi kurma.
2. Requirement 1–2: `app/frontend/` içinde kayıt yaşam döngüsü ve sınırlı yükleme
   kuyruğunu önce testle geliştir. İzin/track/son parça/iptal/geç izin sınırlarını
   koru; TR/EN metinleri ve erişilebilir bileşenleri aynı değişimde tamamla.
3. Requirement 3–4: Gerçek 002 yükleme/API istemcisini kullan; codec çözme,
   durum/hata eşlemesi ve destek denetimini backend adapter sınırında bağla.
   Kontrat değişirse OpenAPI/tipleri yeniden üret; şema gereği çıkarsa PRD'yi
   önce güncelle ve profil migrasyon akışını izle.
4. Çalışma bölümü: Decoder/model paketi, typed settings, ortam yüzeyleri,
   Compose/Helm, kaynak bütçesi ve readiness'i senkronize et; runtime egress açma.
5. Kabul ölçütleri: Sıradan yetkili kullanıcıyla TR/EN gerçek mikrofon→durdurma→
   metin/hafıza akışını `e2e/speaker-identity/` senaryosu ve kayıtlı manifest satırıyla
   doğrula. Dar testler ardından `scripts/quality-gate.sh all`, güvenlik ve chart
   kontrollerini çalıştır; `53-test-run-report.md` biçiminde eksikleri kaydet.

Bağımlılık: 002 yüklenen kaynak ve konuşmacılı metin/hafıza sözleşmesi.
Bu bağımlılık 002'nin dosya teslimini mikrofon uygulamasına bağlamaz.
