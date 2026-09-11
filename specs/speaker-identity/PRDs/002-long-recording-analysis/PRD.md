# PRD — Konuşmacılı toplantı dökümü ve kalıcı kişi hafızası

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [002 — long-recording-analysis](../../roadmap.md)
Kabul kaydı: 10 Eylül 2026. Kullanıcı ses dosyası yükleme veya kayıt alma,
kayıttaki kişileri ayırma, her kişinin sözlerini yazma ve yeni kişileri hafızaya
ekleme akışını açıkça istedi. Bu talimat ürün kapsamının kabulüdür; model
erişimi, bağımlılık kabulü, uygulama veya doğruluk testinin tamamlandığı anlamına gelmez.
9 Eylül taslağının transkript ve mikrofonu dışarıda tutan kapsamı bu kararla değişti.
Sabit profil: `kt-vibecoding-python-web-v2`.

Ek kabul kaydı: 10 Eylül 2026. Kullanıcı ileride Teams toplantılarındaki kısa ve
aralıklı konuşmaları işleyeceğimizi açıkladı; aynı kişiye ait konuşmaların
biriktirilmesini ve toplam konuşma 20 saniyeyi aştığında süre açısından yeterli
sayılmasını istedi, güvenilir yöntemin seçimini uygulayıcıya bıraktı. Aşağıdaki
Decision 6, Decision 8 ve Decision 9 bu kararı kaydeder. Süre kararı kalite ve
kimlik kontrollerini kaldırmaz; 001'in tek konuşmacılı API/eşikleri değişmez.

Son kabul kaydı: 10 Eylül 2026. Kullanıcı akışın uçtan uca tamamlanmasını istedi:
kayıt yükleme, konuşmacı ve metin çıktısı, kişilere elle isim verme, kalıcı hafıza,
aynı beş kişinin sonraki toplantıda aynı beş profille tanınması ve altıncı yeni
kişinin eklenmesi. İsteğe bağlı konuşmacı sayısı girdisi de bu kabulün parçasıdır.
Decision 10–11 ve Requirement 8–10 bu sonucu tanımlar; gözlenen ön hazırlık
kanıtları uçtan uca kabul yerine geçmez. Kullanıcı sonraki kaynak sorusunu
"Kaydı yüklemek yeterli; tanıma ve hafızayı tamamla" diye yanıtladı. Bu nedenle
002'nin güncel teslim kaynağı yüklenen dosyadır; Teams'ten otomatik kayıt alma ve
mikrofon yakalama bu akışın kabul şartı değildir. Önceki mikrofon isteği tarihçede
korunur ve yol haritasında ayrı mikrofon yeteneği olarak izlenir.

## Amaç, aktörler ve kullanıcı sonucu

Yetkili kullanıcı kaydedilmiş tek ses dosyasını yükler.
Sistem tek zaman çizelgesinde kimin ne söylediğini yazar, önceki toplantılardan
tanınan kişilere mevcut kalıcı kimliklerini bağlar ve yeterli temiz kanıtı olan
yeni kişileri otomatik kaydeder. Gerçek isim çıkarılmaz; yeni kişi kararlı bir
geçici ad taşır; toplantı sonucu veya mevcut profil ekranından kullanıcı elle ad verebilir.

Aktörler: toplantı sahibi kullanıcı, tenant yöneticisi ve kalıcı analiz yürütücüsü.
İlk kabulde Windows web/API/veritabanını, yetkili Spark cihazı bütün yapay zekâ
çıkarımını çalıştıracak şekilde planlandı. Sonraki cihaz seçimiyle kullanıcı
yerel RTX 4060 üzerinde geliştirmeyi de açıkça seçti; sağlayıcı sınırı Decision 9'dadır.
Tarayıcı model servisine doğrudan erişmez. Dosya parçalarla aktarılır; analiz
aktarımın tamamlanması ve doğrulanması sonrasında başlar. Kayıt sürerken metin yayımlama
bu kapsamda yoktur; 003 mevcut olarak yalnız canlı konuşmacı kimliği analizini
kapsar. Toplantı platformu bağlantısı bu yeteneğin parçası değildir.
Mikrofon yakalama, önceki isteği koruyan ayrı yol haritası yeteneğinde izlenir.

## Kararlar

Decision 1: 001'in tek konuşmacılı kayıt/tanıma API'si ve `identify` işleminin
profili değiştirmeme kuralı korunur. Yeni akış ayrı toplantı servisi ve API'sidir.
002 uygulama çalışması öne alınır; 001'in açık doğruluk hedefi geçilmiş sayılmaz.

Decision 2: Üç farklı görev ayrılır: konuşmacı zaman aralıklarını ayırma,
konuşmayı metne çevirme ve kalıcı kişiyle eşleştirme. İlk sağlayıcı adayları:

| Görev | Model ve araştırmada doğrulanan revision | Durum |
| --- | --- | --- |
| Konuşmacı ayrımı | `pyannote/speaker-diarization-community-1`, `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee` | CC-BY-4.0; kullanıcı koşul kabulü ve yetkili indirme erişimi gerekir. |
| Metne çevirme | `Systran/faster-whisper-large-v3`, `edaa852ec7e145841d8ffdb056a99866b5f0a478` | Whisper large-v3'ün CTranslate2 dağıtımı; sabit model kartı MIT, erişim kapısız; paket/lisans/hash ve gerçek çıktı ayrıca doğrulanır. |
| Kalıcı kişi | `speechbrain/spkrec-ecapa-voxceleb`, `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286` | Mevcut 192 boyutlu normalize ECAPA uzayı ve exact cosine araması. |

İlk iki satır araştırma seçimidir, üretim çalışma zamanı kabulü değildir. Dosya
hashleri, gerçek çıktı sözleşmesi, lisans dosyaları ve seçilen cihazın Python
3.13/CUDA bağımlılık kapanışı görülmeden ilgili sağlayıcı etkinleştirilmez.
Spark için ARM64 kapanışı ayrıca gerekir; yerel RTX 4060 kanıtı bunun yerine geçmez.
Mevcut profil vektörleri diarization
modelinin vektörleriyle karşılaştırılmaz. Yeni model eğitimi bu kapsamda gerekli değildir.

Metne çevirme için ilk araştırmada `openai/whisper-large-v3` revision
`06f233fe06e710322aca913c1bc4249a0d71fce1` kaydedilmişti. Güncel dağıtım seçimi
yukarıdaki üretici tarafından dönüştürülmüş CTranslate2 paketidir; eski revision
bu paketin byte kimliği olarak kullanılmaz. Seçilen uygulama kitaplıkları
`faster-whisper 1.2.1` ve `ctranslate2 4.8.1` için bağımsız sürüm/güvenlik/kapanış
kabulü gerekir. Başlangıç yürütme ayarı GPU'da `int8_float16`, CPU'da `int8`,
batch 1 ve modelin 30 saniyelik doğal metin pencereleridir. Ortak sağlayıcı girdisi
en çok 310 saniyedir (Decision 14); konuşmacı ayrımı ve metin aşamaları GPU'da sırayla çalışır.
Sözcük zaman damgaları ve hizalama ancak gerçek sağlayıcı deneyiyle dondurulur;
bu seçim başarılı çıkarım, yeni bağımlılık kabulü veya ürün hazır olma iddiası değildir.

Decision 3: Kaynak dosya sıralı/hashli parçalarla diske aktarılır;
tam kayıt tarayıcı RAM'inde veya HTTP gövdesi olarak bellekte biriktirilmez.
Henüz ölçülmemiş başlangıç tasarım bütçeleri kaynak başına 4 saat ve 2 GiB,
aktarım parçası başına 4 MiB,
tenant başına en çok iki aktif aktarım ve 10 GiB tutulmuş toplantı kaynağıdır.
Bu bütçeler kişi kotası değildir. İlk kabuldeki 16 MiB mikrofon tamponu kararı
ayrı mikrofon yeteneğine taşınmıştır; dosya aktarımı bellekte bütün kaydı tutmaz.

Dosya kaynakları WAV/FLAC'tır. Diğer kapsayıcı/codec desteği ancak ilgili
çevrimdışı decoder kabulü ve gerçek dosya testleriyle açılır; uzantı değiştirmek
dönüştürme sayılmaz. Önceki WebM/Opus mikrofon hedefi ayrı yetenekte korunur.
Decoder/binary hashları uygulama öncesi
sağlayıcı sözleşmesinde dondurulur; keyfi dosya, URL, codec veya kabuk komutu kabul edilmez.

Decision 4: Çözüm Decision 14 uyarınca 300 saniyelik ana bölge ve her yanda 5 saniyeye kadar bağlamla
sınırlı bellek kullanır. Asıl kayıt bütün kanallarıyla korunur; ayrı katılımcı
kanalı bildirimi varsa ayrı işlenir, karma mikrofon kayıtlarında bu bilgi varsayılmaz.
Parça etiketi, toplantı akustik kümesi, kaynak platform katılımcısı ve kalıcı
kimlik birbirine eşit sayılmaz. Bağlamdaki aynı ses ve aynı söz iki kere sayılmaz.
Seçilen cihazda aynı anda tek GPU çıkarım işi
yürür; mevcut pilotla meşgul olma, zaman aşımı ve adil kuyruk davranışı birlikte sınanır.
Sağlayıcının dolgu nedeniyle kaynak süresini aşan son zaman damgası gerçek kaynak
aralığına kırpılır; tamamen kaynak dışındaki aralık kanıt veya söz üretmez. Sonlu
olmayan veya ters zaman aralıkları hata olarak kalır. Ham sağlayıcı zamanı ile
uygulamanın kaynak sınırına aldığı zaman ayrı doğrulanır; dolgu konuşma süresi sayılmaz.

Decision 5: Dil varsayılanı Türkçe; kullanıcı Türkçe, İngilizce veya otomatik
algılama seçebilir. Çıktı özgün dilde transkripttir, özet veya çeviri değildir.
Metin üretmek için duyulmayan sözler tamamlanmaz. Belirsiz sözcük hizası,
çözülemeyen kişi ve üst üste konuşma görünür kalır. Exclusive diarization
hizalamayı kolaylaştırabilir; normal örtüşmeli çıktı saklanır ve tek kimliğe zorlanmaz.

Decision 6: 10 Eylül ek kararıyla toplantıdan otomatik kalıcı profil oluşturmanın
önceki en az 10 saniye tasarım eşiği, aynı toplantı akustik kümesine güvenle
atanmış temiz ve örtüşmesiz konuşmaların toplamının **20 saniyeden fazla** olması
şeklinde değişti. Tam 20 saniye yeterli değildir. Bu toplantı eşiği 001'in mevcut
kayıt/tanıma API'sini veya eşiğini değiştirmez. Ayrı konuşma aralıkları biriktirilir;
tek kesintisiz 20 saniyelik söz gerekmez. Aynı kaynak/kanaldaki zaman aralıklarının
birleşimi örnek sayısı üzerinden ölçülür: yeniden işlenen bağlam, tekrar gönderim,
aynı sesin tekrar seçilmesi, sessizlik ve kayıt boşlukları süreyi artırmaz.

Süre yeterliliği yalnız bir kapıdır. Toplanan kanıt ayrıca konuşmacı tutarlılığı,
Decision 13'teki toplantıya özel kayıt kalitesi ve güncel galeriye göre bilinmeyen kişi kararını sağlamalıdır.
Mevcut 0.55/0.45/0.10
kimlik eşikleri başlangıç referansıdır, toplantı verisinde garanti değildir.
`recognized` mevcut profile bağlanır; `ambiguous` otomatik kaydedilmez.
Yeterli sesi olmayan bilinmeyen kişi toplantıda `profile_pending` durumuyla kalır;
hafızaya kaydedildi denmez ve kısa olduğu için mevcut en yakın kişiye zorlanmaz.
Kısa konuşma metne çevirmeyi veya toplantı içinde konuşmacı etiketi taşımayı
engellemez. Sonraki temiz aralıklar geldikçe aynı kümenin kanıtı yeniden değerlendirilir;
yetersiz ses başlı başına bütün toplantı analizinin hata vermesine neden olmaz.

Toplantı tamamlanırken tenant kilidi altında güncel galeriye yeniden eşleme
yapılır; kişi hâlâ bilinmiyorsa tek kalıcı profil, kısa kaynak örneği ve izlenebilir
enrollment işi aynı işlemde oluşturulur. Eşzamanlı toplantı/yeniden deneme aynı
kanıttan iki profil yaratmamalıdır. Mevcut profilsiz `enroll` API'sini kör çağırmak
bu davranışı sağlamaz. Tanınan kişinin profilini otomatik genişletme yapılmaz;
yanlış eşleştirmeyle hafızanın bozulması önlenir. Profil başına 20 örnek sınırı korunur.

Decision 7: Toplantı ses kaynağı tamamlanma/iptalden sonra 7 gün, metin/zaman
çizelgesi ve toplantı kişi eşlemesi 30 gün tutulur; tamamlanmamış yükleme 24 saatte
sona erer. Aktif işin kaynağı silinmez; süre aşımı işi açık hatayla bitirir.
Kalıcı hafızaya seçilen temiz kısa örnek ayrı kayıttır ve profil yaşam döngüsüne
tabidir; bütün toplantıyı süresiz tutturmaz. Kaydı/transkripti silmek ile kalıcı
kişiyi silmek farklı işlemlerdir ve arayüz etkilerini açıkça belirtir.

Decision 8: Kaynak platformun bildirdiği katılımcı kimliği, toplantı içindeki
akustik konuşmacı kümesi ve kalıcı ses profili ayrı alanlar ve ayrı kanıt türleridir.
Doğrulanmış platform katılımcısı varsa kısa söz ona bağlanabilir; bunun için yeni
biyometrik profil oluşturmak şart değildir. Yalnız görünen ad, ses kaynağı kimliği
veya toplantı içi etiket kalıcı biyometrik kimlik kanıtı sayılmaz. Ortak oda
mikrofonu birden çok kişiyi taşıyabilir; karışık kaynakta konuşmacı ayrımı korunur.
Kaynak/kanal kimliği, zaman tabanı, örnek aralıkları, parça kimliği/sırası,
örtüşme, kesinti ve yeniden bağlantı bilgisi mevcutsa kaybolmadan iç porta taşınır.
Geç gelen veya tekrar işlenen parça kalıcı kanıtı iki kez artırmaz; düzeltmeler
sürümlenir ve geçici küme değişikliği mevcut ses profilini sessizce değiştirmez.

Decision 9: Sabit Python 3.13/FastAPI sınırı korunur. Kullanıcının seçtiği yerel
RTX 4060, bağımlılıkları ve model paketi kendi cihazında doğrulanan açık bir
geliştirme sağlayıcısı olabilir; Spark bağlantısı kesildiğinde sessiz fallback
yapılmaz. Yerel geliştirme, bağımsız araştırma deneyi ve üretim/Spark kabulü ayrı
kanıt olarak raporlanır. Python 3.12 CPU araştırma çıktısı varsa uygulama runtime'ı,
Python 3.13 uyumu veya ARM64/CUDA kanıtı sayılmaz. Teams bağlantısı bu yetenekte
uygulanmaz; 003 Draft kalır. Canlı ham Teams medya SDK'sının .NET/Windows Server
gereksinimi bu repoya alternatif backend veya .NET servis ekleme yetkisi değildir.

Decision 10: Kullanıcı isterse toplam katılımcı sayısını üst sınır bilgisi olarak,
gerçekte konuşan kişi sayısını ise ayrı bir kesin sayı beklentisi olarak girebilir.
Bu iki bilgi tek anlama gelmez: beş katılımcı bulunan toplantıda yalnız üç kişi
konuşabilir. İkisi de boş bırakıldığında model sayı tahmini yapar. Kesin konuşan
sayısı katılımcı sayısından büyükse girdi reddedilir; negatif, kesirli veya
geçersiz değerler tipli ve yerelleştirilmiş hata üretir. Elli kişi kalite hedefidir,
bu girdi veya galeri için yeni bir 50 kişi kotası değildir.

Toplantının bütününde geçerli sayı her analiz parçasının `num_speakers` değeri
olarak zorlanmaz; parçada yalnız konuşan alt küme bulunabilir. Sağlayıcıya sayı
bilgisinin aktarımı gerçek sözleşmede kapsamıyla kaydedilir. Son birleştirmede
beklentiyle akustik sonuç uyuşmazsa fark görünür kalır; en yakın iki sesi körce
birleştirerek, kısa kişiyi kayıtlı profile zorlayarak veya varsayımsal konuşmacı
üreterek sayı tutturulmaz. Sayı bilgisi kalite ve bilinmeyen kişi kapılarını geçirmez.

Decision 11: Elle isim vermek yalnız gösterim adını değiştirir; ses vektörünü,
akustik kümeyi veya kalıcı profil kimliğini değiştirmez. Kalıcı profile bağlanan
kişinin adı profil yazma izniyle güncellenir ve sonraki toplantılarda aynı kimlikle
görünür. `profile_pending` kişiye verilen toplantı adı, kalite kapıları geçilene
kadar biyometrik profil oluşturmaz; uygun otomatik kayıt oluşursa seçilen adı
taşır. Aynı görünen adı iki kişiye vermek onları birleştirmez. Boş/geçersiz/izin
dışı ad değişimi reddedilir; eşzamanlı değişim açık çatışma veya güncel sürüm
sonucuyla ele alınır. Model kişinin gerçek adını sesten bulduğu izlenimini vermez.

Decision 12: Gerçek beş kişilik A kaydı, kısa ECAPA kalite reddinin toplantı
kimliğini de kopardığını gösterdi: 11 geçici küme, sıfır profil. Aynı sabit
Community-1 paketinin `embedding` bileşeniyle üretilen 256 boyutlu merkezler,
toplantı içi eşleştirme için ayrı tutulur. Native çıktıdaki satır/etiket sırası,
boyut ve sürüm gerçek modelden doğrulanmıştır. İlk üç parçanın sonradan kaynakla
denetlenen saf çiftlerinde aynı kişi benzerliği en az 0,7458, farklı kişi en çok
0,2711 bulundu; bu küçük keşif 50 kişi doğruluk kabulü değildir.

Bu 256 boyutlu temsil yalnız toplantı kümesini izler; 192 boyutlu ECAPA kalıcı
profiline dönüştürülmez, kesilmez veya onunla karşılaştırılmaz. Model/sürüm
kimliğiyle ayrı nullable sütunlarda saklanır ve sonuç süresi dolunca diğer özel
kanıtlarla temizlenir. Mevcut checkpoint'lerde alan yoksa eski güvenli davranış
korunur. Yeni izleme temsilinde de mutlak 0,55 eşleşme, 0,45 bilinmeyen ve 0,10
aday farkı uygulanır; eşzamanlı konuşma veya belirsiz model kararı kör birleşme
yapmaz. İzleme başarısı tek başına temiz konuşma süresini artırmaz veya hafızaya
yazma izni vermez; Decision 6 ve mevcut kalıcı kişi politikası ayrıca geçerlidir.
Özel HTTP sözleşmesi bu bileşeni açık biçimde etiketler; vektörler genel API,
tarayıcı, log veya Git kanıtlarına konmaz. Gerçek A/B/D/C denemesi değişmeden
yeniden çalıştırılır; ilk başarısız koşum korunur.

## İşlevsel gereksinimler ve sözleşme

Decision 13: Gerçek sabit A denemesinde kısa ECAPA pencerelerinin bütün çiftlerini
0,55 üstünde tutma koşulu temiz kişileri de reddetti. Bu koşul 001'in mevcut
tek kayıt akışında korunur; yeni toplantı kanıtı ayrı uygulama portu ve
`meeting-natural-context-v1` işleme sürümüyle değerlendirilir. İkinci kez
Community çalıştırıp yalnız etiket sayısını kontrol etmek, karışık negatif
kontrolleri geçirdiği için kalite kapısı olarak kabul edilmedi.

Yeni adaylar temiz sayılmış aralıklardan ayrı tutulur.
Bir kişinin aday manifesti kaynak sırasındaki ilk 256 örtüşmesiz bağlamla sınırlıdır;
son doğrulama bu manifestten en çok 60 saniyelik özgün ses seçer. Aynı etiketin arada başka
ses veya örtüşme olmayan en çok bir saniyelik doğal boşlukları bağlama katılabilir;
bağlamlar 3–8 saniyedir. Sessizlik yalnız bağlamdır, konuşma süresi değildir.
Her özgün bağlamın 256 boyutlu WeSpeaker temsili atanmış toplantı merkezine en az
0,55 benzerlik ve diğer merkezlere göre en az 0,10 fark sağlamalıdır. Bağlam
içindeki üç saniyelik kontrol pencereleri de aynı koşulları sağlamalıdır.
Ek 1,5 saniyelik pencereler 0,5 saniye adımla incelenir: başka bir merkezin
benzerliği en az 0,45 ve atanmış merkeze göre farkı en az 0,10 ise bu pencerenin
örnekleri elenir. Bu bir belirsizlik vetosudur; diğer kişiye atama yapılmaz ve
0,55 tanıma eşiği düşürülmez. Yalnız 1,5 saniyelik pencerenin düşük mutlak
güveni, alternatif kanıt yokken bütün kişiyi reddettirmez. Doğal bileşenin
son 0,25 saniyesi geçiş koruması olarak kanıttan çıkarılır; bu kesinti iç sekiz
saniye sınırlarına veya her VAD aralığına uygulanmaz. Sessiz, kırpılmış,
örtüşen ve rakip kişiye ait aralıklar süreye katılmaz. Aynı PCM içeriği bağımsız
bağlam sayısını artırmaz. Yeni profil için en az üç farklı, örtüşmesiz bağlam ve
doğrulama sonrasında 20 saniyeden fazla tekil konuşma gerekir. Daha kısa, kaliteli
kanıt yalnız mevcut kişiyi tanımada kullanılabilir. Tekrarlı ve farklı sesli
karışımlar ayrıca negatif kontrol olarak ölçülür; bu model kararı mutlak saflık
kanıtı veya 50 kişi doğruluk garantisi değildir.

Özel doğrulama girdisi en çok 60 saniyelik mono PCM WAV, özgün bağlam/ses
aralıkları, atanmış merkez ve rakip merkezlerdir. Sunucu kaynak örnek haritasını
korur. Yanıt girdi hash'i, seçilen bağlam indeksleri, doğrulanmış örnek aralıkları,
çıktı örneğinin hash'i, iki gerçek modelin vektör/sürüm bilgisi ve kalite durumunu
taşır. Vektörler yalnız seçilen son örnekten üretilir. Sunucu kaydettiği örneğin
hash'ini ayrıca doğrular; yeniden örnekleme sınırları içeri doğru yuvarlanır.
Yanlış sürüm/hash/aralık veya kalite reddi daha kolay eski yola geri düşmez.

Mevcut kalıcı profil kimliği, adı, yaşam döngüsü ve 192 boyutlu ECAPA alanı
korunur. Yeni toplantı profiline ek nullable 256 boyutlu temsil, Community paket
kimliği/sürümü, işleme sürümü ve tenant kapsamlı kaynak kayıt referansı eklenir.
Bu alanlar birlikte dolu veya birlikte boş olmalıdır. 192 boyutlu temsil de
gerçek seçilen örnekten hesaplanır; 256 boyuttan dönüştürülmez. İki uzayın sayısal
skorları birbirine karıştırılmaz. Toplantı eşlemesi aynı model/sürüm/işleme
popülasyonundaki 256 boyutlu temsili kullanır; 192 boyutlu galeri eski profilleri
tanımak ve çelişki/çift kayıt önlemek için ayrı değerlendirilir. İki uzay farklı
kişiye işaret ederse veya ilgili popülasyon belirsizse otomatik kayıt yapılmaz.
Yeni kişi kararı iki popülasyonda da bilinmeyen olmalıdır. Tanınan kişinin
vektörleri ve örnek sayısı kendiliğinden değişmez. Eski aday alanı olmayan
checkpoint'lerin eski güvenli davranışı korunur.

Değerlendirmede her yeni profil için kaynakla ölçülen tutulmuş konuşma saflığı
en az yüzde 99 olmalı; en kötü yabancı konuşma süresi ayrıca raporlanmalıdır.
Bu sıfır toleranslı kaynak ölçümü model güven skoru değildir. Sabit A/B/D/C,
bağımsız sorgular ve başarısız negatif kontroller sonuçtan çıkarılmaz. Bu kapı
geçilmeden kalıcı hafıza doğruluğu tamamlandı veya 50 kişi için kabul edildi denmez.

Decision 14: Sabit 182,025 saniyelik A kaydının bütün bağlamıyla, sayı ipucu
verilmeden yapılan gerçek Community denemesi beş kişi verdi; önceki 60 saniyelik
parçalar aynı kayıtta altı veya on bir küme üretmişti. Ölçülen çıkarım yaklaşık
6 saniye ve en yüksek ayrılmış GPU belleği 2,11 GB oldu. Yerel toplantı analizi
bu nedenle 300 saniyelik ana pencere ve iki yanda en çok beş saniyelik bağlam
kullanır. 310 saniyelik sınır bağımsız doğrulanır; bütün dört saatlik ses tek
isteğe yüklenmez. Örnek hafızası 60 saniyeyle sınırlı kalır. Kaynak byte/süre
limitleri, checkpoint, özgün zaman sahipliği ve tekrar saymama kuralları değişmez.
Özel taşıma sınırı, model/şema doğrulayıcıları, bellek ölçümleri ve uzun kaynak
testleri bu yeni sınıra birlikte taşınır. Tek ana pencereye sığan toplantıda kesin
konuşan sayısı varsa bütün kapsam için kullanılabilir; çok parçalı toplantının
kesin sayısı her parçaya zorlanmaz. Ayrı ASR modeli kendi iç kısa pencerelerini
kullanır; değişiklik gerçek 4060 çalışma ve kaynak bellek ölçümüyle doğrulanır.
Pencere boyutu toplantı oluşturulurken kaydedilir. Bu alanı taşımayan eski
toplantılar 60 saniyelik özgün ana pencereleriyle devam eder; güncelleme,
yeniden deneme veya işlem yeniden başlatma mevcut checkpoint'in kaynak
sınırlarını yeniden yorumlayamaz. Eski 0–239 checkpoint indeksleri korunur.
En yüksek 310 saniye/192 kHz kaynağın gerçek özel HTTP taşınmasında, 119 MB
istek ve 8,2 MB yanıtla yürütücü belleği 223,54 MiB ölçüldü. Bu ölçüm veritabanı
checkpoint yazımını kapsamaz. Ek çalışma payı için yürütücünün Kubernetes
bellek isteği 256 MiB, sınırı 512 MiB olur; bütün işin küme yük testi ayrıca
gerekir. Bu değişiklik model belleği veya Spark kapasitesi iddiası değildir.

Decision 15: Sabit A/B/D/C kaynaklarının sayı ipucusuz karşılaştırmasında
Community kümeleme ayarı `Fa=0.15`, `Fb=0.8`, `threshold=0.6` ve
`segmentation.min_duration_off=0.0` seçildi. A'nın on bir yerel etiketi mevcut
Decision 12 akustik politikasıyla beş kişide birleşti; B beş, kısa altıncı kişiyi
içeren D altı, yeterli altıncı kişiyi içeren C altı akustik kişi verdi. Birleştirme
ses benzerliği, fark ve örtüşme kontrolüne dayanır; gerçek kaynak kimlikleri
yalnız sonuç denetiminde kullanılır. Doğal bağlamlar bu eşlemeden sonra oluşur;
aynı kişiye ait yerel etiket sınırları kullanılabilir sesi kaybettirmez.
Özel parça sonucu, `silero-vad` / `6.2.1` kimliği ve
`e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720`
model hash'iyle üst düzey `vad` nesnesini taşır. Kimlik otoritesi
`app/inference/voiceup_inference/model_bundle.py` içindeki sürüm ve
`silero/silero_vad.jit` girdisidir. Aralıklar 16 kHz özel parça zamanında
sıralı, örtüşmesiz saniyelerdir; sunucu bunları ve ham konuşma aralıklarını
özgün kaynak örneklerine içe yuvarlayarak dönüştürür. Adaylar bütün yerel
etiketler akustik kişilere eşlendikten sonra oluşturulur; özgün yerel etiket
örtüşmeleri ve eşlenmemiş/rakip konuşma aralıkları birleşmeye engeldir.
Bir saniyeyi aşmayan engelsiz boşluklar doğal bağlamı bağlayabilir; boşluğun
kendisi konuşma sayılmaz. 3–8 saniyelik bağlamlar yalnız kendi kaynak ana
bölgesinden alınır; bileşenin son 0,25 saniyesi ses kanıtından çıkarılır.
Ana bölgeye kırpılınca üç saniyenin altına inen aday korunmaz. `vad` nesnesi
mevcutsa boş aralık listesi veya eksik izleme vektörü eski kalite yoluna
dönüş sağlamaz. Yeni kaynak hash'i/sürümü ve açık aday listesi kaydedilir;
adaylar doğrulanmış konuşma süresini artırmaz. Yalnız `vad` alanı bulunmayan
eski özel sonuçlar önceki aday sözleşmesiyle işlenir. Kaynak sırasında ilk
256 örtüşmesiz aday sınırı korunur.
Model ağırlıkları ve vektör uzayı değişmez; çıkarım tarifi
`community-vbx-fa015-v1` olarak özel sonuçta kaydedilir. Bu ayar tek başına
kalite kabulü değildir: 32 saniyelik karışık negatifte kalan yabancı ses
açığı kapatılmadan yeni hafıza yolu çalışan uygulamada etkinleştirilmez.

Decision 16: Bir kişinin merkezine yakın olmak, örnekte ikinci kişi olmadığını
göstermedi. Son seçilen PCM üzerinde bağımsız ikinci ses vetosu uygulanır.
İki saniyelik pencereler 0,5 saniye adımla incelenir; en az bir saniye VAD sesi
olmayan ve aynı PCM içeriğini tekrarlayan pencereler destek sayılmaz. Normalize
256 boyutlu WeSpeaker vektörleri en uzak çiftle başlatılan, en çok yirmi adımlı
deterministik küresel iki-ortalama yöntemiyle incelenir. Her alt kümenin kendi
merkezine en az 0,55 benzerlik ve diğerine göre en az 0,10 fark gösteren en az
iki örtüşmesiz, farklı PCM penceresi ve üç saniye tekil VAD sesi bulunmalıdır.
Bu iki destekli merkezin benzerliği mevcut aynı kişi eşleşme sınırı 0,55'in
altındaysa bütün aday reddedilir; parçaları iki yeni profile ayırma yapılmaz.
Boş, desteksiz veya birbirine yakın iki alt küme tek başına ret nedeni değildir.
Veto reddinde vektör, doğrulanmış süre/aralık ve çıktı hash'i yayımlanmaz.

İlk 0,45 merkez sınırı 17 kontrolden üçünü kaçırdı ve başarısız olarak korundu.
Ayrı, sonuçlardan önce dondurulan 0,55 deneyi 48 kontrolün tümünde beklenen
kararı verdi: kırk temiz örnek korundu, altı ham karışım ve iki gerçekten hatalı
seçilmiş örnek reddedildi. On iki konuşma önceki veto ayarında kullanılmamış
farklı kayıtlardır; B/C ve diğer kontrollerin kaynak örtüşmeleri raporlanır.
Bu sınırlı sonuç seçilen vetoyu uygulama adayı yapar; üretim uygulaması aynı
48 kontrolde ayrıca sınanır. Türkçe toplantı, tüm ses türleri veya elli kişi
için kusursuz doğruluk iddiası değildir. Aynı sabit A/B/D/C uygulama akışı ve
profil başına en az yüzde 99 kaynak saflığı kabulü ayrıca geçmelidir.

Decision 17: Kilitli Kubernetes hedefinde toplantı çıkarımı açık ve seçilebilir
bir Helm seçeneğidir; varsayılan kapalıdır ve mevcut pilot model/sağlık davranışı
korunur. Mevcut typed `runtime_profile` seçimi chart ve dört ortam/fixture
yüzeyine taşınır. Toplantı seçeneği yalnız doğrulanmış `x86_64-cu128` çalışma
zamanında açılabilir; Pod açık `kubernetes.io/os=linux` ve
`kubernetes.io/arch=amd64` seçicileri ile bir NVIDIA GPU ister. ARM64 pilot
seçimi toplantıyı kapalı tutar; ARM64 toplantı seçimi render sırasında reddedilir.
Bu yapı ARM64 toplantı bağımlılıklarını kabul etmez veya donanım geri dönüşü yapmaz.

Toplantı için ek, 4 GiB boyutlu bir model PVC'si kullanılır. Önceden hazırlanmış
ve sabit manifestlere uygun Community/Whisper paketleri bu diskin `diarization`
ve `asr` alt dizinlerinden `/models/diarization` ve `/models/asr` yollarına salt
okunur bağlanır; manifestler doğrulanmış x86_64 toplantı imajının içindedir.
Çalışma anında model indirme veya diski dolduran init container yoktur. İmaj,
mevcut iç registry ve değişmez digest yüzeyinden ayrıca seçilir. Tek mevcut
Secret referansı, kullanıcı yetkileri, sınırlı yazılabilir `/tmp`, kaynak
sınırları, ClusterIP ve dış ağı kapalı NetworkPolicy korunur.

Toplantı açıkken startup/readiness `/meeting-ready` uç noktasını, liveness
`/live` uç noktasını kullanır; pilotun `/ready` kontrolü toplantı hazır sayılmaz.
Bu sağlık uçları özel servis sınırında anahtarsız GET olduğundan Secret içeriği
probe'a taşınmaz. Pilotun 50 MiB/120 saniyelik ayarları değişmez; toplantı uçları
kendi 120 MiB/310 saniye ve 36 MiB hafıza sınırlarını uygular. Gerçek `lab` ve
`cluster` dağıtım bilgileri uydurulmaz; chart ve fixture geçişi L1 kanıtıdır,
gerçek Kubernetes/Spark çalışması ayrıca doğrulanmalıdır.

Decision 18: Gerçek C kaydında bir ASR kelimesi 105,02–117,68 saniye aralığına
yayıldı ve ardışık üç akustik kişiyi kapsadı. Sözcük olasılığının yüksek olması
bu zaman/kimlik belirsizliğini kaldırmaz. Örtüşme olmayan bir kelime aralığında
birden çok kişi konuşuyorsa ve en güçlü kişinin tekil konuşma desteği toplam
desteğin yüzde 80'ine ulaşmıyorsa metin korunur, kişi boş ve belirsizlik açık
olur. Örtüşme yokken kişi normal konuşma desteğinden seçilir; exclusive çıktının
kısa rakip aralığı bu baskın kişiyi değiştiremez. Eşzamanlı konuşmanın mevcut
görünür örtüşme davranışı korunur. Aynı kişiye
ait ardışık kelimeler bir satıra birleştirilirken aradaki rakip konuşma aşılmaz;
ASR rakibin kelimelerini üretmediğinde onun süresi diğer kişiye mal edilmez.
Bu düzeltme referans kaydı veya değerlendirme eşiğini değiştirmez; başarısız
C koşumu korunur, aynı dört kaynak yeni ve boş bir test hafızasında tekrarlanır.

Decision 19: 11 Eylül doğruluk incelemesinde, önceki normalize merkezin yeniden
süreyle ağırlıklandırılmasının toplam vektörün büyüklüğünü kaybettiği doğrulandı.
Aynı üç kanıtın geliş sırası, sonraki sorgunun tanınmış veya belirsiz olmasını
değiştirebiliyordu. Toplantıya özgü 192 ve 256 boyutlu merkezlerin her biri için
ayrı toplam kanıt ağırlığı ve ağırlıklı vektör toplamının normu, sürümlü özel
`props` içinde korunur. Yeni katkı yalnız tekil, sahip olunan kaynak süresidir;
vektör üretilemeyen süre o vektörün ağırlığına katılmaz. Güncelleme önceki
normalize vektörü saklanan normla çarpar, yeni ağırlıklı kanıtı ekler ve ancak
sonra normalize eder. Vektör, norm, ağırlık ve kaynak aralıkları aynı mevcut
transaction içinde yazılır. Sıfır/tekrar kanıt merkezi değiştirmez; geçersiz veya
desteklenmeyen mevcut durum sessizce sıfırlanmaz, model uyuşmazlığı olur.

Eski kayıtlarda kaybolmuş norm geri üretilemez. Durum bulunmayan eski merkez,
mevcut kayıtlı süresi kadar ağırlıklı tek başlangıç gözlemi olarak alınır ve
`legacy_centroid_seed` kökeni korunur; geçmişin tam toplamı hesaplanmış sayılmaz.
Yeni kaynak geçmişi `source_resultant` kökenini taşır. Kalıcı profil örnekleri,
eşikler, model kimlikleri ve kaynak/örtüşme birleşme kuralları değişmez. Bu
düzeltme merkez üzerinden zincirleme yanlış birleşmenin bütün nedenlerini
çözmüş sayılmaz; ayrı yanlış birleşme/bölünme incelemesi ölçümde görünür kalır.

Decision 20: Doğruluk değerlendirmesi yalnız kaynak aralığı uyuşmasına dayanmaz.
Resmî referansı bütünüyle mevcut konuşmalarda kişi başına kronolojik metin
birleştirilir; bütün kişi eşlemeleri içindeki en küçük kelime ekleme, silme ve
değiştirme toplamı, bütün referans kelimelerine bölünerek kişi eşlemeli kelime
hata oranı (`cpWER`) hesaplanır. Eksik veya fazla kişi boş akışlarla, kişisi
belirsiz metin ayrı bir hipotez akışıyla hesaba katılır. Ayrıca belirsiz akışı
gerçek kişiye eşlemeyen hata ve belirsiz kelime oranı ayrı raporlanır; çekinme
metni veya zor örnekler paydadan çıkarılmaz. Normalizasyon, kaynak/çıktı
hashleri, eşleme ve hesaplama sınırları deneyden önce sabitlenir. Resmî metnin
yalnız bir kısmının çalındığı, zaman hizası bulunmayan kesite tam referans
uydurulmaz; bu kaydın metin doğruluğu ölçülmediği belirtilir.

Önceden model/ayar seçiminde kullanılan A/B/C ve tarihsel test grupları
regresyon verisidir. Yeni kişi değerlendirmesi için bunlarla kişi, kaynak parça
ve hash çakışması bulunmayan veri ayrılır; seçim model sonucuna göre değişmez.
5/10/20/50 kişi kapsamı, ilk kayıt başarısı, doğru/yanlış kimlik, çekinme ve yeni
kişi hatası ayrı paydalarla görünür olur. İngilizce sesli kitaplar üzerindeki
sonuçlar Türkçe doğal toplantı veya eğitim verisiyle kişi bağımsızlığı kanıtı
değildir. Yeni bir çıkarım tarifi ancak değişmeyen regresyon kaynakları,
ayrılmış değerlendirme ve kaynak sınırlarında ölçüldükten sonra uygulanır;
referans metin çıkarıma veya profil kabul kararına verilmez.

Decision 20'nin bağımsız kişi seçimi ve değişmez kaynak üretimi, model çalışmadan
önce [corpus-protocol.md](corpus-protocol.md) içinde dondurulur.

Decision 21: Elli kişi incelemesinde bir belirsiz sonucun hangi modelden ve hangi
eşikten kaynaklandığı mevcut son karar alanından ayırt edilemedi. Kullanılabilir
hafıza kanıtı eşleştirilirken her modelin döndürdüğü en fazla iki benzerlik skoru,
kendi karar/sebep değeri, sabit model kimliği ve kullanılan politika, sürümlü
özel karar izi olarak toplantı konuşmacısının `props` alanında saklanır. İki
modelin ilk adayının aynı olup olmadığı yalnız nullable boolean olarak yazılır;
aday profil kimlikleri, kişi adları, vektörler, ses veya metin bu ize eklenmez.
İz son karar ile aynı tenant/fencing/izin denetimli transaction içinde oluşur;
tekrar tamamlanmış sonucu değiştirmez. Önceki kayıtların eksik izleri bugünkü
galeriyle geriye dönük doldurulmaz. Kalite nedeniyle eşleştirme yapılmadığında
skor uydurulmaz. Bu değişiklik eşikleri veya iki modelin birleşme kararını
değiştirmez; karar nedenini ölçülebilir kılar. İz mevcut sonuç saklama/silme
kurallarına tabidir ve genel API/arayüzde yayımlanmaz.

Decision 22: Elli kişi kaydının sonlandırma aşamasında aynı WeSpeaker modelinin
her kısa kalite penceresinde GPU'ya taşınıp CPU'ya geri alındığı görüldü. Mevcut
özel istek kilidi bütün model işini zaten tekilleştirir. Bir hafıza doğrulama
isteği boyunca model GPU'da tutulabilir; pencere seçimi, tek örnekli çağrı
sırası, batch boyutu, hassasiyet ayarları, kalite eşikleri ve üretilen kararlar
değişmez. Başarı veya hata sonunda kaynaklar CPU'ya döner; küresel hassasiyet
ayarları her durumda geri yüklenir ve kilit serbest kalır. İç içe veya eşzamanlı
yanlış kullanım açık hata olur. Değişiklik ancak aynı gerçek sabit örneklerde
eski/yeni vektörler, saklanan PCM hashleri ve kalite kararları karşılaştırılıp
GPU belleği ve süre ölçüldükten sonra etkinleştirilir. Model/bağımlılık kabulü,
özel HTTP sözleşmesi ve 20 saniye kalite koşulu değişmez.

Decision 23: Elli kişilik bağımsız A kaydında aynı kaynak parçasında modelin ayrı
bulduğu iki native etiket, uygulamanın yalnız benzerlik ve zaman örtüşmesine
bakan birleştirmesiyle aynı toplantı kişisine bağlandı. Bu kişinin kalıcı örneği
iki ayrı kaynağı yaklaşık eşit süre içerdi; bu başarısız kayıt ve test hafızası
korunur. Bütün ayrı native etiketlerin koşulsuz farklı kişi sayılması önce
yeniden oynatıldı ve reddedildi: eski başarılı A kaydı 5 kişiden 11'e, C kaydı
6 kişiden 8'e bölündü. Bu katı aday üretime alınmaz; ayrı native etiket tek
başına farklı kişi kanıtı değildir.

İkinci, önceden sabitlenen aday yalnız iki native etiketin de kullanılabilir
ECAPA192 kanıtı varsa ve bu iki vektörün benzerliği mevcut yeni-kişi eşiği
0,45'in altındaysa farklı kişilik kısıtı kurar. Eksik veya belirsiz ikinci-model
kanıtı farklı kişi diye yorumlanmaz. Bu sınır sonuçlara göre taranmaz veya
ayarlanmaz; aynı eski/yeni kaynaklarla karşılaştırılmadan etkinleşmez. Bütün
adaylarla mevcut benzerlik ve fark hesabı yapılır; bağımsız ayrım kanıtıyla
engellenen kazanan yerine düşük sıradaki bir adaya zorunlu atama yapılmaz.
Ortak kaynak bağlamıyla yeniden bağlantı da kanıtlanan ayrımı aşamaz. Parça
kimliği, model tarifi ve doğrulanmış native ayrım ilişkisi sınırlı, sürümlü
özel kanıt olarak saklanır; yeni parçalardaki aynı kişi eşleştirmesi mevcut
model politikasıyla sürer.

Aynı kaynak parçasında yukarıdaki bağımsız kanıtla farklı kişi olduğu doğrulanan
iki toplantı kişisi daha sonra tek kalıcı profile bağlanamaz. Mevcut zaman
örtüşmesi çatışmasına ek olarak doğrulanan kaynak ayrımı da son hafıza atamasında
denetlenir. Çatışan eşlemeler belirsiz
olur; başka profile zorunlu atama, mevcut örneği değiştirme veya yeni örnek
oluşturarak çatışmayı gizleme yapılmaz. Özel kanıt mevcut tenant, kaynak
fingerprint, transaction, yeniden deneme ve sonuç temizliği sınırlarını taşır.
Eski kayıtta bulunmayan kanıt bugünkü modelle uydurulmaz; geçersiz mevcut kanıt
sessizce yok sayılmaz. Yeni karar genel sözleşmedeki `ambiguous` ve
`inconsistent_audio` değerlerini kullanabilir; isim, ses veya özel etiketler
genel API'ye eklenmez.

Doğrulanmış ayrım, ayrı yaşam döngüsü olan yeni ilişki varlığı değil, mevcut
toplantı/parça kaynak kanıtının yeniden üretilebilir özel önbelleğidir. İlk
kanıtın model/sürüm, kaynak hash, parça, etiketler ve politika bilgisi korunur;
aynı toplantının `meeting_speaker_id` değerleri en fazla 999 karşı konuşmacı
içeren bir listede tutulur. Aynı kaynaktaki iki karşı kayıt simetrik ve mevcut olmalıdır. Bu
sınırlı kanıt için yeni ilişki tablosu veya SQL üzerinden JSON içi join/arama
oluşturulmaz; mevcut toplantı sahipliği ve transaction içinde tenant, eksik veya
silinmiş hedef ve karşılıklılık doğrulanır. Bu tercih, kalıcı iş ilişkilerinin
fiziksel yabancı anahtar sınırını değiştirmez. Önbellek kaynakla birlikte
temizlenir; doğrulanamayan eski kanıt atlanarak kullanılmaz.

Bu kural native modelin yanlış bölmesini düzelttiği iddiası değildir. Önceki
A/B/D/C ve uzun kayıt kaynakları ile yeni elli kişilik A kaynak eşlemesi,
değişmeyen model çıktıları üzerinden önce yeniden oynatılır. Saflık, yanlış
birleşme ve bölünme birlikte raporlanır. Sonra gerçek PostgreSQL/HTTP sınırları
ve boş bir hafızayla gerçek model koşumu doğrulanır; eski yanlış profil silinmez
ve yeni deneyin galerisine taşınmaz. Eşikler, kişi sayısı girdisi ve model
ağırlıkları bu düzeltmeyle değiştirilmez.

Decision 24: Yeni karışık kalıcı örnekte mevcut WeSpeaker256 kontrolü iki ayrı
grubu buldu ancak merkez benzerliği 0,626 olduğundan reddetmedi. Aynı kaynak
pencerelerini kullanan bağımsız ECAPA192 tanısı iki grubu 0,542 benzerlikle
ayırdı; ilk sabit karşılaştırmadaki 53 temiz örneği reddetmedi. Bu ilk bulgu
tek başına yeni kalite kuralını etkinleştirmez. Eski 48 kontrol ve yeni kaydın
bütün 37 kalıcı örneğinden oluşan, dosya hashleri sabit 85 vaka tamamlanır;
yinelemeler varsa açıkça sayılır ve bağımsız örnek diye çoğaltılmaz.

Sınanacak aday, son saklanacak PCM üzerinde mevcut ikincil-ses denetimini iki
model uzayında bağımsız uygular. İki saniyelik pencere, yarım saniyelik adım,
tekil PCM, en az bir saniye VAD, iki merkezli deterministik kümeleme, her grupta
iki örtüşmeyen pencere ve üç saniye konuşma desteği değişmez. ECAPA192 kendi
mevcut 0,55 tanıma ve 0,10 fark sınırlarını kullanır; iki merkez benzerliği
0,55'in altındaysa ve iki grup da destekliyse karışık ses reddedilir. Modellerin
vektörleri veya benzerlik skorları birbirine karıştırılmaz. Mevcut WeSpeaker
reddi korunur; herhangi bir bağımsız model yeterli ikinci-ses kanıtı bulursa
sonuç `inconsistent_audio` olur ve saklanacak hash, aralık veya kimlik vektörü
dönmez. Reddetme yeni kişi üretmez ve mevcut profili değiştirmez.

Aday ancak bütün sabit temiz kontroller korunup bütün bilinen karışımlar
reddedildiğinde, gerçek model/özel HTTP ve hata sınırları doğrulandığında
etkinleşir. Eşik taraması, kayıt değiştirme ve zor örnekleri çıkarma yapılmaz.
Gerçek cihazdaki süre/bellek artışı ve sınıra yakın vakalar ayrıca kaydedilir.
Bu kontrollere uyum, her gerçek toplantının karışımını bulma garantisi değildir;
yeni hafızayla elli kişi koşumu ve sonraki bağımsız toplantılar ayrıca ölçülür.

Requirement 1: `Toplantılar` ekranı dosya seçimini, kaynak süresini, aktarım
ilerlemesini, iptal davranışını ve onaylanan aktarım miktarını gösterir.
Desteklenmeyen format, boyut/süre sınırı, yetki ve bağlantı hatası yerelleştirilir.
Son dosya parçası doğrulanmadan analiz başlatılamaz. Sonuç ekranı konuşmacılı
metni, kişi kararını ve elle isim verme akışını sunar; mikrofon UI'si gerekmez.

Requirement 2: Toplantı oluşturma, sıralı parça aktarımı, aktarımı bitirip analiz
başlatma, durum/listeler, sayfalı konuşmacı/transkript, iptal ve başarısız işten
devam ayrı tipli HTTP sözleşmeleridir. Önerilen kök `/meetings`; son alanlar
gerçek sağlayıcı deneyiyle `contracts.md` içinde dondurulur. API, özel model
embedding'ini, dosya yolunu, iç anahtarı veya üçüncü taraf servis tokenini döndürmez.

Requirement 3: Yükleme parçası indeks, boyut ve SHA-256 ile eşleşir; aynı parça
aynı içerikle tekrar kabul edilir, farklı içerikle aynı indeks reddedilir.
Eksik/sırası bozuk parça varken tamamlanma olmaz. Opaque dosya anahtarı, kök
sınırı, symlink reddi, byte/süre/kanal/format doğrulaması ve yeterli disk denetlenir.
Tarayıcı yenilendiğinde dosya aktarımı ancak aynı kaynak ve sunucu manifesti
doğrulanarak sürdürülebilir; yüklenmemiş içerik varmış gibi işlenmez.

Requirement 4: Toplantı/parça işleri kalıcı PostgreSQL kuyruğunda lease ve artan
fencing token kullanır. Tamamlanan parça tekrar üretilmez; eski worker sonucu
geçerli sonucu ezemez. Aktarım, sırada bekleme, işleme, son birleştirme,
tamamlanma, hata ve iptal ayrı durumlardır. Başarısız parça tam başarıya çevrilmez.
Yürütücü toplantı işini sahiplenmeden önce özel `/meeting-ready` yanıtını
hizmet anahtarıyla, en çok beş saniye ve 16 KiB sınırları içinde denetler;
hazır durumu, sabit model kimlikleri ve Decision 15 kapsamındaki
`community-vbx-fa015-v1` tarifi doğrulanmalıdır. Eski checkpoint kimliğinde
tarifin isteğe bağlı olması yeni iş kabulüne uygulanmaz. Modelin soğuk açılışında
bağlantı yokken veya geçici 503 yanıtında iş kuyrukta kalır; deneme sayısı ve
sahiplenme sayacı artmaz. Pilot işler, temizlik ve sağlık işareti ilerlemeyi
sürdürür. Hazır yanıtından sonra başlayan gerçek model/iş hataları mevcut
sınırlı yeniden deneme davranışını korur; bu denetim hatalı işi sonsuz yeniden
denemeye dönüştürmez. Yanlış model kimliği ve kalıcı hazır olma hataları
gizlenmeden, ses veya anahtar içermeyen operasyonel hata olarak kaydedilir.

Requirement 5: Her sonuç satırı başlangıç/bitiş zamanı, toplantı konuşmacı kimliği,
varsa kaynak platform katılımcısı, ayrı nullable kalıcı profil kimliği/adı, metin,
dil, örtüşme ve karar durumunu taşır. İç sözleşme kaynak kimliği ile biyometrik
kimliği birbirine dönüştürmez. Kısa kişinin transkripti ve `profile_pending`
durumu, tanınmış kişi ve kalıcı kaydı tamamlanmış yeni kişiden ayrılır.
Kişinin adı değişse bile kimliği sabit kalır. Son birleştirmeden önce görülen
çıktı açıkça ara sonuçtur; son sürüm parça sınırındaki çift/kayıp sözleri önler.
Profil silinirse eski metin bir başka kişiye yeniden bağlanmaz.

Requirement 6: Toplantı kişi kümelerinden kaliteli ve örtüşmesiz kısa örnekler
çıkarılıp Decision 6'ya göre biriktirilir; kaynak aralıkları/hash/model sürümü izlenir.
Süre yalnız tekil kullanılabilir aralıklardan hesaplanır; yetersiz, karışık veya
belirsiz kanıt profili değiştirmez. Otomatik kayıt kullanıcının
`speaker_profiles:write` yetkisini ayrıca gerektirir. Kaydı başlatmada ve worker
sonlandırmada güncel tenant/izin/lifecycle durumu denetlenir. Hafıza yazımı
başarısızsa transkript mevcut olabilir fakat toplantının hafıza sonucu açık hata taşır.

Requirement 7: Yeni toplantı, aktarım parçası, analiz parçası, toplantı konuşmacısı
ve transkript/zaman çizelgesi tabloları aynı domain'e aittir; zorunlu audit/soft-delete
şekli ve tenant kapsamlı fiziksel foreign key'ler kullanılır. Aktif kalıcı profil,
kısa kaynak Recording, SpeakerJob ve SpeakerSample arasındaki mevcut bütünlük korunur.
Şema otoritesi SQLAlchemy, eklemeli migrasyon Alembic'tir; migrasyon model çalıştırmaz.

Requirement 8: Toplantı başlatma ve sonuç sözleşmesi isteğe bağlı katılımcı üst
sınırını, ayrı kesin konuşan kişi beklentisini, kullanılan sayı kapsamını ve
gözlenen akustik kişi sayısını ayrı taşır. Kesin alan adları/izin verilen teknik
sınırlar gerçek sağlayıcı sözleşmesiyle `contracts.md` içinde dondurulur.
Arayüz iki girdinin farkını TR/EN açıklar; sonuçta uyuşmazlık sessizce gizlenmez.
Parça işçileri global kesin sayıyı her parçaya kopyalamaz; tekrar istek aynı sayı
ayarlarını korur, aynı idempotency anahtarıyla değişen ayar çatışma üretir.

Requirement 9: Toplantı konuşmacısına elle ad verme gerçek tipli HTTP mutasyonudur;
tenant, toplantı erişimi ve kalıcı profil yazımı varsa `speaker_profiles:write`
izni denetlenir. Mevcut profil yeniden oluşturulmaz; ad değişimi audit bilgisiyle
kalıcılaşır. Sonuç sayfası/kişi listesi ve sonraki toplantı mevcut profil adını
gösterir. Bekleyen kişinin yalnız toplantı adıyla profil adı ayrımı görünürdür.
Ad alanı düz metindir; HTML/komut olarak yorumlanmaz ve ham ses/metin loglanmaz.

Requirement 10: Bağımsız gerçek konuşma parçalarıyla üç toplantılık kabul akışı
gösterilir. A toplantısında beş kişinin yeterli temiz kanıtından tam beş kalıcı
profil oluşur ve kullanıcı adları elle verir. B toplantısında aynı beş kişinin
farklı sözleri aynı profil kimliklerine ve adlarına bağlanır; toplam profil beş
kalır. C toplantısında bu beş kişi ve daha önce kaydedilmemiş altıncı kişi
konuşur; mevcut beş kimlik korunur ve kalite kapılarını geçen yeni kişiyle toplam
profil altı olur. İşi tekrar çalıştırma profil sayısını artırmaz; servis yeniden
başlatıldığında adlar ve eşlemeler korunur. Altıncı kişinin kanıtı yetersizse
`profile_pending` görünür; bunu başarılı altıncı profil kabulü diye raporlamak
veya eşiği gevşetmek yasaktır. Tanınan kişilerin örnekleri kendiliğinden büyümez.

## Güvenlik, çalışma ve dağıtım

JWT/tenant ve `meeting_analysis:read/run` izinleri bütün HTTP uçlarında uygulanır.
Otomatik hafıza yazımı ek profil yazma yetkisi ister; uygulama `super_admin` sınırları
korunur. Özel dosya ve ses içeriği loglanmaz; sunucu transkripti düz metin olarak
ele alır, içerikteki talimatları çalıştırmaz. Metin React tarafından kaçışlanır.

Spark sağlayıcısında 004'ün yetkili SSH tüneli ve iç HTTP anahtarı kullanılır.
Yerel geliştirme sağlayıcısı açık RTX 4060 seçimiyle aynı tipli uygulama portuna
bağlanır; kullanıcı sesi ve model çıkarımı yerelde kalır. Spark model servisi
veritabanını okumaz; kaynakları sınırlı, kimliği doğrulanmış aktarım ve parça
sözleşmesinden alır. İki Spark proxy'sinde yeni uçlar açık allowlist'e eklenir.
Gerekli dosya decoder'ı, model bağımlılıkları ve ağırlıkları yalnız kurulum/paketleme sırasında
resmî kaynaklardan hash ile alınır; çalışma anında indirme veya dış API yoktur.
Hugging Face tokeni kurulum sırrıdır; Git'e, tarayıcıya veya inference runtime'a taşınmaz.
Yetkili hazırlık seçilmiş sabit revision dosyalarını alır; tam yol/boyut/SHA-256
envanteri ve gerekli lisanslar doğrulanır. Yarım indirme veya bozuk paket hazır
sayılmaz. Hazır yerel paket doğrulanarak yeniden kullanılır; normal başlatma
internete bağlanmaz. Token URL/komut çıktısı/hata/log/manifest içinde bulunmaz.
ASR dosya hazırlığı `scripts/prepare-asr-model.py`, sabit envanter
`scripts/asr-model-manifest.json` ve gerçek dosya sınırı regresyonları
`tests/test_prepare_asr_model.py` ile izlenir. Erişim kapısız ASR paketinde token
okunmaz veya gönderilmez. Community-1 hazırlayıcısının güvenli no-replace yayın
ve tam paket doğrulama davranışı yeniden kullanılır; model hazırlamak yeni
kitaplık sürümlerini kendiliğinden kabul ettirmez.

Typed settings, tüm ortam yüzeyleri, depolama/worker/model volume'leri, kaynak
istekleri, Compose/Helm ve NetworkPolicy birlikte güncellenir. Readiness yeni
modelin gerçekten hazır olduğunu bildirir; eksik modelle sahte transkript veya
yerel GPU/CPU'ya sessiz dönüş yapılmaz. 001'in çalışan hazır durumu ayrı korunur.
Yerel, CPU ve Spark modlarında `scripts/stack.sh restart` backend veya frontend
servisini kapsıyorsa başarılı yeniden başlatmadan sonra Nginx'in mevcut etkin
yapılandırması doğrulanıp kesintisiz yeniden yüklenir. Böylece yeniden oluşturulan
servisin önceki IP adresi API erişimini bozmaz. Spark'ın özel dinleyicisini içeren
tek mevcut yapılandırması korunur; yeni geçici dosya veya ortam genişletmesi
üretilmez. Başarısız restart veya yapılandırma doğrulaması başarı sayılmaz;
diğer komutlar ve yalnız worker yeniden başlatması ek işlem yapmaz.
İzlenecek ölçüler: aşama/parça süresi, kuyruk yaşı, iptal/yeniden deneme sayısı,
RAM/GPU belleği, disk, örtüşme ve hafızaya yazılmayan kişi sayısı; kimlik/metin loglanmaz.
Önbellek N/A — ilk çözüm için kalıcı PostgreSQL checkpoint'i ve opak dosya deposu yeterlidir.
Harici toplantı entegrasyonu N/A — gelecekteki Teams kaynağına ait bilgi korunur;
bu Accepted yeteneğin yürütülen kaynağı kullanıcının yüklediği dosyadır.
Mikrofon yakalama N/A — kullanıcı dosya yüklemesini yeterli seçti; önceki kaynak
isteği ayrı mikrofon yeteneğine taşındı, geçmişten silinmedi.

## Test stratejisi ve kabul ölçütleri

Yeni davranışlar önce başarısız test, sonra gerçek uygulanmış davranışla doğrulanır.
Taşıma, dosya, HTTP ve PostgreSQL sınırlarında gerçek entegrasyon kullanılır;
sağlayıcı fikstürü gerçek sürümden kaydedilmiş şekle bağlanır, yalnız tüketiciye
uyan sahte yanıt çalışma kanıtı sayılmaz. İşaretli maddeler 11 Eylül 2026'daki
yerel gerçek HTTP/tarayıcı akışı ve otomatik sınır testlerinin kanıtına dayanır;
işaretlenmemiş cihaz, kalite ve süre hedefleri tamamlanmış sayılmaz.

- [x] Requirement 1–3: Gerçek tarayıcıda TR/EN dosya yükleme akışı; yetki/format/bağlantı hatası, son parça, iptal ve kaynak temizliği gözlenir.
- [x] Requirement 2–4: Tenant/izin/eksik parça/çelişkili tekrar/lease kesintisi/eski worker/iptal testleri gerçek HTTP, disk ve PostgreSQL ile geçer.
- [ ] Requirement 4–5: Parça sınırındaki konuşmada çift/kayıp çıktı olmaz; üst üste konuşma korunur, belirsiz söz yanlış kişiye zorlanmaz.
- [ ] Requirement 5–6: En az üç farklı kamu konuşmacısının bağımsız parçalarında gerçek Spark transkripti ve kişi ayrımı gözlenir; ikinci kayıtta kalıcı kimlik geri gelir, tekrar profil sayısını artırmaz.
- [x] Requirement 6–7: Tanınan kişi, yeni kişi, kısa/karışık/belirsiz kişi, eşzamanlı otomatik kayıt ve silinmiş profil ayrı test edilir; bütün toplantı kalıcı örneğe bağlanmaz.
- [x] Decision 6 / Requirement 5–6: Ayrı kısa aralıkların temiz toplamı tam 20 saniyeyken `profile_pending`, 20 saniyeyi aşınca diğer kapılar da geçerse otomatik kayıt görülür; örtüşme/boşluk/bağlam/tekrar süreyi artırmaz. Kısa kişinin metni korunur; 20 saniyeden uzun karışık veya belirsiz kanıt kalıcı profile dönüşmez.
- [x] Decision 8 / Requirement 5: Kaynak kimliği, toplantı kümesi ve kalıcı profil bağımsız doğrulanır; yalnız platform adı kalıcı kimliği birleştirmez, geç parça veya yeniden bağlantı kanıtı çift saydırmaz.
- [x] Decision 10 / Requirement 8: Sayı girdisi boş, yalnız üst sınır, kesin konuşan sayısı ve çelişkili/geçersiz değerler gerçek API/UI testlerinden geçer; beş kişilik toplantının tek/iki kişili parçasına beş etiket zorlanmaz. Sayı uyuşmazlığı kör birleşme olmadan gösterilir.
- [x] Decision 11 / Requirement 9: Elle ad verme TR/EN arayüzünde ve sıradan izinli kullanıcıyla çalışır; yenileme/yeniden başlatma/sonraki toplantıda korunur. İzin/tenant/sürüm çatışması, aynı adla iki ayrı profil ve bekleyen kişinin adı ayrı sınanır.
- [x] Requirement 10: Gerçek model, HTTP, PostgreSQL ve tarayıcı üzerinden A=5 yeni profil → elle isim → B=aynı 5 kimlik/ad → C=aynı 5+1 yeni kimlik akışı gözlenir; bağımsız sesler, tekrar ve yeniden başlatma sonuçları raporlanır. Dublör yanıtı veya aynı dosyayı yeniden yüklemek çapraz toplantı tanıma kanıtı değildir.
- [x] Decision 19: Ayrı 192/256 toplam norm ve gerçek katkı ağırlığı, sıfır/tekrar, eksik vektör, geçersiz durum ve eski başlangıç testleri geçer; gerçek worker yeniden oynatması ve son profil kapısı doğrulanır. [Kanıt](../../../../docs/evidence/2026-09-11-accuracy-audit/resultant-report.md).
- [x] Decision 20 ölçüm aracı: Tam referans, eksik/fazla/atanmamış kişi, Unicode genişlemesi ve çalışma sınırları korunur; bağımsız küçük permütasyon hesabı ve gerçek A/B/C kelime ölçümleri kaydedilir. Bu madde kişi ölçeği kalite hedefini tamamlamaz. [Kanıt](../../../../docs/evidence/2026-09-11-accuracy-audit/metrics-report.md).
- [x] Decision 21: Özel karar izi gerçek transaction, tenant, tekrar, temizlik ve genel yanıttan dışlama sınırlarından geçer; gerçek elli kişilik dönüş kaydında gözlenir. [Kanıt](../../../../docs/evidence/2026-09-11-accuracy-audit/memory-trace-report.md).
- [x] Decision 22: İstek sahipliği, hata ve hassasiyet temizliği sınanır; sabit GPU kontrollerinde 2.979 vektör birebir aynı kalır, süre/bellek ve dağıtılmış kaynak kimliği kaydedilir. [Kanıt](../../../../docs/evidence/2026-09-11-accuracy-audit/residency-report.md).
- [x] Decision 23: Bağımsız farklı ses kanıtı, yalnız bağlam, tam aday sırası, karşılıklı tenant/kaynak doğrulaması ve son kimlik çatışması gerçek PostgreSQL testleriyle korunur; eski beş kişilik akış ve taze galerinin bütün örnek denetimi geçer. Elli kişilik C'deki kalan yanlış birleşme açık tutulur. [Kanıt](../../../../docs/evidence/2026-09-11-accuracy-audit/native-exclusions-report.md).
- [x] Decision 24: Sabit 76 temiz ve 9 karışık örnekte iki bağımsız kalite kontrolü doğru izin/veto üretir; eski karışık örnek çalışan özel HTTP ucunda saklanabilir çıktı olmadan reddedilir. [Kanıt](../../../../docs/evidence/2026-09-11-accuracy-audit/dual-coherence-report.md).
- [ ] Decision 3–4: 1/2/4 saatlik kaynakta bellek kayıt süresiyle doğrusal büyümez; kesinti/devam, disk ve işleme/ses süresi oranı raporlanır.
- [ ] Kalite: 5/10/20/50 toplantı kişisi ve 50/100/200 kayıtlı kişi havuzu ayrı ölçülür; kimlik precision/recall/F1, ilk kayıt kapsamı, konuşmacı ayrım hatası, kelime hata oranı ve kişi atamalı metin hatası raporlanır. Başarısız veya çözülemeyen kişiler paydadan çıkarılmaz.
- [ ] Tam profil kapısı, üretilmiş OpenAPI/tipler, migrasyon/history/drift, güvenlik, chart ve gerçek Spark/browser kanıtı kaydedilir; temsilî Türkçe veriyle L3 kabulü ayrıca alınır.

Open Question 1: Community-1 erişimi ve sekiz dosyalı lisans/boyut/hash paketi
doğrulandı. Seçilmiş ASR paketi de altı sabit dosyayla hazırlandı. Yerel x86_64
bağımlılık kapanışı, bağımsız inceleme ve 211 koordinatlı kabul kaydı tamamlandı;
gerçek özel HTTP/GPU çalışması gözlendi. Bu hazırlık sorusu yerel sağlayıcı için
çözüldü; Spark uyumu ve gerçek toplantı kimlik kalitesi ayrı açık kabul maddeleridir.
Open Question 2: Kontrollü Türkçe çok konuşmacılı kalibrasyonla dondurulacak diarization, kelime ve kişi atamalı metin hata hedefleri; 001'in hedefi bu farklı görevlerin yerine geçirilmez.
Open Question 3: Spark ARM64/Python 3.13/TorchCodec/CUDA kapanışı ve üretim bağımlılık
kabulü. Açık yerel RTX 4060 geliştirme deneyi bu eksikleri kapatmış sayılmaz.
Open Question 4: Kaynak seçimi kullanıcı tarafından çözüldü: yüklenen kayıt
yeterli. Teams bağlantısının doğrudan kayıt/döküm alma biçimi bu teslimde bir
engel veya zorunlu kabul adımı değildir.

Birincil kaynaklar: [Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1),
[Whisper large-v3](https://huggingface.co/openai/whisper-large-v3),
[seçilmiş CTranslate2 model kartı](https://huggingface.co/Systran/faster-whisper-large-v3/blob/edaa852ec7e145841d8ffdb056a99866b5f0a478/README.md),
[tarayıcı kayıt standardı](https://www.w3.org/TR/mediastream-recording/),
[Teams ayrı ses tamponları](https://microsoftgraph.github.io/microsoft-graph-comms-samples/docs/bot_media/Microsoft.Skype.Bots.Media.AudioSocketSettings.html),
[Graph döküm sözleşmesi](https://learn.microsoft.com/en-us/graph/api/calltranscript-get?view=graph-rest-1.0),
[Teams medya SDK gereksinimleri](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/calls-and-meetings/requirements-considerations-application-hosted-media-bots).
