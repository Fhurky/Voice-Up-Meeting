# PRD — Mikrofonla temiz profil kaydı

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [017 — microphone-profile-enrollment](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak (29 Ekim 2026): Kullanıcının seçtiği doğruluk odağının temiz profil kaydı
bileşenidir; [016](../016-meeting-participant-roster/PRD.md) katılımcı listesinin
seçeceği profillerin kalitesini artırır.
Kabul (29 Ekim 2026): Kullanıcı 015, 016 ve 017 taslaklarını kabul etti ve 015 ile başlanmasını istedi.

## Amaç ve gerekçe

Depodaki ölçümler, kontrollü temiz kayıtla oluşturulan galerinin toplantıdan otomatik
oluşturulan profillerden belirgin biçimde daha doğru olduğunu gösterir: kontrollü
galeride 100 bilinen sorgunun 95'i doğru ve yanlış kimlik yok; tam toplantı
zincirinde geri dönen 50 kişinin 35'i doğru. Bugün temiz profil yalnız hazır dosya
yüklenerek oluşturulabilir. Kullanıcı, Konuşmacılar ekranında kişiyi doğrudan
mikrofonla, yönlendirmeli ve kalite geri bildirimli kaydedebilmelidir.

## Kararlar

Decision 1: 007'nin `AudioWorklet` + OPFS PCM16 WAV yakalaması yeniden kullanılır.
Kayıt mevcut 001 akışına (`POST /recordings`, ardından `POST /speaker-jobs`
`purpose=enroll`) gider; API, kalite kuralları, 120 saniye ve 50 MiB sınırları değişmez.

Decision 2: Kayıt ekranı kullanıcıya 45–60 saniyelik yönlendirme verir: ekranda
okunacak doğal bir Türkçe (İngilizce arayüzde İngilizce) paragraf, ardından birkaç
saniyelik serbest konuşma. Süre sayacı ve seviye göstergesi görünür. 120 saniyede
kayıt otomatik durur.

Decision 3: Sonuç açıkça gösterilir: profil oluştu, yetersiz konuşma, tutarsız ses,
kırpılma veya sessizlik. Başarısız kayıtta neden ve yeniden deneme yolu verilir; aynı
kişiye mevcut kurallarla ikinci örnek eklenebilir (en çok 20).

Decision 4: Mikrofon izni, güvenli bağlam ve OPFS desteği 007'deki gibi denetlenir;
desteklenmeyen tarayıcıda dosya yükleme yolu açık kalır.

## Gereksinimler

Requirement 1: Konuşmacılar ekranına mikrofonla kayıt kaynağı; yeni profil ve mevcut
profile örnek ekleme akışları.

Requirement 2: TR/EN yönlendirme metni ve bütün durum/hata mesajları katalogda; tam
klavye erişimi.

Requirement 3: Birim testleri (durum makinesi, sınırlar, hata eşlemesi) ve kalıcı
tarayıcı senaryosu; canlı mikrofon kanıtı 007'deki gibi ayrı işaretlenir.

Requirement 4: 015/016 hattında temiz kayıtlı galeri ile toplantıdan otomatik galeri
karşılaştırması `results.md` içine kaydedilir.

## Katmanlar

Backend, API, şema ve migration: N/A — mevcut 001 sözleşmesi kullanılır. Vektör
sözleşmesi: N/A — ECAPA 192 ve eşikler değişmez. Worker: mevcut. Kubernetes: N/A.
Ses dosyası saklama ve silme kuralları 001'dir.

## Kabul ölçütleri

- [ ] Mikrofonla yeni profil ve örnek ekleme gerçek tarayıcıda TR/EN çalışır; hatalar anlaşılır biçimde gösterilir.
- [ ] Frontend birim testleri ve tarayıcı senaryosu geçer; tam kalite kapısı geçer.
- [ ] Temiz kayıtlı galerinin etkisi 015 protokolüyle ölçülüp kaydedilir.

Open Question 1: Temiz kayıtla oluşan profiller yalnız ECAPA 192 vektörü taşır;
toplantıda 256 boyutlu Community-1 popülasyonunda aranmazlar. Kayıt sırasında 256
boyutlu toplantı vektörü de üretmek, ayrı bir çıkarım ve şema kararı gerektirir.
015 ölçümü bu eksikliğin etkisini gösterdikten sonra karar verilir.
