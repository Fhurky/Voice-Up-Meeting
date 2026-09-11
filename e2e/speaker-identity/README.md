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
