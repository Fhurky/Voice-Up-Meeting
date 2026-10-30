# Görevler — Ayarlar menüsü ve işlemci seçimi

- [x] T01 Çıkarım servisinde geçiş ve testleri (Requirement 1): `test_processor_switch.py`, çıkarım testleri 256/256.
- [x] T02 Arka uç, sözleşme ve testleri (Requirement 2): `test_meeting_processor.py`, `test_meeting_context_inputs.py`.
- [x] T03 Ayarlar sayfası ve testleri (Requirement 3): `SettingsPage.test.tsx`.
- [x] T04 Tam kalite kapısı (31 Ekim 2026: arka uç 956/956, ön yüz 287/287, tüm adımlar geçti).
- [x] T05 Çalışan uygulamada gerçek geçiş ve tarayıcı senaryosu (Requirement 4): `17-settings-processor.mjs` 2/2. Beş ardışık geçiş 53–58 saniye,
  konteyner yeniden başlamadı, bellek 2,6–3,0 GiB. 37 saniyelik kayıt CPU'da 68 saniye (tepe 4,4 GiB, bellek hatası yok), GPU'da 9 saniye; cihaz servis
  kaydından doğrulandı. İş sürerken geçiş 409 `inference_busy` aldı. Yükleme hatasında geri dönüş yalnız birim testiyle doğrulandı.
- [ ] T06 Kullanıcı kabulü (L3).
