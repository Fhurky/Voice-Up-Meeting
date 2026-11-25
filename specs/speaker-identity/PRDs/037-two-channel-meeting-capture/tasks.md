# Görevler — Teams masaüstü toplantısını iki kanalla kaydetme

- [x] T01 Tarayıcı kayıt modülü (Requirement 2). Çıktılar: `meetingCapture.ts`, `meetingCapture.worklet.ts`,
  `meetingCapturePcm.ts`, `captureUpload.ts` ve birim testleri. 25 Kasım 2026: 32/32 test geçti; lint ve tip denetimi
  temiz.
- [x] T02 Edge'de sistem sesi denemesi (Decision 1–2). 25 Kasım 2026, bu bilgisayar, Edge 158, görünür pencere:
  - Kayıt modülü gerçek ekran paylaşım penceresinde `--auto-select-desktop-capture-source` ile "Entire screen" veya
    "Tüm ekran" seçilerek başlatıldı. 16 kHz kabul edildi.
  - Görüntü izi başta durduruldu; sistem ses izi canlı kaldı.
  - Varsayılan çıkıştan çalınan 3 saniyelik 440 Hz ton kanal 1'de 2–5. saniyelerde ölçüldü (RMS 0,15–0,18). Tonun
    olmadığı saniyeler 0'dı.
  - Mikrofon kanalı 0 kaldı: varsayılan mikrofon kablosuz kulaklıktı ve ses vermiyordu. Mikrofonun kanal 0'daki kanıtı
    T11'deki gerçek görüşmeye kalır.
  - `--use-fake-ui-for-media-stream` sistem sesi yerine sahte bir ses kaynağı ("Fake audio") verir. Bu ayar yalnız akış
    denemesi içindir; sistem sesi kanıtı sayılmaz.
- [x] T03 Şema, migrasyon ve şema testi (Requirement 4). Migrasyon `1a4b9071a9a5`; yerelde uygulandı, doğrulandı.
  `test_the_migrated_schema_carries_capture_and_channel_semantics`: açıklamalar, kısıtlar ve varsayılanlar veritabanında.
- [x] T04 Kayıt API'si: oluşturma, parça, tamamlama, mühürleme. Servis, depo, depolama, birim ve entegrasyon testleri
  (Requirement 3). `tests/integration/test_meeting_capture.py`, `tests/unit/test_meeting_capture.py`.
- [x] T05 Kanallara göre işleme: worker, parça, kişi hafızası kanıtı, satır sırası. Testler (Requirement 5).
  `tests/integration/test_meeting_two_channel_processing.py`: kanal başına tek geçiş, aynı model etiketinin iki kanalda
  ayrı konuşmacı olması, ilk konuşmaya göre numara, zaman sırasıyla satırlar. Parçalı akışta kanallar arası birleştirme
  çatışma olarak yasak.
- [x] T06 `meeting_capture` olayı ve testi (Requirement 7). Her reddedilen boşluk ayrı bir `meeting_capture_gap`
  olayıdır; reddedilen istek kalıcı sayaç yazamaz.
- [x] T07 OpenAPI dışa aktarımı ve ön yüz tipleri.
- [x] T08 Ön yüz ekranları ve yerelleştirme. Ön yüz testleri (Requirement 1). Arka uç 996/996, ön yüz 334/334
  (25 Kasım 2026, yerel koşu; tam kapı T10'da).
- [x] T09 Tarayıcı senaryosu `19-meeting-two-channel-capture.mjs` ve kalite manifestosu (Requirement 8). 25 Kasım 2026:
  canlı uygulamada Edge 158, sıradan rollü toplantı hesabı, sahte aygıtlar, mikrofona 40 saniyelik açık AMI konuşma
  kesiti; PASS. Ürün arayüzünden gerçek paylaşım penceresiyle otomatik deneme bu bilgisayarda bir kez takıldı: Edge'in
  otomatik ekran seçimi, aynı oturumda daha önce çalışan T02 kontrol denemesinde de artık seçim yapmadı. Gerçek sistem
  sesi kanıtı T02 ve T11'dedir.
- [x] T10 Tam kalite kapısı. 25 Kasım 2026, `gate_exit=0`: arka uç 997/997, ön yüz 334/334; migrasyon, OpenAPI, tipler,
  yönetişim ve chart adımları geçti.
- [ ] T11 Gerçek Teams ölçümleri: 60 dakika arka planda, iki deneme görüşmesi ve tek kanal karşılaştırması, hoparlör ve
  kulaklık (Requirement 9). Sonuçlar `results.md`'ye yazılır.
- [ ] T12 Kullanıcı kabulü (L3).
