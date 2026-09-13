# Konuşmacı ve toplantı tarayıcı senaryoları

Kapsam [Accepted PRD](../../specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md) ile tanımlıdır.
`scripts/e2e.sh speaker-identity` mevcut ortak harness ve kabul edilmiş çevrimdışı tarayıcı paketini kullanır.
Paket bulunamadığında bu engel raporlanır; genel npm kayıt deposuyla sessiz geçiş yapılmaz.

Gerekli yerel test ayarları:

- `APP_E2E_BASE`: SPA ve API'yi birlikte sunan adres; bu pilot için `http://127.0.0.1:8081`.
- `APP_E2E_SUPER_ADMIN_USER` / `APP_E2E_SUPER_ADMIN_PASS`: yalnız yerel test yöneticisi.
- `APP_E2E_READER_USER` / `APP_E2E_READER_PASS`: `speaker_profiles:read` ve `speaker_analysis:read` izinleri olan sıradan hesap; yazma, analiz başlatma veya super-admin yetkisi olmamalıdır.
- `APP_E2E_ENROLL_AUDIO`: en az 10 saniye kullanılabilir konuşma içeren tek konuşmacılı ses dosyasının mutlak yolu.
- `APP_E2E_OTHER_AUDIO`: yanlış kişiye örnek ekleme ve bilinmeyen ses denemesi için farklı bir kişiye ait temiz kayıt.
- `APP_E2E_EXPECT_DEVICE`: isteğe bağlı cihaz öneki; 4060 denemesinde `cuda`.
- `APP_E2E_CAPACITY_USER` / `APP_E2E_CAPACITY_PASS`: ayrı test tenant'ında, profil okuma/yazma ve analiz okuma/başlatma izinleri olan sıradan hesap. Tenant en az 50 test profili içerir; ilk sayfada 20 örnek sınırına ulaşmamış bir profil bulunur. Değişken adları mevcut fikstür bağlantısını korur; güncel ürün kotası tanımlamaz.
- `APP_E2E_CAPACITY_JOB`: aynı tenant'ta son işler sayfasında bulunan, terminal `failed/profile_limit` durumundaki mevcut test işinin public kimliği.

`02-read-only.mjs` gerçek girişle iki dilde salt okunur sayfaları, gizli yazma alanlarını,
yenilemeyi ve çıkışı doğrular. `01-local-pilot.mjs` gerçek yükleme, bozuk/sessiz ses,
kalıcı iş, profil oluşturma, ad değiştirme, tanıma ve silme akışını doğrular; oluşturduğu
profilleri ve kullanılmayan kayıtları `finally` yolunda public API üzerinden temizler.
Doğru ek örnek kabulünü, yanlış kişiden örnek eklemenin reddini, örnek sayısının korunmasını
ve kayıtlı olmayan konuşmacının kimliğe bağlanmamasını da denetler.

`03-profile-capacity.mjs`, Decision 11'in kota kaldırma davranışını iki dilde gerçek
giriş, API'deki aktif toplam gösterimi, 50 ve üzerindeki toplamda yeni profil
alanlarının açık olması, mevcut profile örnek ekleme seçimi ve sayfalama üzerinden
doğrular. `max_profiles` alanının bulunmadığını ve toplamın yalnız ilk 20 satırdan
hesaplanmadığını denetler. Eski `profile_limit` işinin geçmiş kural nedeniyle
reddedildiği açıklanır; bugünkü profil sınırı gibi gösterilmez. Sağlanan izole
fikstürleri yalnız okur; profil, ses veya iş oluşturmaz/silmez ve son profil/iş
yanıtlarını başlangıçla karşılaştırır. Fikstür kurulumu ve kaldırılması koşucuya
ait değildir; gerçek kişi verisiyle çalıştırılmamalıdır. Bu senaryo gerçek yeni
kayıt tamamlanması veya 50/200 kişilik tanıma doğruluğu kanıtı değildir.

Ses dosyasının kendisini yeniden tanımak bağlantı kontrolüdür; ayrı oturum doğruluk deneyi
değildir. Tekrarlanmış resmi test klibi kullanılabilir, ancak bunun oluşturulmuş fixture
olduğu koşum raporunda belirtilmelidir. Gerçek kullanıcı veri seti olmadan beş kişilik
tanıma hedefi tamamlanmış sayılmaz.

Toplantı senaryoları [Accepted 002 PRD](../../specs/speaker-identity/PRDs/002-long-recording-analysis/PRD.md)
kapsamındadır. Aynı `speaker-identity` koşucusuna kayıtlıdır; ek paket veya tarayıcı sürümü seçmez.

- `APP_E2E_MEETING_USER` / `APP_E2E_MEETING_PASS`: boş ve yalnız test için ayrılmış tenant'ta sıradan hesap; `meeting_analysis:read`, `meeting_analysis:run`, `speaker_profiles:read`, `speaker_profiles:write` izinleri gerekir.
- `APP_E2E_MEETING_READER_USER` / `APP_E2E_MEETING_READER_PASS`: aynı test tenant'ında yalnız toplantı/profil okuma izinleri olan sıradan hesap.
- `APP_E2E_MEETING_AUDIO_A`: beş kişinin yeterli temiz konuşmasını içeren gerçek ses kaydı.
- `APP_E2E_MEETING_AUDIO_B`: aynı beş kişinin farklı sözleri; A'nın tekrar kopyası olmamalıdır.
- `APP_E2E_MEETING_AUDIO_D`: aynı beş kişi ve hafızaya yetecek kadar konuşmayan yeni altıncı kişi.
- `APP_E2E_MEETING_AUDIO_C`: aynı altı kişinin, yeni kişiyi kaydetmeye yetecek temiz konuşması.

`04-meeting-upload.mjs` iki dilde gerçek oturum, sayı girdisi, bozuk dosya,
yükleme yenileme, gerçek hashli parça manifestiyle devam, yanlış dosyayı reddetme,
iptal, silme ve salt okunur izinleri sınar. Sonuç uydurmaz; bozuk ses model doğruluğu kanıtı değildir.
`05-meeting-memory.mjs` gerçek modellerle A→B→D→C akışını, elle ad vermeyi,
aynı profil kimliklerini, yetersiz yeni kişinin beklemesini ve 5→5→5→6 profil sayısını sınar.
Bu kayıtlı senaryo için ses fixture'ları İngilizcedir; formda konuşma dili `en` seçilir.
Koşum sonunda yalnız oluşturduğu toplantı/profil kimliklerini public API ile temizler.
Kaynakların lisansı, insan sayısı ve bağımsızlığı koşum protokolünde ayrıca belgelenmelidir;
temiz birleştirilmiş kaynakların geçmesi doğal toplantı veya 50 kişi doğruluğu garantisi değildir.

`06-meeting-observation.mjs`, kalıcı profil oluşturamayan tamamlanmış bir gerçek
model sonucunu salt okunur inceler. `APP_E2E_MEETING_OBSERVATION_USER` / `_PASS`
sıradan hesabı, `_ID` mevcut toplantı kimliğini, `_TRACKS` beklenen gözlenen
etiket sayısını (1–20), `_GALLERY=0` ise boş profil hafızasını belirtir. Ekranı
iki dilde gerçek API sayılarıyla karşılaştırır, veriyi değiştirmez; doğruluk
veya başarılı hafıza kabulü değildir. Çıktı yalnız sayısal ölçüleri saklar;
metin, ad, vektör veya kimlik doğrulama bilgisi rapora yazılmaz.

`07-modern-workspace.mjs`, [Accepted 008 PRD](../../specs/speaker-identity/PRDs/008-modern-workspace/PRD.md)
için gerçek şifreli girişten sonra ortak çalışma alanını iki dilde ve 1440/390
piksel genişlikte inceler. `APP_E2E_WORKSPACE_USER` / `APP_E2E_WORKSPACE_PASS`,
toplantı, profil ve ses analizi okuma izinlerinin üçüne sahip sıradan salt okunur
test hesabını belirtir; yazma/başlatma ve super-admin izinleri bulunmamalıdır.
Klavye ile içeriğe geçişi, etkin gezinmeyi, yazma formlarının yokluğunu, yatay
taşmayı ve konsol/HTTP hatalarını denetler. İsteğe bağlı
`APP_E2E_WORKSPACE_MEETING_ID`, aynı test tenant'ındaki tamamlanmış, metin ve
konuşmacı içeren mevcut bir toplantı sonucunu ek olarak gözler; verilmezse bu
adım çalıştırılmış sayılmaz. Hesap veya biyometrik fixture oluşturmaz, mevcut
veriyi değiştirmez; `finally` yolu oturumu kapatır. Görüntüler ve ölçülü JSON
raporu `test-results/` altına yazılır. Senaryo kaydı ve sözdizimi kontrolü canlı
tarayıcı geçişi değildir; kullanılan gerçek koşucu ve ortam ayrıca raporlanır.

`08-microphone-capture.mjs`, [Accepted 007 PRD](../../specs/speaker-identity/PRDs/007-microphone-meeting-capture/PRD.md)
için mevcut sıradan toplantı yazarı/okuyucusu hesaplarını kullanır. Varsayılan
koşum iki dilde mikrofon/dosya kaynak seçimini, ortak toplantı seçeneklerinin
korunmasını, erişilebilir kayıt göstergelerini ve salt okunur kullanıcıya kayıt
kontrolü sunulmamasını doğrular; ses kaydetmez veya toplantı/profil yaratmaz.

- `APP_E2E_MICROPHONE_LIVE=1`: gerçek fiziksel mikrofonla kayıt dalını açıkça etkinleştirir. Sağlıklı bir mikrofon, güvenli köken, OPFS/AudioWorklet desteği ve hazır gerçek model gerekir.
- `APP_E2E_MICROPHONE_SECONDS`: her dilde gerçek kaydın gözlenen süresi; varsayılan 35 saniye, izin verilen aralık 25–300 saniyedir.
- `APP_E2E_MICROPHONE_LANGUAGE`: kaydedilen konuşmanın dili `tr`, `en` veya `auto`; arayüz diliyle aynı olmak zorunda değildir, varsayılan `tr`.

Gerçek kayıt dalı boş ve yalnız test için ayrılmış profil tenant'ı gerektirir.
Koşucu yazdığı başlangıç iletisi boyunca mikrofona temiz konuşma sağlanmalıdır;
ses dosyası, sahte mikrofon, simüle edilmiş model veya enjekte edilmiş oturum
kullanılmaz. Headless tarayıcının fiziksel giriş cihazına erişimi ayrıca
doğrulanmalıdır. Koşucu mikrofon iznini tarayıcı bağlamına verir; tarayıcının
insana gösterdiği izin penceresini tıklama kanıtı değildir. Bir saniyelik iptal
denemesinin ardından kayıt gözlenen hedef süreye gelince "Durdur ve analiz et"
tıklanır. Son WAV için gerçek kaynak hash/boyut/süre eşitliği, başarılı analiz,
boş olmayan metin ve görünür konuşmacı/hafıza kararı aranır. Sessizlik veya boş
metin bu deneyi geçirmez; kalite nedeniyle `profile_pending`/`ambiguous` sonucu
zorla başarılı kişi kaydına dönüştürülmez.

Senaryo kendi başlık önekiyle oluşturduğu toplantıları ve yalnız bunların
`enrolled` sonucundan doğan profilleri `finally` yolunda public API ile temizler.
Önceki kullanıcı verisiyle çalıştırılmamalıdır. `test-results/microphone-capture.json`
yalnız durum/sayım kanıtını yazar; ses, cihaz etiketi, ad, transkript veya token
raporlanmaz. Bayrak kapalıysa fiziksel kayıt açıkça çalıştırılmamış sayılır.
Gerçek cihaz kesilmesi, reddedilen izin penceresi, zorla kapanma sonrası disk
temizliği ve L3 kullanıcı kabulü bu senaryonun geçtiği varsayılarak kapatılmaz.

`09-meeting-audio-review.mjs`, [Accepted 011 PRD](../../specs/speaker-identity/PRDs/011-meeting-audio-review/PRD.md)
için `APP_E2E_AUDIO_REVIEW_USER` / `APP_E2E_AUDIO_REVIEW_PASS` ile sıradan
okuyucu hesabından gerçek parola girişi yapar. `APP_E2E_AUDIO_REVIEW_MEETING_ID`
aynı tenant'taki mevcut, tamamlanmış, kaynağı tutulmuş ve en az iki metin
satırlı toplantıyı belirtir. Senaryo hesap, toplantı veya profil oluşturmaz;
başlangıç ve bitiş public verisini karşılaştırır, sonunda oturumu kapatır.

TR/EN ve 1440/390 pikselde klavyeyle satır seçimi, en çok 30 saniyelik
yetkili WAV, cache engeli, oynatıcı decode/süre/denetimleri, kapatma ve odağın
geri gelmesi doğrulanır. `test-results/meeting-audio-review.json` yalnız toplu
gözlemleri içerir. Tarayıcı oynatmayı engellerse decode başarısıyla karıştırılmaz;
`playback_started` ayrıca kaydedilir. Fiziksel hoparlör, uzun satırın tüm
bölümleri, kaynak süresinin dolması ve model doğruluğu bu dar senaryodan
çıkarılmaz. Başarısızlık ekranları metin içerebilir ve özel `test-results/`
alanında kalmalıdır. Senaryo kaydı veya sözdizimi kontrolü gerçek koşum değildir.

`10-contextual-transcript-review.mjs`, [Accepted 013 PRD](../../specs/speaker-identity/PRDs/013-model-selection-saved-corrections/PRD.md)
için `APP_E2E_TEXT_REVIEW_USER` / `APP_E2E_TEXT_REVIEW_PASS` ile sıradan okuma ve
çalıştırma yetkili hesaptan gerçek giriş yapar. `APP_E2E_TEXT_REVIEW_MEETING_ID`
aynı tenant'taki tamamlanmış bir toplantıyı seçer; ilk metin sayfasında en az
bir boş olmayan, en çok 1.024 Unicode kod noktalı satır gerekir. Gerçek yerel
model ve uygulamadaki metin inceleme ayarı hazır olmalıdır. Kaynak sesin
tutulması gerekmez. İsteğe bağlı `APP_E2E_TEXT_REVIEW_MODEL` listelenen gerçek
kullanılabilir modelin tam adını seçer; verilmezse kullanılabilir kayıtlı
varsayılan gerekir. Başka modele sessiz geçiş yapılmaz.

Senaryo kurulu seçenekleri gerçek API ile karşılaştırır; panel açma ve seçim
tek başına hesaplama başlatmaz. Her dilde açık kontrol eylemi bir gerçek model
çağrısı yapar; 100 saniyelik model sınırına uygun bekler ve gerçek 200 yanıtı
gerektirir. TR/EN ve 1440/390 pikselde yeşil ve altı çizili kelimeler, tüm
anlamsal inceleme/eşlenememe önerileri, düz metin model cevabı ve modelin o
koşumda döndürdüğü durum denetlenir. Kaynak ID/metin/SHA256, model adı/digest
ve mevcut sürüm eşitliği, yalnız model seçimi içeren istek, kapatma/odak ve
ham toplantı/kişi/metin verisinin değişmediği kontrol edilir. Kaydetmez veya
fixture oluşturmaz; `finally` oturumu kapatır. `test-results/contextual-transcript-review.json`
yalnız toplu kanıttır; metin, model cevabı veya kaydetme kanıtı raporlanmaz.

`11-saved-transcript-corrections.mjs` aynı sıradan hesapla ayrı, silinebilir
test toplantısında gerçek öneriyi kaydeder. Çalıştırmadan önce yalnız bu test
için oluşturulmuş toplantı aşağıdaki açık sözleşmeyle sağlanmalıdır:

- `APP_E2E_CORRECTION_SAVE_MEETING_ID`: aynı tenant'ta tamamlanmış test toplantısı; başlığı `e2e-text-correction-` ile başlamalıdır.
- `APP_E2E_CORRECTION_SAVE_CONFIRM=disposable-test-meeting`: bu test toplantısına sürüm kaydedilmesini ve `finally` içinde public API ile toplantının silinmesini açıkça etkinleştirir.
- `APP_E2E_CORRECTION_SAVE_TRANSCRIPT_ID`: isteğe bağlı ilk sayfadaki hedef satır; verilmezse ilk uygun satır seçilir.
- `APP_E2E_TEXT_REVIEW_MODEL`: isteğe bağlı gerçek model seçimi, senaryo 10 ile aynı kurala tabidir.

Fixture gerçek kullanıcı verisi içermemeli, başka senaryonun kalıcı okuma
fixture'ı olmamalıdır. Koşucu hesap veya ses profili oluşturmaz; yalnız
kimliği ve başlık öneki doğrulanmış bu toplantıyı sonunda temizler.
Gerçek modelin en az bir tam eşlenmiş, kaydedilebilir değişiklik üretmesi
gerekir; boş veya bozuk sonuç yerine sahte başarı konmaz. Kaydetme isteğinin
yalnız gösterilen önerinin kanıtını gönderdiği, tek sürüm oluşturduğu,
özgün kaynak/zaman/konuşmacıyı koruduğu, yenilemeden sonra yeşil görünüm ve
TR/EN Orijinal/Düzeltilmiş geçişi doğrulanır.
`test-results/saved-transcript-corrections.json` toplu sayımları ve temizlik
sonucunu içerir; kaynak metin veya token içermez.

İki senaryo da kelime doğruluğu, insan kabulü veya gözlenmeyen hata dalları
için kanıt değildir. Paylaşılan `text-review-support.mjs` gerçek giriş,
yerel public API okuma ve seçilen modelin görünür öneri sözleşmesini kullanır.
Senaryoları kaydetmek ve sözdizimini kontrol etmek canlı koşum sayılmaz.
Başarısızlık ekranları metin içerebilir ve özel `test-results/` alanında kalır.
