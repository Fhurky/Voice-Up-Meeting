# Görevler — MP4 toplantı yükleme

- [x] T01 Ses çıkarma kütüphanesi ve birim testleri (Requirement 1).
- [x] T02 Form, hata ve yardım metinleri (Requirement 2).
- [x] T03 Kalıcı tarayıcı senaryosu ve canlı geçiş (Requirement 3).
- [x] T04 Tam kalite kapısı.
- [ ] T05 Kullanıcının 4 konuşmacılı MP4 kaydı (L3).

30 Ekim 2026 kanıtı: `mediaAudio.test.ts` ve form testleri dahil ön yüz 278/278, arka uç 932/932, tüm adımlar geçti.
`16-meeting-mp4-upload.mjs` Edge ile gerçek bir MP4'te (MPEG-4 video, stereo AAC, 8 saniye) geçti: sunucuya 16 kHz tek
kanal WAV gitti, süre korundu, ses sessiz değil, video baytı yok. Paketlenmiş Chromium AAC çözmediği için senaryo
`APP_E2E_BROWSER_CHANNEL` ister. Uzun gerçek MP4 henüz sınanmadı (T05).
