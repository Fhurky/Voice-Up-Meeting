# Görevler — Toplantı katılımcı listesi

- [x] T01 `meeting_participant` şema otoritesi ve incelenmiş migration (`0cbad1723e7d`, yalnız ekleme).
- [x] T02 Liste kısıtlı ve liste dışı aday sorguları; Decision 2–4 servis kararları; birim ve PostgreSQL testleri.
- [x] T03 API sözleşmesi, hatalar, idempotency parmak izi; OpenAPI ve frontend tipleri.
- [x] T04 Aranabilir çoklu profil seçici ve toplantı sayfası gösterimi; TR/EN; vitest ve tarayıcı senaryosu.
- [ ] T05 AMI listeli/listesiz eşlenmiş ölçüm ve `results.md` kaydı.
- [x] T06 Tam kalite kapısı, canlı doğrulama ve koşum raporu.

29 Ekim 2026 ara kanıtı: `test_meeting_roster.py` gerçek PostgreSQL'de 8/8; aynı ses
vektörü listesiz denendiğinde iki benzer kişi arasında `insufficient_margin` ile
belirsiz kalır, liste yalnız birini içerdiğinde doğru profile bağlanır; liste dışı
daha iyi aday `outside_roster` ile belirsiz bırakır; listede olmayan kayıtlı misafir
yeni profil açılmadan tanınır. Toplantı/hafıza entegrasyon paketleri 95/95, backend
statik denetimleri temiz, frontend kapısı 214/214, `12-meeting-participant-roster.mjs`
sıradan rolle TR 1440 ve EN 390 px'te geçti. Bu sonuçlar sabit test vektörleridir;
gerçek ses üzerindeki etki T05'te ölçülür.

30 Ekim 2026: tam kapı geçti (backend 895/895 gerçek PostgreSQL, frontend 227/227, migration,
OpenAPI, tip, yönetişim ve chart adımları). T05 AMI eşlenmiş ölçümü taban çizgisinden sonra koşuyor.
