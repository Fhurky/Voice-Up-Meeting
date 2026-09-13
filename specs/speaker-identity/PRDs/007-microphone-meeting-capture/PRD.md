# PRD — Mikrofon kaydından toplantı analizi

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [007 — microphone-meeting-capture](../../roadmap.md)
Sabit profil: `kt-vibecoding-python-web-v2`.
Kabul kaydı: 10 Eylül 2026'da kullanıcı ses dosyası yükleme **veya** kayıt alma
isteğini açıkça iletti. Bu kaynak kapsamı başlangıçta 002 içinde Accepted idi.
Aynı gün kullanıcı "Kaydı yüklemek yeterli; tanıma ve hafızayı tamamla" yanıtıyla
o teslimi dosyaya daralttı ve mikrofon isteği bu bağımsız yeteneğe taşındı.
11 Eylül 2026'da kullanıcı "Uygulmanın içinde de ses kaydı yapabilelim istiyorum,
kayıt yükleme gereksinimi olmadan" talimatıyla 007'nin uygulanmasını açıkça istedi.
Bu yeni kabul kaydı aşağıdaki tarayıcı kaydı kararlarını etkinleştirir;
uygulama veya gerçek cihaz doğrulamasının tamamlandığı iddiası değildir.

## Amaç, aktörler ve sınır

Yetkili kullanıcı tarayıcıda seçtiği mikrofonla kayıt alır ve "Durdur ve analiz et"
eylemiyle kaydı 002'nin konuşmacılı metin/kalıcı hafıza akışına verir. Kullanıcının
ses dosyası hazırlaması, kaydetmesi veya dosya seçicisinden tekrar seçmesi gerekmez.
Aktörler toplantı sahibi, tenant yöneticisi ve analiz yürütücüsüdür. Varsayılan
mikrofon yalnız seçilen giriş cihazını yakalar; bilgisayarın bütün seslerini veya
uzak Teams katılımcılarını otomatik toplamaz. Canlı metin/kimlik yayını ve toplantı
platformu bağlantısı bu yeteneğe dahil değildir; 003 canlı kimlik taslağı ayrıdır.

## Kararlar

Decision 1: Mikrofon yalnız kaynak üretir; 002 model rolleri, kalıcı kimlik,
>20 saniye temiz kanıt, isimlendirme ve yetki kuralları tekrar uygulanmaz veya
gevşetilmez. Analiz kayıt durup son parça doğrulandıktan sonra başlar.

Decision 2: Önceki WebM/Opus araştırma hedefi yerine tarayıcının yerleşik
`AudioWorklet` işlemcisi tek kanallı, işaretli 16 bit PCM üretir. Örnekleme hızı
gerçek `AudioContext.sampleRate` değerinden doğrulanır ve WAV başlığına aynı
değer yazılır; desteklenmeyen hız sessizce yeniden etiketlenmez. Bu gerçek PCM
verisi RIFF/WAVE dosyasına yazılır; kapsayıcı uzantısı değiştirilerek dönüşüm
iddiasında bulunulmaz. Son WAV mevcut 002 `SoundFile` decoder'ından geçer;
WebM/MP4 decoder'ı, yeni paket veya bağımlılık sürümü eklenmez. 002'nin 8–192 kHz
doğrulama sınırı korunur; seçilen dar tarayıcı hızının desteği gerçek cihazda
ayrıca doğrulanır.

Decision 3: Kayıt sürerken ses tarayıcının kökene özel dosya sistemindeki
(`Origin Private File System`, OPFS) geçici dosyaya sıralı yazılır. Tam kayıt
tarayıcı RAM'inde veya bütün parçaları birleştiren bir `Blob` içinde tutulmaz.
Üreticideki kısmi blok, ileti kuyruğu ve henüz diske yazımı onaylanmamış bloklar
birlikte en çok 16 MiB olur. Üreticiye yazım onayıyla geri verilen sınırlı
kapasite, ana iş parçacığı yavaşladığında da sınırsız kuyruk oluşmasını önler.
Sınır aşılacaksa kayıt sessiz kayıp yerine görünür eksik kayıt hatasıyla durur.
Geçici kaynak, WAV başlığı dahil en çok 2 GiB ve en çok 4 saat olur. Önceden
bilinen süre/byte sınırına ulaşıldığında son geçerli örnekte üretim durur;
tampon boşaltılır, WAV mühürlenir ve sınır nedeniyle durduğunu belirten görünür
bildirimle normal analiz akışı otomatik başlar. Sınıra kadar eksiksiz kaydedilen
ses atılmaz; sınır sonrasındaki ses kaydedilmiş gibi gösterilmez. Tarayıcı
kotası daha erken dolarsa, yazılamayan ses bulunduğundan eksik kayıt hatası
yolu kullanılır. Kota tahmini başarılı yazma garantisi sayılmaz; gerçek yazma
hatası ayrıca ele alınır.

Decision 4: "Durdur ve analiz et" önce üretimin bitmesini ve son PCM bloğunun
diske yazılmasını bekler; ardından kesin örnek sayısıyla WAV başlığını tamamlar,
yazıcıyı kapatır ve dosya tutamacından `File` alır. Yalnız bu mühürlenmiş kaynak
002'nin değişmeyen oluşturma ve sıralı SHA-256 doğrulamalı 4 MiB aktarım yoluna
verilir. Başlık, dosya boyutu, örnek sayısı veya son yazım uyuşmazsa analiz
başlatılmaz. Mikrofon ve ses bağlamı dosya aktarımı beklenmeden kapatılır.

Decision 5: OPFS dosyası kayıt bileşeninde yükleme boyunca yaşar; bağlantı
hatasından sonra analiz/aktarım tekrarı aynı değişmeyen kaynak ve hashlerle sürer.
Başlatma ve aktarım aynı ekranda tamamlanır; toplantı sonucuna yönlendirme ancak
002 tamamlanma yanıtından sonra yapılır. Aktarım tamamlandığında veya
kullanıcı kaydı iptal ettiğinde geçici kaynak serbest bırakılır. Kayıt hatası,
sayfadan çıkış, oturum sonu ve geç gelen izin yanıtı cihaz/bağlam/yazıcı
temizliğini tetikler. Uygulamaya ait rastgele kimlikli geçici dosyada ad, token
veya transkript tutulmaz. Tarayıcı çökmesi ya da yenileme ile kaybolmuş mikrofon
geçmişi yeniden oluşturulmaz; mühürlenmemiş dosya tamamlanmış kaynak diye
aktarılmaz. Sekme/işlem zorla kapandığında temizlik en iyi çaba düzeyindedir;
kalan geçici dosya için otomatik kurtarma veya başka sekmelerin dosyalarını
tarayan bir temizleyici sunulmaz. Bu yerel disk sınırı belgelenir.
Uygulama yalnız kendi kayıt geçicilerini temizler; kullanıcının
seçtiği dosyalara veya önceki toplantı verisine dokunmaz.

Decision 6: Kayıt, mikrofon izni ve `AudioWorklet` ile OPFS desteği olan güvenli
tarayıcı bağlamı gerektirir. Yerel `http://localhost`/`http://127.0.0.1` ve uygun
HTTPS kökenleri hedeflenir; düz HTTP ağ adresinin aynı yetenekleri sunduğu
varsayılmaz. Desteklenmeyen ortamda neden ve mevcut dosya yükleme yolu gösterilir.
Kayıt kullanıcı eylemi olmadan başlamaz; sadece seçilen giriş cihazı yakalanır.
Bir tarayıcı/cihazdaki başarı başka tarayıcı, Apple veya Spark kanıtı sayılmaz.

Decision 7: Mevcut decoder'ın eksik veya çelişkili RIFF uzunluğunu sessizce
kırparak kabul etmesi tam kaynak sayılmaz. RIFF dosya uzunluğu ve alt parça
sınırları/dolgusu gerçek byte dizisiyle uyuşmalıdır; PCM başlığının işaretlediği
ses kaybolmaz veya fazladan kuyruk sessizce yok sayılmaz. Yasal bilinmeyen/JUNK
parçaları ve tek uzunluklu parçalardaki dolgu kabul edilir; mevcut RF64
desteğinin davranışı korunur. Bu gerçek disk adaptöründeki bütünlük kontrolü
yeni decoder, API alanı veya şema eklemez.

## Gereksinimler

Requirement 1: Mikrofon izni, giriş cihazı seçimi, gerçek kayıt durumu/süresi,
"Durdur ve analiz et" ve iptal erişilebilir TR/EN arayüzünde bulunur. İzin reddi,
cihaz yokluğu/kesilmesi, desteklenmeyen tarayıcı, yetersiz yer, tampon sınırı ve
yükleme bağlantısı hatası ayrı yerelleştirilmiş durumlardır. Kontroller mevcut
008 tasarımının ortak bileşenleri, odak ve dar/geniş görünüm kurallarını kullanır.

Requirement 2: İptal, sayfadan çıkma ve geç dönen izin sonucu bütün mikrofon
track'lerini kapatır. Durdurma `AudioWorklet` son blok/bitirme onayını ve disk
yazımını bekler; henüz yazılmayan ses tamamlanmış sayılmaz. Kaynak cihazın
kesilmesi, ses bağlamının beklenmedik durması veya işlemci hatası görünür eksik
kayıt üretir; otomatik yeniden bağlanma süre boşluğunu konuşma gibi göstermez.
Yenileme, eski mühürlenmemiş kayıttan otomatik analiz başlatmaz. Önceden bilinen
4 saat/2 GiB sınırında kayıpsız bitirme Decision 3 uyarınca normal durdurma
akışıdır; kota, tampon, cihaz veya yazım hatası bu duruma dönüştürülmez.

Requirement 3: Mühürlenmiş WAV, 002'nin yetkili yükleme portundan geçer; aynı
tenant, boyut/süre, hash, tekrar, kaynak sınırı ve iptal kuralları uygulanır.
Tarayıcı kayıt süresince yeni toplantı işi veya biyometrik profil yaratmaz;
eksik kayıt bir işin analiz kuyruğuna alınmasına neden olmaz. Gerçek kaynak
decoder'dan geçirilmeden hayalî model yanıtıyla kabul yapılmaz.

Requirement 4: Tam kaynak 002 analiziyle konuşmacılı metin verir; kısa kişinin
metni korunur ve biyometrik profil sonucu ayrı gösterilir. 002 sayı ipuçları ve
elle isim verme sözleşmesi kullanılır; kaynak kaydı ayrı kimlik sistemi üretmez.

Requirement 5: Toplantı adı, dil, isteğe bağlı katılımcı üst sınırı, kesin
konuşan kişi sayısı ve yetkiye bağlı kalıcı hafıza seçeneği mikrofon kaynağında
da kullanılır. Dosya ile mikrofon arasında geçiş, aktif kaydı sessizce arka
planda sürdürmez. Salt okunur kullanıcıya kayıt/yükleme eylemi sunulmaz;
nihai yetki kontrolü değişmeyen backend API'sinde kalır.

## Veri, güvenlik ve çalışma

Şema ve migrasyon N/A — ayrı kayıt/profil otoritesi oluşturulmaz; son WAV mevcut
002 kaynak ve iş sözleşmesini kullanır. API/OpenAPI değişikliği N/A — yeni uç,
alan veya içerik türü eklenmez; üretilmiş sözleşme/tip drift kontrolü yine yapılır.
Önbellek N/A — OPFS geçicisi yetkili kullanıcı kaydının sınırlı yerel kaynağıdır,
sunucu verisinin ikinci önbelleği veya kalıcı toplantı geçmişi değildir.

JWT/tenant/rol denetimi 002 ile aynıdır; otomatik hafıza için ayrıca profil yazma
izni gerekir. Mikrofon kullanıcı eylemi ve tarayıcı izni olmadan başlamaz; ses,
transkript veya token loglanmaz. Saklama ve silme 002 kaynak/profil ayrımını
izler. Web/API Python 3.13/FastAPI ve React/Vite sınırında kalır; farklı backend
veya çalışma anında model/bağımlılık indirme eklenmez.

Yeni decoder/lisans/hash ve bağımlılık kabulü N/A — tarayıcı yerleşik ses/dosya
API'leri ve kabul edilmiş WAV decoder'ı kullanılır; mevcut pinler değişmez.
Yeni typed setting, ortam değişkeni ve model readiness değişikliği N/A — kaynak
bütçeleri mevcut 002 sınırlarını aşmaz; tarayıcı desteği kayıt kontrolünde
ölçülür. Dağıtım, aynı kökenden yüklenen derlenmiş worklet varlığını sunar;
Compose/Helm sürümleri veya ağ çıkışı değişmez, tam chart kapısı yine koşulur.
Gözlemlenebilirlik kayıt süresi, bekleyen byte ve sınıflandırılmış yerel hata
durumlarıyla sınırlıdır; ses, cihaz kimliği/etiketi, dosya içeriği veya transkript
telemetriye gönderilmez. Kullanıcıya kaynak sınırı ve mikrofonun yalnız seçilen
girişi yakaladığı açıklanır; çevrimdışı kullanım ve cihaz farkları belgelenir.

## Test ve kabul

- [ ] Requirement 1–2, 5: TR/EN arayüzünde cihaz seçimi, izin, kayıt, durdurma, iptal, ortak toplantı seçenekleri ve sıradan/salt okunur yetkiler doğrulanır.
- [x] Decision 3–5 / Requirement 2: 16 MiB toplam tampon, yavaş disk, kota/yazma hatası, son PCM bloğu, başlık/örnek sayısı, 4 saat/2 GiB sınırında kayıpsız durdurup analiz, cihaz/bağlam kesilmesi, iptal ve geç izin temizliği davranış testleri geçer; tam kayıt RAM'de tutulmaz. [26 adaptör/PCM testi ve bileşen testleri](../../../../docs/evidence/2026-09-11-microphone-recording/README.md); fiziksel cihaz/saatler süren koşum bu kanıttan çıkarılmaz.
- [ ] Decision 4–5 / Requirement 3: Gerçek diskten alınan mühürlü WAV, 002 gerçek HTTP/disk sınırından geçer; hash, eksik/çelişkili parça, tekrar, kaynak sınırı, yetki ve tenant kontrolleri korunur.
- [ ] Decision 2, 6–7 / Requirement 3: Gerçek tarayıcı mikrofon çıktısı mevcut çevrimdışı WAV decoder'ı ile çözülür; RIFF/PCM uzunluk ve parça sınırları, yasal JUNK/dolgu ve RF64 korunumu gerçek disk testlerinde doğrulanır; desteklenmeyen ortam ve dosya yükleme seçeneği doğrulanır.
- [ ] Requirement 4: Durdurulan gerçek mikrofon kaydı 002 üzerinden konuşmacılı metne ve uygun hafıza sonucuna dönüşür; sahte capture veya token enjeksiyonu canlı kanıt sayılmaz. Sessiz cihaz deneyi metin/kişi başarısı sayılmaz.
- [ ] Tam profil/güvenlik/kontrat/chart ve kayıtlı gerçek tarayıcı senaryosu kanıtı kaydedilir; yalnız simüle edilen yaşam döngüsü vakaları, eksik cihaz/ortam ve L3 kabulü açıkça raporlanır.

Open Question 1: Hedef tarayıcıların gerçek mikrofon/örnekleme hızı ve OPFS desteği
cihaz bazında ölçülecektir. Desteklenmeyen ortama çalışan kayıt veya farklı
cihazda başarı atfedilmez; bu eksikler görev ve koşum raporunda izlenir.
