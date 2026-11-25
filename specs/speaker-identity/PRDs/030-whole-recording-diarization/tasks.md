# Görevler — Tüm kayıtta tek geçişte konuşmacı ayırma

- [x] T01 Çıkarım: tüm kayıt uç noktası ve testleri (Requirement 1): `test_recording_audio.py`, `test_meeting_recording.py`.
- [x] T02 Çıkarım: verilen aralıklarla parça analizi ve testleri (Requirement 2): `test_meeting_recording.py`, `test_meeting_models.py`.
- [x] T03 Arka uç: `meeting_diarization` şeması, migrasyon `518a67a49001` ve şema testi (Requirement 3).
- [x] T04 Arka uç: kaydı kaynak hızında tek kanal PCM16 olarak bloklarla okuyan okuyucu; 16 kHz'e dönüşüm çıkarım servisinde akışla yapılır (Requirement 4).
- [x] T05 Arka uç: adaptör, worker adımı, etiketle bağlama, geri dönüş, temizlik; birim ve entegrasyon testleri (Requirement 3): `test_meeting_whole_recording.py` (birim ve entegrasyon).
- [x] T06 Gözlemlenebilirlik olayı ve testi (Requirement 5).
- [x] T07 Tam kalite kapısı (17 Kasım 2026: arka uç 984/984, ön yüz 295/295, tüm adımlar geçti; çıkarım testleri 288/288).
- [x] T08 Süre ve bellek ölçümü (Requirement 6a): çalışan servisin kendi sürecinde, AMI kayıtları uç uca eklenerek; boştayken
  2,9 GiB. 90 dakika 142 sn ve en çok 3,8 GiB; 120 dakika 235 sn ve 4,3 GiB; 240 dakika 498 sn ve 6,6 GiB. Süre sınırı 120 dakika
  oldu; dağıtım sınırı (8 GiB) değişmedi.
- [ ] T09 AMI test, iki koşul, ürün akışıyla DER (Requirement 6b).
- [ ] T10 AMI uzak mikrofon, rotasyon 2, kişi tanıma (Requirement 6c).
- [ ] T11 İki gerçek Türkçe toplantıda konuşmacı sayısı ve MP4 tarayıcı senaryosu (Requirement 6d).
- [ ] T12 Kullanıcı kabulü (L3).

17 Kasım 2026 ilk canlı deneme: 36 dakikalık, 11 konuşmacılı Türkçe toplantıda tek geçiş 56 saniyede 11 konuşmacı buldu (önceki
akış 15). İlk parça kayıt doğrulamasında reddedildi: parça sonucu, ses etkinliği aralıkları varken yalnız eski tarifi kabul ediyordu.
Düzeltildi ve regresyon testi eklendi (`test_attributed_chunk_with_speech_ranges_is_a_valid_result`); toplantı "yeniden dene" ile
kaldığı yerden sürdü ve 387 saniyede başarıyla bitti.
