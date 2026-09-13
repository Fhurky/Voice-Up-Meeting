# PRD — Türkçe değerlendirme ve deney günlüğü

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [009](../../roadmap.md)
Sabit profil: `kt-vibecoding-python-web-v2`.
Kabul kaydı: 13 Eylül 2026 kullanıcı isteği, her denemenin önceden belirlenen
doğruluk skorlarını kökte `results.md` içinde kaydetmeyi, Türkçe veri setlerini
kapsamlı araştırmayı ve uygulamayı Türkçe toplantılar için geliştirmeyi yetkilendirir.

## Amaç, aktörler ve sınır

Geliştirici ve değerlendirme sorumlusu doğrulanmış kaynaklardan tekrar üretilebilir
Türkçe deneyler çalıştırır, başarılı/başarısız bütün denemeleri aynı günlükte görür.
Konuşmayı metne çevirme, toplantı içi konuşmacı ayırma ve kayıtlar arası kalıcı
kimlik başarısı ayrı görevlerdir; birinin skoru diğerinin yerine geçmez.
Yaklaşık 50 kişi hedefi korunur, veri setinin gerçek kişi sayısı gizlenmez.

## Kararlar

Decision 1: Sabit FastAPI/React/PostgreSQL ve mevcut yerel model HTTP sınırları
korunur. Veri hazırlama çevrimdışı çalışmanın öncesinde açık bir işlemdir; model
servisine internet erişimi, yeni model indirme veya başka veritabanı eklenmez.

Decision 2: `results.md` her deneyin kök günlüğüdür. Açık deney kimliği, zaman,
veri sürümü/dili/protokolü, kalibrasyon veya test rolü, kaynak/ayar/model sürümleri,
planlı ve gözlenen kapsam, tamamlanma durumu ve uygun metrikler kaydedilir.
Eksik referans veya tamamlanmamış deney skoru sıfır/başarı gibi gösterilmez.
Aynı deneyin aynı sonucu tekrar kaydetmek çift satır üretmez; değişen terminal
veya devam durumu aynı deney kimliği altında ayrı, açık sürüm olarak korunur.
Yazma kilitli/atomik olur; mevcut deneyler ve elle yazılmış açıklamalar korunur.

Decision 3: Günlüğe yalnız izin verilen toplu alanlar yazılır. Token, parola,
ham ses/metin, kişi adı/kimliği, tenant, özel mutlak dosya yolu ve serbest hata
içeriği yayımlanmaz. Makine çıktısı toplu kanıta bağlanır. Geçmiş sonuçlar
yeniden kör test diye adlandırılmaz; kalibrasyon, reddedilen aday ve başarısız
denemeler seçilerek gizlenmez. Tekrar kullanılan sorgular bağımsız örnek sayılmaz.

Decision 4: Mevcut kimlik precision/recall/micro ve macro F1, bilinmeyen kişi F1,
VoiceUp Score, kapsam ve yanlış kabul tanımları değişmez. `cpWER` ve belirsiz
akışı ayrı cezalandıran metin skoru yalnız uygun referans varsa hesaplanır.
İngilizce LibriSpeech protokolüne Türkçe dosya/kimlik etiketi takılmaz; Türkçe
verinin kaynağına uygun ayrı adaptör/protokol kullanılır.

Decision 5: Eski `unicode-words-v1` ve tarihsel çıktıları korunur. Açık seçilen
sürümlü Türkçe normalizasyonu `I→ı`, `İ→i`, kanonik birleşik/ayrık Unicode ve
Türkçe harf ayrımlarını korur. Bu ölçüm düzeltmesi akustik model iyileşmesi
diye sunulmaz; karşılaştırılan sonuçların normalizasyonu belirtilir.

Decision 6: Kaynaklı araştırma, büyüklükten ayrı olarak konuşmacı etiketi,
oturum tekrarı, doğal diyalog/örtüşme, referans kalitesi, lisans ve erişimi
karşılaştırır. İnsan konuşması ile sentetik ses ve birleştirilmiş toplantılar
ayrılır. FLEURS benzeri kalıcı kişi kimliği olmayan kaynak ASR ölçebilir,
kimlik hafızası ölçemez. Otomatik VAD/metin kesin insan referansı sayılmaz.

Decision 7: İlk uygulanacak hazırlama, kaynak bütünlüğü doğrulanmış Türkçe
altyazı/ses veya konuşmacı kanallarıyla sınırlı ve yeniden üretilebilirdir.
İndirilen revision, dosya hashleri, seçim ve dışlama nedenleri kaydedilir;
ses/veri paketleri Git'e eklenmez. Kalibrasyon ile test kaynakları açık ayrılır;
aynı ses parçası hem kayıt hem sorgu olamaz. Resmî oturum kimliği yoksa farklı
klipler farklı oturum diye adlandırılmaz. Kaynak erişimi engelliyse engel açık
kaydedilir ve erişilebilen uygun Türkçe kaynakla bağımsız iş sürdürülür.

Decision 8: Gerçek yerel model taban çizgisi önce ölçülür. Bir çıkarım/kimlik
değişikliği ancak eşleştirilmiş geliştirme verisinde gerekçelendirilen kazançla
ve regresyonlarıyla benimsenir; ölçüm belirsizliği model eşiğini gevşetme nedeni
değildir. Ayrılmış test sonradan ayar seçimine katılırsa test rolü değiştirilir.

## Gereksinimler

Decision 9: İlk kaynak seçimi Real-TurnTurk revision
`db8f20f6eb6b215ec75fb466374fc5cc861b91df` ve MediaSpeech Türkçe resmî
`TR.tgz` arşividir. Gerçek altı görüşmenin ilk 180 saniyesi zamanları korunarak
karıştırılır; ilk altı kişi görünümü yeni, sonraki altı görünüm bilinen sorgudur.
Başarısız ilk kayıt, sonraki bilinen sorguyu planlı paydadan çıkarmaz. Otomatik
etkinlik referansındaki örtüşme kişi eşlemesine çift oy vermez. Bu zincirin
skorları zayıf referanslı tanılayıcı sonuçtur. MediaSpeech arşivindeki klipler
`voiceup-mediaspeech-tr-v1` tohumu ve dosya kimliğinin SHA-256 sırasıyla 40
geliştirme + 40 ayrılmış test klibine seçilir; bu ayrım kişi/oturum bağımsızlığı
iddiası taşımaz. Mevcut Whisper ayarlarıyla sabit `tr` taban çizgisi ve otomatik
dil adayı yalnız aynı geliştirme kliplerinde karşılaştırılır; ayrılmış test
aday seçimi için kullanılmaz. Klip başına metin hataları toplam kelime sayısıyla
ağırlıklandırılır, klipler farklı kişiler varsayılarak birbirine eşlenmez.

Decision 10: Real-TurnTurk kaynak incelemesinde rec01 kanallarında tekrarlanan ve
sıçrayan WebM zaman damgaları, rec03 sol kanalında milisaniyelik oynamalar
gözlendi. Hazırlama `decoded-sample-clock-v1` politikasıyla çözülen örnekleri
kendi sırasıyla, ilk örnekten başlayan 16 kHz zaman çizelgesinde tutar; damga
kusurları nedeniyle konuşma/sessizlik atılmaz, üst üste yazılmaz veya eklenmez.
İlk 180 saniyelik seçim ve iki kanalın sabit yarım kazançla karışımı korunur.
Kaynak damga sapmaları ve tüm çözülen kanalın süresi, VAD/metin sonlarıyla
karşılaştırılarak özel manifestte kaydedilir. Kaynağın kesin çözme yöntemi
belgelenmediğinden `unverified-source-timestamps` niteliği zorunludur; referans
hizası doğrulandı ve insan denetimli DER elde edildi iddiası yapılmaz. Politika
seçimi model skorlarına göre yapılmaz; zamanlama kusuru ve politika test edilir.

Decision 11: İlk altı görüşmelik tanısal taban çizgisinde rec03'te ek sıfır
saniyelik küme ile `reconciliation_ambiguous`, rec06'da üç kümeye bölünme ve
yetersiz baskın eşleme görüldü. Aynı altı sabit kalibrasyon kaydı, ayrı ve boş
deney tenantında açık `--use-known-speaker-count` adayıyla yeniden çalıştırılır;
mevcut API'ye hem `expected_speakers=2` hem `participant_count=2` gönderilir.
Bu bilgi iki kişilik kaynak görüşmelerinden bilinen meşru girdidir; model
ağırlıkları, kimlik eşikleri, metin ayarı, kaynaklar ve ölçüm politikası değişmez.
Seçenek varsayılan olarak kapalıdır, durum dosyasına dondurulur ve devam
işleminde değiştirilemez. rec02'deki 10,893 saniyelik yetersiz temiz kanıt
nedeniyle 20 saniyeyi aşma kapısı gevşetilmez. Adayın kazancı veya gerilemesi
bütün altı kaydın aynı planlı paydalarıyla kaydedilir; kalibrasyon deneyi
bağımsız test veya bilinen sayıyla otomatik başarı garantisi sayılmaz.
İlk görünümde başarılı kayıt oranı `first_enrollment_coverage`, deney sonunda
biriken kayıt oranından ayrı gösterilir. Eski `enrollment_coverage` alanının
anlamı son birikimli kapsam olarak korunur; eski kanıt sessizce değiştirilmez.

Requirement 1: Standart değerlendirme komutları veya ortak deney yürütücüsü,
geçerli toplu sonuçları `results.md` günlüğüne otomatik ekler. Tek komutla açık
deney kimliği ve kanıtın yeniden kaydı desteklenir; hata/eksik durumlar görünürdür.

Requirement 2: Günlük kimlik, metin ve toplantı hafızası kapsamını ve ölçülmeyen
alanları açık gösterir. Güvenilir geçmiş skorlar kaynaklarıyla başlangıç
deneyleri olarak aktarılır; sayısız eski günlüklerden skor uydurulmaz.

Requirement 3: Türkçe veri araştırması bağımsız okunabilen kaynaklı Markdown
raporunda saklanır. Seçilen kaynağın hazırlanması, yerel çalıştırılması ve
etiketlerinin sınırı kullanım belgesinde açıklanır.

Requirement 4: Türkçe normalizasyon ve veri adaptörleri gerçek dosya sınırlarıyla
sınanır. En az erişilebilen Türkçe kaynakta gerçek model denemesi ve mevcut
referansların izin verdiği skorlar kaydedilir; insan doğruluğu, kalıcı kişi veya
50 kişi başarısı eksik etiketlerden çıkarılmaz.

## Veri, API, güvenlik, gözlem ve dağıtım

Şema/migrasyon N/A — deneyler geliştirme artefaktıdır, uygulama iş verisi ve
profil otoritesi mevcut 001/002'de kalır. API/OpenAPI/UI N/A — yeni ürün ekranı
veya uç eklenmez; mevcut gerçek HTTP işlemleri ve izinleri kullanılır.
İşçi/önbellek/yeni ayar N/A — ayrı sürekli süreç veya runtime yapılandırması
gerektirilmez. Dağıtım N/A — yerel hazırlama/değerlendirme araçları model ağ
sınırını veya chart davranışını değiştirmez; tam profil kapısı yine çalışır.
Toplu günlük anonimdir; özel manifest/çıktı dosyaları yok sayılan yerel dizinde
tutulur. Deney hesabı kendi tenant/yetkileriyle gerçek giriş yapar; veri silme
yalnız deneye ait açık sahiplik doğrulamasıyla mevcut API üzerinden yapılır.
Bağımlılık değişikliği N/A — mevcut Python standart kitaplığı ve kabul edilmiş
ses araçları kullanılır; yeni gereksinim doğarsa kabul ayrıca kaydedilir.
Gözlemlenebilirlik kanıt hashleri, durum, kapsam, süre ve toplu hata kodlarıdır;
gerçek ses/metin ve kimlik özellikleri loglanmaz.

## Test ve kabul

- [x] Atomik, yinelenmeyen ve gizli veri taşımayan günlüğün başarı/hata/eksik/devam davranışları gerçek dosyada geçer; 35 günlük testi son birleşik koşuma dahildir.
- [x] Eski metrikler değişmeden, Türkçe normalizasyonu sürümlü seçenek ve 53 ilgili regresyonla çalışır.
- [x] Birincil kaynaklı Türkçe veri karşılaştırması, erişim/lisans/etiket sınırları ve seçimin gerekçesi araştırma ve kullanım belgelerinde yayımlandı.
- [x] İki Türkçe kaynak hazırlandı; 3 gerçek ASR + 2 gerçek toplantı/hafıza deneyi ve uygun skorlar `results.md` içine yazıldı.
- [x] Son dar 389 + tam profil 738 test geçti; güvenlik kapısının araç eksiği dahil çalışmayan cihaz/veri/etiket koşulları ayrı açık kaydedildi.

Kanıt: [Koşum raporu](../../../../docs/evidence/2026-09-13-turkish-evaluation/README.md).

Open Question 1: Açık veride 50 farklı kişinin doğal ve tekrar eden Türkçe
toplantı konuşması yeterli değilse bu hedef sınırlı paketle tamamlandı sayılmaz.
