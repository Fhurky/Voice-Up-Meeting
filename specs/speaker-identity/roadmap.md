# speaker-identity yol haritası

Her satır bağımsız bir yetenek gereksinimine bağlanır. Draft durumu uygulama kabulü değildir.

| Order | Capability | PRD | Status |
|---:|---|---|---|
| 001 | local-speaker-pilot | [PRD](PRDs/001-local-speaker-pilot/PRD.md) | Accepted — guarded speech recovery and fresh public holdout measured; quality target and Turkish acceptance incomplete |
| 002 | long-recording-analysis | [PRD](PRDs/002-long-recording-analysis/PRD.md) | Accepted — file/microphone transcript and automatic new-speaker memory requested; provider access/runtime preparation pending, implementation not complete |
| 003 | live-speaker-analysis | [PRD](PRDs/003-live-speaker-analysis/PRD.md) | Draft — selected after 002 identity continuity |
| 004 | spark-remote-inference | [PRD](PRDs/004-spark-remote-inference/PRD.md) | Accepted — Spark application path live; security release evidence unavailable |
| 005 | local-cpu-runtime | [PRD](PRDs/005-local-cpu-runtime/PRD.md) | Accepted — fully local MacBook CPU environment requested; implementation and device evidence tracked in tasks |
| 006 | local-admin-login | [PRD](PRDs/006-local-admin-login/PRD.md) | Accepted — one-click local administrator login and GitHub publication requested |

9 Eylül 2026 sıralama kararı: [uzun kayıt ve canlı çalışma](../../docs/LONG_RECORDING_STRATEGY.md).
001'in gerçek kişi deneyi önce gelir; sonraki model seçimi ölçüme dayanır.

Yeni cihaz isteğiyle 004, gerçek veri deneyinin çalışma ortamını hazırlamak için öne alındı.
002/003 ve 001 gerçek kişi doğruluğu kanıtı açık kalır; donanım geçişi bunların tamamlanması değildir.

9 Eylül açık veri deneyi tamamlandı: 140 kişi/604 parça, ayrı testte 50 adaydan 29
profil ve 77/150 doğru tanıma; yeni kişinin geri dönüşü kalite nedeniyle başarısız.
[Kanıt](../../docs/evidence/2026-09-09-public-speaker-evaluation/README.md).
001'in yüksek doğruluk hedefi karşılanmadı; kısa konuşma bölgelerinin kullanımı ve
kalite retleri kalibrasyon üzerinde incelenmelidir. 002/003'e geçiş kabulü verilmedi.

Sonraki korumalı kurtarma ölçümü tamamlandı: kalibrasyon 109→111/150, aynı tarihsel
test 77→78/150 doğru; ayrı yeni temiz İngilizce grupta 40/50 profil ve 116/150 doğru.
[Yeni kanıt](../../docs/evidence/2026-09-09-speech-recovery/README.md). Eşik/model
değişmedi; ilk profil kaydındaki kalite retleri ve temsilî Türkçe doğruluk 001'de
açık kalır. Yeni grubun oranı eski daha zor grupla eşdeğer karşılaştırma değildir.

10 Eylül kullanıcı açıklaması: 50 bir profil kotası değil, yüksek doğruluk
hedeflenen katılımcı düzeyidir. 001 Decision 11 ile kota kaldırıldı; 51. profil
canlı Spark'ta oluşturuldu, 200 üzeri kayıt davranışı teknik testlerde doğrulandı.
[Kanıt](../../docs/evidence/2026-09-10-speaker-quality-target/README.md).
Model aynı kaldı; [kayıt retleri ve model karşılaştırması araştırması](../../plans/SPEAKER_QUALITY_50.md)
001'in açık doğruluk hedefini besler, yeni model seçimi veya 002/003 kabulü değildir.

10 Eylül sonraki kullanıcı talimatı: dosya yükleme veya mikrofonla kayıt sonrası
konuşmacılı transkript ve yeni kişilerin otomatik hafızaya alınması şimdi istenen
ürün akışıdır. Bu nedenle 002 kapsamı genişletilip Accepted yapıldı ve uygulama
önceliği verildi; 001 kalite kabulü hâlâ açık. Mikrofon kaydını durdurup analiz
etme 002, canlı konuşmacı kimliği 003'tür; canlı transkript kapsamı eklenmedi.
[Akış](../../docs/MEETING_WORKFLOW.md),
[uygulama planı](PRDs/002-long-recording-analysis/plan.md).
