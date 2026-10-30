# PRD — Toplantı ön girdileri

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [022 — meeting-context-inputs](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak (30 Ekim 2026): Kullanıcı toplantı oluştururken isteğe bağlı konu, cevaplanması beklenen
sorular ve kişi sayısı bilgilerinin girilmesini ve bunların sonraki
[023](../023-meeting-effectiveness-analysis/PRD.md) analizine temel olmasını istedi.
Kabul edilirse 002'deki `expected_speakers` anlamı Decision 2 ile değişir.
Kabul (30 Ekim 2026): Kullanıcı taslağı kabul etti; 023 taslak kaldı.

## Amaç ve önceki durum

Bugün toplantı oluştururken ad, dil, toplam katılımcı sayısı (`participant_count`), kesin konuşan
kişi sayısı (`expected_speakers`), katılımcı listesi (016) ve hafıza seçeneği girilebilir. Toplantının
konusu ve cevaplanması beklenen sorular yoktur. Hedef: bu iki bilgiyi eklemek, kişi sayısı alanlarını
anlaşılır kılmak ve hepsini isteğe bağlı tutmak. Hiçbir ön girdi girilmeden toplantı bugünkü gibi
işlenir.

## Kararlar

Decision 1: Formda "Toplantı bilgileri" bölümü: konu (en çok 500 karakter) ve sorular (en çok 20
soru, her biri en çok 500 karakter; satır ekle/sil). Dil, en çok kişi sayısı, tahmini kişi sayısı ve
katılımcı listesi aynı formda kalır; hepsi isteğe bağlıdır.

Decision 2: `participant_count` "En çok kişi sayısı" olur ve parça analizine üst sınır olarak gider.
`expected_speakers` "Tahmini konuşan kişi sayısı" olur ve bağlayıcı değildir: modele `num_speakers`
veya `max_speakers` olarak gitmez, kümelemeyi zorlamaz (021 Decision 3); yalnız sonuçta gözlenen
sayıyla farkı bildirir. Tahmin en çok sayıyı aşamaz. Kolon adı değişmez, göç gerektirmez.

Decision 3: Sorular ayrı `meeting_question` tablosunda tutulur (`public_id`, `tenant_id`,
`meeting_id`, `ordinal`, `text`, zorunlu yaşam döngüsü alanları); 023 cevapları bu kimliğe bağlar.
Konu `meeting.subject` metin kolonudur. Sorular normalleştirilir, boş ve yinelenen soru reddedilir.

Decision 4: Konu ve sorular toplantı oluşturulurken alınır ve `Idempotency-Key` parmak izine girer.
Okuma mevcut `meeting_analysis:read`, yazma `meeting_analysis:run` yetkisiyle yapılır. Sonuç ekranında
"Toplantı bilgileri" olarak gösterilir. Sonradan düzenleme bu kapsamda yoktur.

Decision 5: Bu PRD yapay zekâ çağrısı yapmaz; konu ve sorular konuşma modellerine verilmez, yazıya
çevirmeyi veya kimliği değiştirmez. Girdiler toplantı içeriği sayılır: aynı kiracı, saklama ve silme
kurallarına tabidir, günlüklere yazılmaz.

## Gereksinimler

Requirement 1: Şema otoritesi ve gözden geçirilmiş Alembic göçü (Decision 3); kiracı nitelikli
yabancı anahtar, soft delete ve kısmi indeks.

Requirement 2: `MeetingCreate` ve `MeetingResponse` genişler; doğrulama, kiracı yalıtımı, yetki ve
idempotent tekrar testleri. OpenAPI ve ön yüz tipleri yeniden üretilir.

Requirement 3: Worker `expected_speakers` değerini modele göndermez (Decision 2); mevcut sayı
testleri yeni anlama göre güncellenir, farkı bildirme davranışı korunur. `run-ami-evaluation.py`
`--known-speaker-count` seçeneği ayrı bir bilgi olarak `participant_count` kullanır.

Requirement 4: `MeetingUploadForm` ve sonuç ekranı TR/EN metinlerle güncellenir, soru satırları
klavye ile erişilebilirdir, 390 ve 1440 px'te taşma yoktur. Kalıcı tarayıcı senaryosu eklenir.

## Katmanlar

Vektör: N/A — gömme yok. Worker: yalnız Requirement 3. Gözlemlenebilirlik: N/A — yeni sinyal yok,
konu ve soru metni günlüğe yazılmaz. Dağıtım: yalnız göç; yeni ayar yok.

## Kabul ölçütleri

- [ ] Hiç ön girdi verilmeden toplantı akışı değişmeden çalışır.
- [ ] Konu ve sorularla toplantı oluşturulur, sonuç ekranında görülür; kiracı ve yetki testleri geçer.
- [ ] Tahmini kişi sayısı modele gitmez; en çok sayı üst sınır olarak gider.
- [x] Tam kalite kapısı ve tarayıcı senaryosu geçer; kullanıcı formu kabul eder (L3). (30 Ekim 2026: kullanıcı inceledi, "şimdilik yeterli".)
