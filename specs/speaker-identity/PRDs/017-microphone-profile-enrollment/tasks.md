# Görevler — Mikrofonla temiz profil kaydı

- [x] T01 Konuşmacılar ekranında mikrofonla yeni profil ve örnek ekleme.
- [x] T02 TR/EN yönlendirme metni, durum ve hata mesajları; klavye erişimi.
- [x] T03 Vitest ve tarayıcı senaryosu; canlı mikrofon kanıtı ayrı işaretli.
- [ ] T04 Temiz galeri ile otomatik galerinin 015 protokolüyle karşılaştırılması.
- [x] T05 Tam kalite kapısı ve koşum raporu.

29 Ekim 2026 ara kanıtı: `SpeakerMicrophoneEnrollment` bileşeni 007 yakalamasını
120 saniyelik çağıran sınırıyla (`maxSeconds`) kullanır; 001 akışıyla yükler, iş
oluşturur, sonucu aynı bölümde izler. 10 saniyeden kısa veya sessiz kayıt
gönderilmez; yükleme hatasında aynı idempotency anahtarıyla yeniden denenir.
Vitest: bileşen 10/10, Konuşmacılar sayfası 17/17, yakalama 15/15; iki davranış
bozularak (kısa kayıt sınırı, anahtar tekrarı) testlerin yakaladığı doğrulandı.
`13-microphone-profile-enrollment.mjs` sıradan yazar ve okuyucu hesapla TR 1440 ve
EN 390 px'te geçti (sıfır iş kaydı yazımı, konsol hatası yok). Ön yüz kalite kapısı
227/227; 30 Ekim 2026 tam kapısı (backend 895/895) geçti. Fiziksel mikrofonla kayıt (`APP_E2E_MICROPHONE_LIVE=1`) koşulmadı; bu kanıt
007'deki gibi ayrı işaretlidir ve gerçek mikrofonlu bir oturum gerektirir.
