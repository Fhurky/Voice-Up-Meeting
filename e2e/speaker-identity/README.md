# Yerel konuşmacı pilotu tarayıcı senaryoları

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
