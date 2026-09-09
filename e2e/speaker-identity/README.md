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

`02-read-only.mjs` gerçek girişle iki dilde salt okunur sayfaları, gizli yazma alanlarını,
yenilemeyi ve çıkışı doğrular. `01-local-pilot.mjs` gerçek yükleme, bozuk/sessiz ses,
kalıcı iş, profil oluşturma, ad değiştirme, tanıma ve silme akışını doğrular; oluşturduğu
profilleri ve kullanılmayan kayıtları `finally` yolunda public API üzerinden temizler.
Doğru ek örnek kabulünü, yanlış kişiden örnek eklemenin reddini, örnek sayısının korunmasını
ve kayıtlı olmayan konuşmacının kimliğe bağlanmamasını da denetler.

Ses dosyasının kendisini yeniden tanımak bağlantı kontrolüdür; ayrı oturum doğruluk deneyi
değildir. Tekrarlanmış resmi test klibi kullanılabilir, ancak bunun oluşturulmuş fixture
olduğu koşum raporunda belirtilmelidir. Gerçek kullanıcı veri seti olmadan beş kişilik
tanıma hedefi tamamlanmış sayılmaz.
