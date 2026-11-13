# Görevler — Konuşmacı ve sürdürülen yüklemelerde MP4

- [x] T01 Süre sınırı parametreli ses çıkarma ve testleri (Requirement 1): `mediaAudio.test.ts`.
- [x] T02 Konuşmacı formu, hata ve yardım metinleri, testleri (Requirement 2): `AudioJobForm.test.tsx`.
- [x] T03 Sürdürme paneli ve testleri (Requirement 3): `MeetingSourceUpload.test.tsx`.
- [x] T04 Tam kalite kapısı (13 Kasım 2026: arka uç 956/956, ön yüz 295/295, tüm adımlar geçti).
- [x] T05 Kalıcı tarayıcı senaryosu ve canlı geçiş (Requirement 4): `18-speaker-mp4-upload.mjs` Edge ile iki kez üst üste geçti. Video
  ve AAC ses içeren 47 saniyelik MP4'ten profil oluştu; aynı kişinin başka bölümlerinden 34 saniyelik MP4 0,91 benzerlikle tanındı.
  İki yükleme de WAV'dı, MP4 baytı yoktu. Sürdürme panelinde MP4 yalnız birim testiyle doğrulandı.
- [ ] T06 Kullanıcının kendi MP4 dosyasıyla denemesi (L3).
