# PRD — 4060 üzerinde yerel konuşmacı pilotu

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [001 — local-speaker-pilot](../../roadmap.md)
Hazırlanma tarihi: 8 Eylül 2026
Kabul kaydı (8 Eylül 2026): Bu belgedeki ilk sürüm kapsamı kullanıcıya sunulup kabulü sorulduktan sonra kullanıcı “sıradaki adım nedir ona geç” diyerek uygulamaya devam edilmesini istedi. Bu yanıt kapsamın kabulü olarak kaydedildi; kabul, testlerin veya kalite hedeflerinin tamamlandığı anlamına gelmez.

## Amaç

Kullanıcı tarayıcıdan bir kişiye ait temiz ses örneğiyle kalıcı profil oluşturur,
farklı bir kayıttaki sesi bu profillerle karşılaştırır ve analiz durumunu/sonucunu görür.
İlk çalışma cihazı RTX 4060 Laptop 8 GB'dır. Aynı web/API sözleşmesi daha sonra Spark
çıkarım ortamıyla kullanılabilir. Bu belge yeni ürün özelliğini tanımlar; mevcut
`src/voiceup/` araştırma kodunun varlığı platform entegrasyonunun tamamlandığı anlamına gelmez.

## Aktörler ve sonuçlar

- Yetkili pilot kullanıcısı: kendi tenant'ında profil oluşturur, yeni örnek ekler,
  tek konuşmacılı kaydı tanıtır ve sonuçları inceler.
- Yerel yönetici: mevcut platform kullanıcı/tenant/yetki mekanizmasını ve model
  çalışma durumunu yönetir; başka uygulamaların servis veya verisini değiştirmez.
- Analiz yürütücüsü: kalıcı iş kaydını sahiplenir, yerel çıkarım adaptörünü çağırır ve
  tek terminal sonuç üretir. Web isteği model yüklenmesini veya çıkarımı beklemez.

## Kararlar ve sınırlar

Decision 1: Sabit ürün yapısı Python 3.13/FastAPI, React/Vite SPA, PostgreSQL 17,
SQLAlchemy/Alembic olarak kalır. Kök SQLite prototipi ürün veritabanı yapılmaz.

Decision 2: İlk pilot yalnız **tek konuşmacılı WAV/FLAC** örnekler kabul eder. Kullanıcı
bu niteliği ekranda açıkça görür. VAD kişileri birbirinden ayırmaz; birden fazla kişinin
karıştığı dosyada doğruluk iddiası yapılmaz. Otomatik toplantı bölümleme, ASR, canlı
mikrofon ve toplantı platformu bağlantısı bu PRD'nin kabul kapsamına dahil değildir.

Decision 3: Mevcut ECAPA modeli referans alınır; ağır alternatifler Spark karşılaştırma
planında kalır. Yeni kişi, kullanıcı tarafından profil oluşturma akışıyla eklenir.
`identify` kararı mevcut profilleri değiştirmez ve kendi kendine yeni kişi oluşturmaz.
Otomatik yeni konuşmacı kaydı, karışık toplantı yeteneğinde ayrıca tanımlanacaktır.

Decision 4: 4060'ta aynı anda bir GPU işi ve bir model örneği kullanılır. Web backend'inin
Alpine image'ına PyTorch kurulmaz; Python 3.13 ile uyumluluğu doğrulanmış ayrı CUDA/Linux
çıkarım ortamı ve iç HTTP adaptörü kullanılır. Cihaz veya model hazır değilse açık hata
üretilir; sessizce sahte sonuç veya CPU'ya geçiş olmaz. CPU, yalnız açıkça seçilmiş
karşılaştırma modu olabilir.

Decision 5: Yerel giriş adresi için `127.0.0.1:8081` hedeflenir; başlamadan boşluğu
kontrol edilir. 8080'deki mevcut uygulama korunur. Spark'a geçişte API ve iş kaydı
sözleşmesi korunarak image/mimari/cihaz ayarları değişir; uyum cihazda doğrulanır.

## İşlevsel gereksinimler

Decision 6 (9 Eylül 2026): Kullanıcının veri seti bulup uygulamayı kapsamlı test etme
isteğiyle, T09 kapsamında açık lisanslı ve konuşmacı etiketli kamu verisinde ayrı bir
Spark doğruluk deneyi uygulanır. LibriSpeech İngilizce okuma verisi Türkçe doğal
toplantı veya farklı gün/mikrofon kabulü sayılmaz. Veri seçimi, kaynak bölüm ayrımı,
kalibrasyon/test kişi ayrımı, sabit eşikler, başarısız işlerin de paydada tutulması ve
deneyin ayrı tenant'larda çalışması sonuç görülmeden kaydedilir. Veri ve kimlik
eşleştirmeleri Git dışında tutulur; rapor anonim toplu ölçümler taşır. Bu karar
002/003 kapsamını veya mevcut kalite sınırlarını değiştirmez.

Decision 7 (9 Eylül 2026): Decision 6 kalibrasyon havuzundaki 50 planlı kişinin
40'ı mevcut kalite kurallarıyla kaydedilebilir bulundu. Aynı Spark çıkarım yoluyla
150 bilinen ve 100 bilinmeyen sorguda, 0.50–0.75 aralığında 0.05 adımlı kabul
eşikleri karşılaştırıldı. Sıfır gözlenen bilinmeyen yanlış kabul altında en yüksek
doğru kabulü veren eşiklerin en yükseği 0.55 seçildi: 109/150 bilinen doğru kabul,
0/100 gözlenen bilinmeyen yanlış kabul; 9 bilinmeyen kalite hatası ayrıca tutuldu.
0.50 iki bilinmeyeni yanlış kabul etti; 0.75 yalnız 50/150 bilinen sorguyu kabul
etti. Ürünün pilot kabul eşiği 0.55 olur; bilinmeyen eşiği 0.45, aday farkı 0.10
ve ses kalite kuralları korunur. Bu, İngilizce kamu verisine dayalı geçici pilot
kalibrasyonudur; Türkçe veya üretim garantisi değildir. Kör test bu seçimden sonra
ayrı kişilerle gerçek uygulama üzerinden çalışır. Kör sonuçlara bakıp aynı deneyi
geçirmek için yeniden ayar yapılmaz. Eski sonuçlar kendi kaydedilmiş eşiklerini korur.

Decision 8 (9 Eylül 2026): Kullanıcının önceki kalite raporundan sonra “Sıradaki
yapmamız gereken her ne ise yapalım” talimatı, kısa konuşma bölgelerinin kaybını
iyileştirme ve ayrı veriyle doğrulama çalışmasının kabulüdür. Önce yalnız mevcut
kalibrasyon kişilerinde iki sabit aday karşılaştırılır: konuşma bölgelerini zaman
sırasıyla birleştirme ve bunu yalnız yetersiz konuşma sonucunda kullanma. Ürüne
geçiş adayı ikinci, sınırlı kurtarma yoludur: eski yol amaca yeterli kullanılabilir
sonuç veriyorsa aynı sonuç korunur; eski tutarsızlık reddi korunur. Yalnız kalan
yetersiz konuşma durumunda VAD'nin bulduğu gerçek örnekler bir kez, sıraları
korunarak birleştirilir ve mevcut 3–8 saniyelik bağımsız pencerelere ayrılır.
Sessizlik eklenmez, örnek tekrarlanmaz, başka kişinin sesi eklenmez. RMS/kırpılma,
0.55 pencere tutarlılığı, 10 saniye/iki pencere kayıt ve üç saniye sorgu sınırları
korunur. Mevcut kısmi ses vektörü varsa kurtarılan vektörle tutarlılığı ayrıca aranır.

İlk iki aday kalibrasyondaki aralıklı iki kişi kontrolünde kötüleştiği için
reddedildi. Bu bulgu sonrası dondurulan korumalı aday, birleştirmeye yalnız en az
1.5 saniyelik özgün bölgeleri alır; daha kısa bölgeler süreye katılmaz. Her özgün
blok ayrı ses vektörüyle denetlenir: tüm blok çiftleri ve her bloğun birleştirilmiş
sonuçla benzerliği en az 0.55 olmalıdır. Bu kısa vektörler yalnız karışım reddi
içindir; profil kanıtı yine 3–8 saniyelik pencerelerden üretilir. Süre, örnek
sırası, blok başına RMS/kırpılma ve eski sonuçları koruma koşulları değişmez.
Kalibrasyon tanısının yeni protokolü puanlardan önce ayrı dosyada sabitlenir.

Geçiş ön koşulları kalibrasyonda eski 40/50 kayıt veya 109/150 doğru tanımanın
iyileşmesi, doğru tanımanın azalmaması, yanlış kişi/bilinmeyen kabulünün artmaması,
eski kabul edilmiş profillerle uyum ve önceden seçilen karışık/yanlış kişi
kontrollerinde kötüleşme olmamasıdır. Bu koşullar sağlanmadan çalışma zamanı
değiştirilmez. Kabul eşikleri 0.55/0.45/0.10 sabit kalır; bu turda yeni model
ağırlığı veya bağımlılık sürümü seçilmez. Eski profil ve sesler yeniden yazılmaz.
Aynı sabit ağırlıklar ve vektör uzayı korunur; kurtarma yolunun sürümü ve kullanımı
çıkarım/iş sonucunda izlenebilir olmalıdır. Tek sınırlı `preprocessing_version`
alanı gerçek kullanılan yolu belirtir; eski işlerde bilinmeyen sürüm `null` kalır.
Bu alan mevcut yedi günlük iş saklama süresine tabidir; kalıcı örnek seviyesinde
provenans iddiası yapılmaz. Anonim koşum/kaynak/imaj manifestleri sürüm kanıtını
ayrıca korur. API ve üretilen tipler güncellenir; kullanıcı akışı değişmediği için
ek teknik arayüz alanı gerekmez. Bir model değişikliği gerekirse ayrı
sürümlü popülasyon ve geçiş planı gerekir; bu düzeltme o yetkiyi vermez.

Önceden ölçülmüş test kişileri artık tarihsel regresyon verisidir. Sonuç seçiminde
kullanılmamış, önceki tüm gelişim/test kişilerinden ayrık yeni açık veri havuzu
hazırlanır; seçim konuşmacı kimliği/kaynak bölümüne dayanır, model puanına dayanmaz.
Yeni politika/kod dondurulduktan sonra 50 kayıt adayı ve 20 bilinmeyen kişiyle,
başarısız işler dahil tüm paydalar üzerinden gerçek uygulama doğrulaması yapılır.
Yeni veri yalnız temiz İngilizce okuma verisiyse kapsam bu adla raporlanır; eski
daha zor havuzla doğrudan başarı yarışı yapılmaz. Lisans/provenans, ses hashleri,
ayrık bölümler, yeni kişinin kayıt/geri dönüşü, yanlış profile ekleme ve gecikme
kaydedilir. Türkçe toplantı kabulü ve 002/003 kapsamı değişmez.

Decision 9 (9 Eylül 2026): Kullanıcının kendi precision, recall ve F1 ölçülerini
oluşturma talimatı, mevcut pilotun çevrimdışı değerlendirme protokolünü genişletir.
`voiceup-open-set-v1` protokolü kimlik precision/recall/micro F1, konuşmacı başına
eşit ağırlıklı macro F1 ve bilinmeyen sınıfı precision/recall/F1 üretir. Ürüne özgü
`VoiceUp Score`, kimlik macro F1 ile bilinmeyen F1'in eşit ağırlıklı harmonik
ortalamasının 100 katıdır; standart F1 veya yüzde doğruluk olarak adlandırılmaz.
İlk kayıt kapsamı ayrıca gösterilir; başarısız kaydedilen kişilerin sorguları
bilinen kişi paydasında kalır. Profil kaybı skorda zaten etkili olduğundan kayıt
oranıyla tekrar çarpılmaz. Yanlış kimlik, doğru kişi için kaçırma ve atanan kişi
için yanlış kabul sayılır. Belirsiz ve hatalı işler bilinmeyeni doğru bulma sayılmaz.

Planlı manifest ile kaynak raporun canonical SHA-256 bağı doğrulanır. Aynı sorgu
tekrar sayılmaz; kişi/rol/aşama uyuşmazlığı, beklenmeyen kayıt veya bozuk terminal
karar reddedilir. Eksik/bekleyen planlı işlemler varken tamamlanmış skor verilmez;
eksikler görünür sayılır. Kaynak koşucunun son galeri doğrulaması dahil hatasız
`complete` sonucu ayrıca gerekir; tüm işler bitmiş olsa bile koşucu hatası skoru
geçersiz kılar. Sıfır paydalı precision/recall `null` olur; desteklenen
sınıfta sıfır doğru sonuç F1=0'dır. Yeni kişinin kayıt ve geri dönüşü ana galeriden
ayrı raporlanır; iç içe galeriler tek büyük deneye toplanmaz.

Bu tanım daha önce görülen veriye sonradan uygulanacaktır; yeni kör deney veya
model iyileştirmesi iddiası değildir. Eşik, model, eski kanıtlar ve önceki kabul
kriterleri değişmez; puanları gördükten sonra geçme sınırı türetilmez. Kesin
formüller, paydalar ve örnekler [ölçüm protokolündedir](../../../../docs/SPEAKER_METRICS.md).
Değişiklik yalnız mevcut raporlama aracı, testler ve anonim dosya çıktılarıdır.
API/arayüz/veritabanı/işçi/yapılandırma/dağıtım değişikliği: N/A — çevrimdışı
raporlanan ölçüler ürün akışına veya veri saklama biçimine eklenmez. Bağımlılık
eklenmez; dosya sınırları, üzerine yazmama ve hassas kimliklerin yayımlanmaması
korunur. Kırmızı/yeşil sınır testleri, eski rapor uyumu, aynı girdiden deterministik
hesap ve üç mevcut veri grubunun bağımsız kontrolü ile tam profil kapısı kaydedilir.

Decision 10 (10 Eylül 2026): Kullanıcının en fazla 50 farklı kişinin tanınacağı
talimatıyla her tenant/çalışma alanı en fazla **50 aktif konuşmacı profili** tutar.
Bu karar aynı gün gelen kullanıcı açıklamasıyla Decision 11 tarafından geçersiz
kılındı; aşağıdaki kapasite davranışı tarihsel uygulama kaydıdır, güncel ürün kuralı değildir.
Bu sınır giriş hesabı sayısına değil kalıcı ses kimliklerine uygulanır; aynı kişinin
doğrulanmış örnekleri yeni kişi değildir. Farklı model revision'larındaki aktif
profiller de aynı sınıra dahildir. Başka tenant'ın ve silinmiş profillerin sayısı
bu tenant'ın kapasitesini etkilemez; `super_admin` bu veri değişmezini aşamaz.

49 profilde 50. kayıt kabul edilir; 50 veya daha fazlasında yeni profil isteği
HTTP 409 ve `profile_limit` koduyla reddedilir. Önceden kabul edilmiş işin aynı
idempotency anahtarıyla tekrarı, kapasite kontrolünden önce aynı işi döndürür.
Bekleyen işler kapasite rezervasyonu değildir: eşzamanlı işler için mevcut tenant
işlem kilidi altında, yeni profil oluşturulmadan hemen önce sayı yeniden okunur.
Son yeri başka iş doldurduysa kuyruktaki iş terminal `failed/profile_limit` olur;
yeni profil/örnek yazılmaz ve otomatik çıkarım tekrarı yapılmaz. Yeni profil
eklemeyen `identify` ve mevcut profile örnek ekleme işlemleri kapasitede çalışır;
mevcut kalite, model ve 20 örnek sınırları geçerlidir. Kullanıcının mevcut silme
akışı bir yeri boşaltır. Önceden sınırı aşmış veri bulunursa kendiliğinden silinmez
ve eşleştirme havuzu ilk 50'ye kesilmez; yeni profil ekleme engellenir.

`GET /speaker-profiles` yanıtına zorunlu `max_profiles` alanı eklenir; değeri sabit
domain kapasitesinden 50 olarak gelir. Arayüz toplam/kapasiteyi gösterir, doluyken
yeni profil formunu engeller, mevcut profile örnek eklemeyi açık tutar ve hem
HTTP hem terminal işteki kapasite hatasını Türkçe/İngilizce açıklar. Sunucu
kontrolü arayüzün eski kalmış kapasite bilgisine dayanmaz. OpenAPI ve istemci
tipleri kaynaktan yeniden üretilir; yetki/tenant sınırları korunur.

Değerlendirme hedefi en fazla 50 kayıtlı kişidir; bilinmeyen test kişileri henüz
profil oluşturmadığı için bu kapasiteye dahil değildir. Yeni canlı değerlendirme
galerileri 50'yi aşamaz. Galeride gerçekten 50 kişi kayıtlıysa sonraki yeni kişi
kaydı kapasite nedeniyle reddedilir; koşucu bunu açık terminal kapasite sonucu
olarak kaydeder ve ana galeri ölçümünü kaybetmez. Bu, kalite hatası veya bilinmeyeni
tanıma başarısı sayılmaz; kapasiteyi aşmak için gizli silme veya yönetici istisnası
yapılmaz. Tarihsel ses, manifest ve kanıtlar yeniden yazılmaz; F1 formülleri ve
tanıma eşikleri değişmez.

Kapsam: sabit `kt-vibecoding-python-web-v2`, repository sayımı, service/worker
değişmezi, tipli API, iki dilli arayüz, değerlendirme aracı ve test/gerçek tarayıcı
kanıtı. Şema/migrasyon: N/A — mevcut profil ve tenant işlem kilidi yeterlidir.
Yeni ortam ayarı/bağımlılık/model/Spark imajı: N/A — 50 ürün kuralıdır; mevcut
Windows backend/worker ve arayüz güncellenir. 49/50/51, eşzamanlı son yer,
idempotent tekrar, örnek ekleme/tanıma, silme sonrası yer açılması, tenant/model
revision ayrımı ve iki dilde arayüz test edilir. Tam profil kapısı ve koşulamayan
güvenlik/tarayıcı girişleri kanıt raporunda ayrı gösterilir.

Decision 11 (10 Eylül 2026): Kullanıcı 50'nin bir kayıt sınırı değil, yaklaşık 50
katılımcı düzeyinde çok yüksek tanıma doğruluğu hedefi olduğunu açıkça düzeltti;
100–200 kişi düzeyinde de kullanım engellenmemelidir. Bu açıklama Decision 10'un
sert sınırını kaldırma yetkisidir. Kalıcı profil deposu ve toplantıya katılan kişi
sayısı ayrı kavramlardır. 50 bir kalite değerlendirme odağıdır; sistem toplam,
aktif veya aynı toplantı katılımcı sayısını bu sayıya kesmez. 100/200 için aynı
doğruluk veya gecikme garantisi verilmez.

Yeni profil kabulü ve işçi tamamlamasındaki yalnız profil sayısına dayalı engeller
kaldırılır. Tenant izolasyonu, idempotent tekrar, işlem kilidi, sahiplenme sürümü,
kalite/model kontrolleri, profil başına 20 örnek sınırı ve tanımanın profil değiştirmemesi
korunur. 50 aktif profil varken 51. kişinin kaydı ve 200 aktif profilden sonra yeni
profil kabulü sayı nedeniyle reddedilmez. Eşzamanlı 49+2 kayıt yeterli kanıtla iki
ayrı profil oluşturabilir; aynı işin yeniden tamamlanması çift örnek oluşturamaz.

`SpeakerProfilePage` tekrar `{items, total, offset, limit}` sözleşmesine döner;
gereksiz `max_profiles` alanı ve arayüz kapasite sayacı/engeli kaldırılır. Liste
toplamı kalır; yeni kişi formu liste kapasitesi yüklenmesini beklemez. Eski
`profile_limit` hata işleri değiştirilmez; Türkçe/İngilizce mesaj geçmişteki kural
nedeniyle reddedildiğini ve yeni kayıt başlatılabileceğini söyler. Bu alanı
kullanan tek yerel arayüz backend ile birlikte güncellenir ve sayfa yenilenir;
harici istemci sürüm uyumu iddia edilmez.

Canlı değerlendirme aracı, metrik doğrulayıcısı ve arşiv hazırlayıcısı doğruluk
hedefini ürün kotası olarak uygulamaz. 50'nin üzerindeki galeriler desteklenir;
100/200 kişilik deneyler mevcut dosya boyutu ve işlem sayısı sınırları içinde
geçerlidir. Bu, hazırlanmış 200 kişilik veri veya 200 kişilik doğruluk kanıtı
anlamına gelmez. Tarihsel kapasite retlerini okuyabilme ve eski rapor/manifest
korunumu devam eder; precision/recall/F1 formülleri değiştirilmez.

Doğruluk çalışması önce ilk kayıt retlerinin nedenini ve profili oluşan kişilerdeki
koşullu tanıma oranını ayrı inceler; bu alt grup ana paydanın yerine geçirilmez.
Yeni model, yeni örnek birleştirme veya kalite eşiği bu karar altında üretime
alınmaz: araştırma ve karşılaştırma önerileri ayrı çalışma belgesinde kaydedilir,
seçilen deney kendi PRD planı ve kontrollü kalibrasyon kanıtıyla uygulanır.

Kapsam: sabit `kt-vibecoding-python-web-v2`, backend/worker, tipli API, iki dilde
UI, değerlendirme manifest sınırları, test ve canlı doğrulama. Şema/migrasyon,
yeni ayar/bağımlılık, model eğitimi ve Spark imajı: N/A — bu düzeltme yalnız
yanlış yorumlanan kota davranışını kaldırır. Yeni kaynaklarla tam kalite kapısı
ve mevcut güvenlik/tarayıcı giriş noktaları çalıştırılır; eksik ortam açık raporlanır.

Requirement 1: Giriş yapmış ve yetkili kullanıcı `Konuşmacılar` ekranında kendi
profillerini listeler; ad, oluşturulma zamanı, örnek sayısı ve model sürümünü görür.
Gerçek ad zorunlu değildir; kullanıcının verdiği takma ad kullanılabilir.

Requirement 2: `Profil oluştur` veya mevcut profile `Örnek ekle` akışında bir ses
dosyası yüklenir. Önerilen örnek süresi 20–30 saniye olarak gösterilir. En az 10 saniye
kullanılabilir konuşma ve en az iki tutarlı 3–8 saniyelik pencere gerekir. Sessiz,
yetersiz, ağır kırpılmış veya tutarsız ses profili değiştirmez; gerekçe gösterilir.
Mevcut profile örnek eklemede ayrıca hedef kişiyle uyumluluk aranır: bütün uygun
profiller karşılaştırılır; hedef kişinin kabul eşiği ve aday farkıyla en iyi eşleşme
olması gerekir. Başka kişiye benzeyen veya belirsiz örnek eklenmez. Yeni profil
oluşturmada bu hedef-profil koşulu uygulanmaz.

Requirement 3: `Sesi tanı` ekranında dosya yüklenir; kalıcı bir analiz işi oluşturulur.
Başarılı sonuç `recognized`, `unknown` veya `ambiguous` olur. Yalnız `recognized`
kalıcı kişi kimliğine bağlanır. Benzerlik yüzde güven gibi sunulmaz. Kullanılabilir
ses süresi, model revision'ı, eşikler ve karar gerekçesi sonuçta bulunur.

Requirement 4: İşler `queued → running → succeeded|failed` durumlarından geçer;
yükleme tamamlanması analiz başarısı sayılmaz. Arayüz bekleyen/işlenen/hatalı durumu
ve sonuç bağlantısını gösterir; sayfa yenilendiğinde PostgreSQL'den devam eder.
İş kabulü HTTP 202 ve işin public kimliğini döndürür; istemci durum sorgularını sınırlı
aralıkla yapar. Bu pilotta SSE zorunlu değildir.

Requirement 5: Yükleme 50 MiB ve 120 saniyeyle sınırlıdır. Uzantıya ek olarak dosya
başlığı/gerçek çözülebilirlik kontrol edilir; ses 16 kHz mono olacak biçimde hazırlanır.
Dosya isimleri depolama yolu olarak kullanılmaz. Geçersiz dosya 400/415, limit aşımı 413,
yetersiz kullanılabilir ses ise açıklamalı başarısız analiz sonucu verir.

Requirement 6: İş başlatma, tenant+işlem kapsamlı bir idempotency anahtarı kullanır.
Aynı anahtarla aynı istek aynı işi döndürür; farklı içerik 409 olur. Yürütücü işi atomik
sahiplenir; yeniden başlatmada yarım kalan işler açık neden ve sınırlı yeniden deneme
politikasıyla işlenir. En fazla bir otomatik yeniden deneme; sonraki hata terminaldir.
Bir enrollment işi tekrar işlendiğinde ikinci profil veya ikinci örnek üretmez.
HTTP `Idempotency-Key` zorunlu, 8–128 ASCII karakterdir; tenant ve işlem türüyle
kapsamlanır ve terminal sonuçtan sonra 7 gün tutulur. İstek parmak izi kaynak SHA-256,
amaç, model sürümü, hedef profil ve normalize edilmiş adı içerir. Aynı dosyanın tekrar
yüklenmesinden gelen farklı recording kimliği aynı içeriği iki iş yapmaz. Yükleme
işlemi de kendi idempotency anahtarıyla aynı dosyada aynı recording kimliğini döndürür;
anahtar farklı içerikle tekrar kullanılamaz. Yanıt kaybında aynı anahtarla sonuç alınır.

Requirement 7: Profil yeniden adlandırma ve silme desteklenir. Silinen profil normal
listelerden ve eşleştirmeden çıkar; ona ait örnek/vektörler de aynı yaşam döngüsünü izler.
Geçmiş iş sonucu silinmiş bir profili etkin kişi gibi göstermez. Fiziksel veri temizliği
ayrı bakım adımıdır; pilotta kullanıcıdan habersiz toplu silme yapılmaz.
Silinen profilin örneklerine bağlı kaynaklar başka aktif profil/iş tarafından
kullanılmıyorsa uygulamaya ait kopyaları temizlenmek üzere işaretlenir. Aktif profil
örneğinin kaynağı `DELETE /recordings` ile tek başına silinemez; 409 döner. Bir profil
iş sürerken silinirse enrollment commit'i yeniden kontrol edilir ve değişiklik yapılmaz.

Requirement 8: Profil başına en fazla 20 aktif doğrulanmış örnek saklanır. Sınırda sessiz
örnek kaybı yerine kullanıcıya açıklamalı limit hatası döner. Birden fazla örnek eşit
ağırlıklı normalize ortalamayla kişi temsilini oluşturur; yeniden hesaplama atomiktir.

## UI ve API sözleşmesi

Önerilen rotalar `/speaker-profiles`, `/speaker-analysis` ve `/speaker-jobs/:publicId`.
Türkçe ve İngilizce metinler mevcut locale yapısına eklenir. AuthGuard, permission
kontrolleri, mevcut API istemcisi ve OpenAPI'den üretilen tipler kullanılır.

Aşağıdaki kaynaklar `/api/voiceup/v1` altında tanımlanacaktır:

| İşlem | Sözleşme |
| --- | --- |
| `POST /recordings` | Sınırlı multipart ses yükle; tenant'a ait recording public kimliğini döndür. |
| `POST /speaker-jobs` | Recording kimliği ve `enroll`/`identify` amacıyla iş oluştur; enrollment için yeni ad veya mevcut profil kimliği kabul et. |
| `GET /speaker-jobs/{public_id}` | Durum ve terminal sonucu getir; ham embedding döndürme. |
| `GET /speaker-jobs` | Tenant'a ait sınırlı/sayfalı iş geçmişi. |
| `GET /speaker-profiles` | Aktif profillerin sayfalı listesi. |
| `PATCH /speaker-profiles/{public_id}` | Adı güncelle; model/ses vektörünü değiştirme. |
| `DELETE /speaker-profiles/{public_id}` | Profil ve örneklerini normal kullanım/eşleştirmeden çıkar. |
| `DELETE /recordings/{public_id}` | Devam eden işte kullanılmayan dosyayı kullanıcı talebiyle kaldırma akışına al. |

Kaynak bulunmaması ve başka tenant'a ait kaynak için varlık sızdırmayan 404 döner.
Hata kodları ve alanlar PRD kabulünden sonra OpenAPI/test sözleşmesiyle kesinleştirilir.

## Güvenlik ve yetkilendirme

Mevcut JWT ve tenant context kullanılır. Önerilen izinler `speaker_profiles:read`,
`speaker_profiles:write`, `speaker_analysis:run`, `speaker_analysis:read`.
Super-admin uygulama yetkisini aşabilir; veri sorgusu yine açık tenant kapsamı taşır.
Yüklemede kayıt URI'si/yerel dosya yolu kabul edilmez. API'nın dönüştürülmemiş dosyası,
model servisine yalnız iç erişim ve doğrulanmış iş/tenant bağlamıyla aktarılır.
Çıkarım servisi dış ağa yayınlanmaz; ürün çalışma anında internet ve model indirmez.

Sesler, adlar, token'lar, embedding'ler veya en yakın kişilerin payload'ları loga
alınmaz. Loglar iş public kimliği, süre, cihaz ve sınırlı hata koduyla ilişkilendirilir.

## Veri ve migrasyon

Domain kayıtları: ses kaydı metadata'sı, profil, profil örneği/model vektörü ve analiz işi.
Hepsi PostgreSQL'de tenant kapsamlıdır. Dışa açılan kayıtlarda public kimlik; içeride
veritabanı üretilmiş kimlik kullanılır. AuditSoftDeleteMixin ve zorunlu lifecycle
alanları, UTC zamanları, aktif satır indeksleri ve açıklamalar uygulanır.

Ham sesler kontrollü kalıcı volume'de opak anahtarla tutulur; PostgreSQL dosya anahtarı,
SHA-256, boyut, format, sahibi ve kullanım durumunu tutar. Fiziksel dosya/DB yazımının
başarısızlıkta temizlenmesi veya geri kazanılması test edilir. Geçici başarısız
yüklemeler temizlenir; profil örneğine bağlı kaynaklar kullanıcı silene kadar tutulur.
Sahipsiz/yüklenip kullanılmamış dosyalar ve identify-only dosyalar 24 saat, terminal iş
metadata/sonuçları 7 gün tutulur. Saatlik bakım, süresi dolmuş yalnız uygulama kopyalarını
ve referanssız kayıtları temizler; aktif iş/profil referansı temizlemeyi engeller.
Kullanıcının yükleme öncesindeki orijinal dosyası bu akışın dışındadır. Silinmiş veya
süresi dolmuş yükleme için idempotency metadata'sı duruyorsa 410 döner; istemci yeni
dosya ve yeni anahtarla başlatır. Politikalar typed config ve testlerle görünür olur.
Pilot veri saklama seçimi bu kabul kapsamının parçasıdır; yeniden embedding için
kaynak ses olmadan başarı iddiası yapılmaz.

Alembic migrasyonu eklemeli olur; mevcut platform tablosu/verisi silinmez. `vector`
uzantısı yalnız kabul edilmiş uyumlu PostgreSQL image'ı ve yetkili migrasyonla açılır.
Uygulama açılışında uzantı veya paket kurulmaz. Şema ve migrasyon kontrolleri tek
kullanımlık `_test` veritabanında yapılır.

## Vektör ve embedding sözleşmesi

- Sağlayıcı: yerel, ağdan model indirmeyen ECAPA altyapı adaptörü; tipli uygulama portu.
- Model: `speechbrain/spkrec-ecapa-voxceleb`.
- Immutable revision: `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`.
- Boyut/normalizasyon: 192 boyut, sonlu/zero olmayan vektör, L2 normalizasyonu.
- Saklama: aynı PostgreSQL'de pgvector `vector(192)`; örnek ve kişi temsili sürümleri
  birlikte izlenir. Farklı revision aynı aramada birleştirilmez.
- Arama: başlangıçta exact cosine; SQL repository'de tenant+aktif profil+model filtresi
  zorunludur. Uygun bütün kişi temsilleri skorlanır; sıralamadan önce aday kırpılmaz.
  En az ilk iki sonuç karar farkında kullanılır, yalnız dönen sonuç sayısı sınırlanır.
  Profil listeleme sayfalaması bu aramadan ayrıdır. HNSW/IVFFlat bu pilotta yoktur.
- Karar: Decision 7 ile kalibre edilmiş pilot 0.55 kabul, 0.45 bilinmeyen ve 0.10
  aday farkı kullanır. Önceki 0.75 referansı karşılaştırma kanıtında korunur.
  Bunlar gerçek doğruluk garantisi veya kalibre olasılık değildir.
- Pilot kalite hedefi: 5 kayıtlı kişinin her birinden farklı oturumda 3 sorgu
  (toplam 15 bilinen) ve en az 2 ayrı kayıtsız kişiden toplam 10 sorguda bilinen doğru
  kabul en az 14/15, kayıtsız yanlış kabul 0/10. Bunlar henüz ölçülmemiş başlangıç
  kabul hedefleridir; küçük örneklem üretim FPIR garantisi vermez. Ayrıntılı 50 kişi
  protokolü [EVALUATION_PLAN.md](../../../../docs/EVALUATION_PLAN.md) içinde kalır.
- Kalite: kullanılan pencere tutarlılığı ve minimum süre denetlenir. Yeni model veya
  eşik yalnız ayrı doğrulama verisiyle seçilir; örneği geçirmek için test verisine ayar yapılmaz.
- Gecikme: en fazla 120 saniyelik dosyada iş başına 300 saniyelik yürütme zaman aşımı;
  bu bir hız iddiası değildir. GPU sıcak/soğuk süreleri, kuyruk bekleme ve tepe bellek raporlanır.
  Ayrıca önceden yüklenmiş modelle 30 saniyelik dosyada en az 20 işten ölçülen p95
  yürütme süresi en fazla 30 saniye hedeflenir; yükleme ve kuyruk beklemesi ayrı raporlanır.
  Bu hedef 4060'ta ölçülmeden geçti sayılmaz.
- Yeniden embedding: yeni model için ayrı sürümlü popülasyon, idempotent backfill,
  doğrulama ve açık cutover; önceki model popülasyonu rollback için korunur.
- Donanım: ilk kanıt 4060/CUDA üzerinde; Spark kanıtı ayrıca gereklidir.

## İşletim, bağımlılık ve dağıtım

Web profile'i değiştirilmez. GPU image'ı, CUDA/PyTorch/torchaudio uyumu, model paketinin
hashleri ve pgvector image/bağımlılığı sahip kaynakları ve dependency-admission kaydıyla
birlikte ele alınır. Mevcut CPU indeksli `uv.lock` değiştirilerek GPU hazır ilan edilmez.
Model bulunamaması readiness/hata durumudur; kullanıcıdan gizli indirme yapılmaz.

Kalıcı iş yürütücüsü bu PRD'de açıkça tanımlı ayrı süreçtir; iş kaydının otoritesi
PostgreSQL'dir. Süreç yeniden başlatma/lease kontrolü ve sınırlı deneme uygulanır.
Yürütücü aynı domain'in backend kodunu kullanan ayrı süreçtir; çıkarım HTTP servisi
veritabanına erişmez. Süreli lease ve artan sahiplenme sürümüyle eski yürütücünün
geç gelen sonucu reddedilir. Enrollment commit'inde lease, hedef tenant/profilin
aktifliği ve model uyumluluğu aynı transaction içinde tekrar denetlenir.
Uygulama servisleri ses modelini doğrudan import etmez. Log/metric: iş sayısı, durum,
iş başına süre, kullanılan ses süresi, model/cihaz, hata nedeni; kişisel içerik yok.
Compose ve ilgili backend/worker chart/config yüzeyleri aynı sözleşmeyle güncellenir.

## Kabul ölçütleri

- [x] Requirement 1–4: gerçek tarayıcıdan yükleme→iş durumu→profil veya tanıma sonucu akışı çalışır; sayfa yenilemede kaybolmaz.
- [x] Requirement 2,5: sessiz/kısa/bozuk/limit aşmış ses doğru gerekçeyle reddedilir ve profil kirlenmez.
- [x] Requirement 2: başka kişiye ait temiz ses mevcut profile örnek ekleme olarak gönderildiğinde reddedilir ve önceki vektörler değişmez.
- [x] Requirement 3,8: tanıma profil değiştirmez; bilinmeyen/belirsiz ses yanlış biçimde yeni kayıt yaratmaz; örnek limiti açıkça uygulanır.
- [x] Requirement 6: çift gönderim, worker kapanması ve yeniden denemede çift profil/örnek oluşmaz.
- [x] Requirement 7: silinen profil aramaya katılmaz; tenant'lar arası erişim ve arama izolasyonu canlı PostgreSQL testinde geçer.
- [x] Tarihsel Decision 10, Decision 11 ile yürürlükten kalktı: çalışma alanında en çok 50 aktif profil; eşzamanlı son yer, yeniden deneme, örnek ekleme/tanıma ve silmeyle yer açma o kararın gerçek PostgreSQL testlerinde doğrulandı. İki dilde kapasite/form/hata görünümü ve kayıt reddi gözlendi. [Tarihsel kapasite kanıtı](../../../../docs/evidence/2026-09-10-speaker-capacity/README.md) korunur; güncel ürün davranışı veya model doğruluğu kanıtı değildir.
- [x] Decision 11: ürün kotası servis/işçi/API/UI'dan kaldırıldı; gerçek PostgreSQL testleri 50→51 ve 200→201 kayıtlarını, yeniden deneme ve mevcut güvenceleri doğrular. Canlı Spark üzerinde 51. profil oluşturuldu; Türkçe/İngilizce altı arayüz kabul noktası gözlendi. 200 kişilik değerlendirme girdisi ve tarihsel sonuç uyumu test edildi. [Yeni kanıt](../../../../docs/evidence/2026-09-10-speaker-quality-target/README.md); 50 gerçek kişi doğruluğu, güvenlik ortamı ve L3 kabulü açık kalır.
- [ ] L1: birim, gerçek PostgreSQL/pgvector, şema, config, OpenAPI, frontend tip/build/test ve güvenlik kontrolleri geçer; skip/failure ayrı verilir.
- [x] L2: gerçek yerel HTTP/browser akışı ve 4060 üzerinde gerçek ECAPA çıkarımı gözlenir; sentetik test embedding'i donanım kanıtı sayılmaz.
- [ ] Veri deneyi: beş kişi için ayrı oturum örnekleri, kayıtlı olmayan altıncı kişi ve açıkça enrollment sonrası geri dönüş ölçülür; doğru/yanlış/belirsiz sonuçlar raporlanır.
- [x] Kalite sonucu: kullanıcı kayıtları sağlanmadıysa bu deney eksik olarak kalır; yazılım testi gerçek Türkçe tanıma başarısı diye sunulmaz.

## Riskler ve uygulama başlangıcındaki durum

Kısa veya karışık ses, benzer kişiler, mikrofon farkı ve aşırı muhafazakâr eşikler
belirsiz/yanlış karar üretebilir. Mevcut kısa gerçek örnek 0.75 kabul eşiğini geçmemiştir.
İlk pilotun amacı bu durumu görünür ve ölçülebilir hale getirmektir.

Başlangıç envanterinde VoiceUp stack'i, CUDA ve pgvector hazır değildi. Yerel uygulama
artık 8081'de, PostgreSQL 17.11/pgvector 0.8.6 ve RTX 4060/CUDA ile çalışıyor.
[Kanıt raporu](../../../../docs/evidence/2026-09-08-local-speaker-pilot/README.md) son testleri
ve eksik girdileri kaydeder. L1'in yazılım/şema kısmı geçti; ayrı güvenlik tarama ortamı
ve kalıcı Playwright paketi sağlanmadı. Bu başlangıç kanıtı sonradan yapılan Spark
ve açık veri deneyinden ayrıdır.

9 Eylül 2026 açık veri sonucu: [gerçek uygulama raporu](../../../../docs/evidence/2026-09-09-public-speaker-evaluation/README.md).
Kalibrasyon ve testte toplam 140 farklı İngilizce kişiyle 604 ses parçası hazırlandı.
Seçilen 0.55 politikası kalibrasyonda 109/150, ayrı testte 77/150 doğru tanıma verdi.
Testte 50 adaydan 29 profil oluşturulabildi; yeni kişi kaydı ve geri dönüş sorgusu
kalite hatasıyla sonuçlandı. Yanlış kimlik gözlenmemesi yüksek doğruluk kabulü
değildir. Türkçe temsilî oturum verisi, kayıtlı 50 kişilik başarı ve güvenlik
kanıtı açık kalır. Mevcut çalışma ortamı Spark'tır; 4060 sonucu tarihsel referanstır.

Decision 8 uygulama kanıtı: [korumalı kurtarma raporu](../../../../docs/evidence/2026-09-09-speech-recovery/README.md).
Eski yeterli kanıtları koruyan sürüm kalibrasyonda 111/150, aynı tarihsel testte 78/150
doğru tanıdı; ilk profil kapsamı 40/50 ve 29/50 olarak kaldı. Önceki 146 kişiden ayrık
yeni temiz İngilizce grupta 40/50 profil ve 116/150 doğru tanıma, yeni kişi kaydı ve
geri dönüş başarısı gözlendi. Hiçbir koşumda yeni yanlış kimlik gözlenmedi; bu
sınırlı veriyle %95 hedefi veya Türkçe toplantı kabulü tamamlanmadı. Güvensiz
birleştirme adayları ve eski sürekli-karışım yolundaki iki kötü kabul kanıtta korunur.

## Teslim akışı

Spec → açık kullanıcı kabulü → Accepted PRD → Plan → Tasks → Implement → kanıt.
Kapsam kabul edildi. Uygulama, bağlı plan ve görevlerden yürütülür; başarısız veya eksik kanıt açıkça raporlanır.
