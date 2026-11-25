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
- [ ] T03 Şema, migrasyon ve şema testi (Requirement 4).
- [ ] T04 Kayıt API'si: oluşturma, parça, tamamlama, mühürleme. Servis, depo, depolama, birim ve entegrasyon testleri
  (Requirement 3).
- [ ] T05 Kanallara göre işleme: worker, parça, kişi hafızası kanıtı, satır sırası. Testler (Requirement 5).
- [ ] T06 `meeting_capture` olayı ve testi (Requirement 7).
- [ ] T07 OpenAPI dışa aktarımı ve ön yüz tipleri.
- [ ] T08 Ön yüz ekranları ve yerelleştirme. Ön yüz testleri (Requirement 1).
- [ ] T09 Tarayıcı senaryosu `19-meeting-two-channel-capture.mjs` ve kalite manifestosu (Requirement 8).
- [ ] T10 Tam kalite kapısı.
- [ ] T11 Gerçek Teams ölçümleri: 60 dakika arka planda, iki deneme görüşmesi ve tek kanal karşılaştırması, hoparlör ve
  kulaklık (Requirement 9). Sonuçlar `results.md`'ye yazılır.
- [ ] T12 Kullanıcı kabulü (L3).
