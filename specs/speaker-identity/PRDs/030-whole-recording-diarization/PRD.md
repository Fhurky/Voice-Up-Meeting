# PRD — Tüm kayıtta tek geçişte konuşmacı ayırma

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [030 — whole-recording-diarization](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak (17 Kasım 2026): Kullanıcı, ortalama 7–8 ve en çok 15 kişilik Teams toplantılarında en yüksek doğruluk için
[rotanın](../../../../plans/TEAMS_MEETING_ACCURACY_ROUTE.md) uygulanmasını istedi ve bu taslağı aynı gün kabul etti. Bu PRD
rotanın Adım 1'idir. Ölçülmüş
gerekçe rotanın Ek A'sındadır. [021](../021-meeting-speaker-reconciliation/PRD.md) parça izi birleştirmesi yeni akışta
çalışmaz; geri dönüş yolunda korunur.

## Amaç ve önceki durum

Bugün konuşmacı ayırma modeli (`pyannote/speaker-diarization-community-1`) kaydı 5 dakikalık parçalarda, kendi
varsayılanından farklı bir ayarla (`community-vbx-fa015-v1`, `Fa` 0,15) çalıştırır. Parça izleri toplantı sonunda
vektör benzerliğiyle birleştirilir (021). 17 Kasım ölçümünde aynı model, modelin kendi ayarıyla tüm kaydı tek geçişte
işleyince AMI test kümesinde (16 toplantı) DER uzak mikrofonda %27,56'dan %19,90'a, yakın mikrofonda %22,43'ten
%17,05'e indi. Tek geçiş 16 toplantının 16'sında daha iyiydi; kazanım konuşmacı karışmasındaydı. İki gerçek Türkçe
toplantıda tam 11 ve tam 4 konuşmacı buldu; ürün 15 ve 7 bulmuştu. Bu sayılar modelin tek başına ölçümüdür.

Hedef: ürün akışı bu kazanımı yükleme, API, metin satırları ve kişi hafızasıyla birlikte göstersin.

## Kararlar

Decision 1: Yükleme tamamlanan toplantıda worker, parçalara başlamadan önce tüm kaydı bir kez konuşmacılara ayırtır.
Tarif modelin kendi ayarıdır ve sürümlü adla kaydedilir: `community-default-whole-v1` (eşik 0,6, `Fa` 0,07, `Fb` 0,8,
`min_duration_off` 0). Katılımcı üst sınırı `max_speakers` olarak gider; kesin kişi sayısı zorlanmaz, tahmini kişi
sayısı modele gitmez (022 ile aynı).

Decision 2: Tek geçişin ürettiği her konuşmacı için hemen bir toplantı konuşmacısı satırı oluşturulur. Numaralar ilk
konuşma anına göre verilir. Konuşmacının 256 boyutlu vektörü mevcut `meeting_speaker.tracking_embedding` sütununa
model kimliğiyle yazılır; model etiketi satırın `props` alanında `diarization_label` olarak saklanır.

Decision 3: Konuşmacı aralıkları (normal ve örtüşmesiz) toplantıya ait yeni `meeting_diarization` tablosunda saklanır:
toplantı başına bir kayıt; tarif, model kimliği, kaynak ses özeti, konuşmacı sayısı ve aralıklar. Kayıt toplantının
içine ait bir yan tablodur, dışa açılmaz; bu yüzden `public_id` taşımaz (41 numaralı kuraldaki yan tablo istisnası,
şema testinde doğrulanır). Saklama ve silme toplantıyla aynıdır. Genel API ve OpenAPI değişmez.

Decision 4: Parçalar yazıya çevirme ve ses kanıtı için sürer, ama kendi ayırmasını yapmaz. Worker, parça penceresine
düşen toplantı düzeyi aralıkları istekle gönderir; çıkarım servisi bu aralıklarla kanıt üretir ve aynı etiketleri
döndürür. Yeni bir çıkarım uç noktası kullanılır; bugünkü parça uç noktası geri dönüş için aynen kalır.

Decision 5: Arka uç parça izini etiketine göre toplantı konuşmacısına bağlar. Parçalar arası akustik eşleme ve toplantı
sonu birleştirme (021) bu yolda çalışmaz. Kelime–konuşmacı eşlemesi, parça sınırında metin dikişi, satır gruplama
(026), kişi hafızası, katılımcı listesi (016) ve 10 saniye kuralı değişmez.

Decision 6: Geri dönüş: CPU modu, ölçülen süre sınırını aşan kayıt ve iki denemede de başarısız olan tek geçiş bugünkü
parçalı akışı kullanır. Neden toplantı kaydında tutulur ve günlüğe yazılır; ekranda gösterilmez. Süre sınırı 120 dakikadır
(Requirement 6a ölçümü: 120 dakika 235 saniye ve 4,3 GiB; 240 dakika 498 saniye ve 6,6 GiB). 240 dakika kurum dağıtımının 8 GiB
sınırına sığar, ancak 7,35 GB'lık yerel Docker belleğine yığınla birlikte sığmaz; sınır bu yüzden 120 dakikadır.

Decision 7: Akış toplantı işleme başlarken seçilir ve o toplantı boyunca değişmez. Bu sürümden önce işlenmiş
toplantılar yeniden işlenmez; sonuçları olduğu gibi kalır.

Decision 8: Ön yüz değişmez; tek geçiş sırasında toplantı bugünkü gibi "işleniyor" görünür.

## Gereksinimler

Requirement 1: Çıkarım servisi: tüm kaydı (16 kHz tek kanal PCM16 WAV) alan, süre ve boyut sınırlı, yetkili yeni uç
nokta; tarif ve model kimliği, aralık ve vektör doğrulaması; meşgul, hazır değil, bozuk girdi ve sınır testleri.

Requirement 2: Çıkarım servisi: ses penceresi ve toplantı düzeyi aralıklarla çağrılan parça uç noktası; ayırma modelini
çağırmaz, verilen etiketlerle kanıt üretir; mevcut parça sonucu sözleşmesini yeni tarif kimliğiyle döndürür; testler.

Requirement 3: Arka uç: `meeting_diarization` şeması ve gözden geçirilmiş Alembic migrasyonu; depo işlemleri; worker'da
tek geçiş adımı, akış seçimi ve geri dönüş; adaptör sözleşme doğrulaması; etiketle konuşmacı bağlama; birleştirmenin
atlanması; toplantı silme ve saklama süresi temizliği. Birim ve canlı PostgreSQL entegrasyon testleri; kiracı yalıtımı.

Requirement 4: Ses: kaydı 16 kHz tek kanala sınırlı bellekle dönüştüren okuyucu ve testleri.

Requirement 5: Gözlemlenebilirlik: worker günlüğünde `meeting_diarization` olayı; akış (`whole` ya da `chunked`), geri
dönüş nedeni, süre ve konuşmacı sayısı. Kişi, kiracı ve içerik bilgisi yazılmaz.

Requirement 6: Ölçüm: (a) çıkarım servisinin kendi sürecinde 90, 120 ve 240 dakikalık kayıtlarda süre ve en yüksek
bellek; süre sınırı buna göre kesinleşir ve dağıtım belleği (chart `app-inference`, sınır 8 GiB) bununla karşılaştırılır;
(b) AMI test kümesinde iki koşulda ürün akışıyla DER; (c) AMI uzak mikrofon, rotasyon 2, 34 toplantıda kişi tanıma;
(d) iki gerçek Türkçe toplantıda konuşmacı sayısı. Toplu sonuçlar `results.md`'ye yazılır.

## Katmanlar

Şema: yeni `meeting_diarization` tablosu ve migrasyon (Requirement 3). Vektör: yeni vektör sütunu yok; mevcut
`tracking_embedding` aynı model kimliğiyle kullanılır. API ve OpenAPI: N/A — genel sözleşme değişmez; değişen
uç noktalar yalnız iç çıkarım servisindedir. Ön yüz: N/A — Decision 8. Gözlemlenebilirlik: Requirement 5. Dağıtım:
inference bellek sınırı Requirement 6(a) ölçümüyle doğrulanır; değişiklik gerekirse aynı işte yapılır.

## Kabul ölçütleri

- [ ] Birim, entegrasyon ve tam kalite kapısı geçer.
- [ ] AMI test kümesinde ürün akışıyla (API'den okunan `speaker-turns`) DER uzak mikrofonda %21'in, yakın mikrofonda
      %18'in altındadır (collar 0).
- [ ] AMI uzak mikrofon, rotasyon 2: yanlış kişi en çok 1/46, yabancıyı tanıdık sanma 0, tanınan en az 33/46
      (bugünkü `eval-ami4-array1-r2`).
- [ ] İki gerçek Türkçe toplantıda 11 ve 4 konuşmacı bulunur.
- [ ] Mevcut MP4 toplantı senaryosu (`16-meeting-mp4-upload.mjs`) canlı uygulamada geçer.
- [ ] Kullanıcı gerçek bir toplantıda sonucu kabul eder (L3).
