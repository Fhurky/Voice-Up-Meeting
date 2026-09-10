# PRD — Yerel yönetici için tek tıkla giriş

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [006 — local-admin-login](../../roadmap.md)
Kabul kaydı (10 Eylül 2026): Kullanıcı giriş ekranında hazır bir admin düğmesiyle
otomatik giriş istedi; tamamlanan özelliğin commit ve push işlemlerini de yetkilendirdi.

## Amaç ve aktörler

Yerel pilot kullanıcısı NVIDIA/Spark veya Mac CPU kurulumunda kullanıcı adı ve
parola yazmadan mevcut yerel yönetici hesabıyla giriş yapar. Normal parola ile
giriş, çıkış, tenant ve uygulama yetkileri korunur.

## Kararlar ve değişmezler

Decision 1: `kt-vibecoding-python-web-v2`, mevcut FastAPI kimlik doğrulaması ve
React/Vite oturum yapısı korunur. Backend normal süreli ve imzalı JWT üretir;
arayüz bir parola, gömülü token veya sahte yetki kullanmaz.

Decision 2: Özellik typed settings içinde varsayılan kapalıdır, yalnız açıkça
etkinleştirilmiş `development` ortamında çalışır. Yerel Compose açık varsayılanı
taşır; staging/production/test ortamında etkinleştirme başlangıçta reddedilir.
İstek Host'u loopback olmalıdır; yabancı Origin ve browser cross-site istekleri
reddedilir. Mevcut web portu yalnız loopback üzerinde yayınlanır.
Yerel API proxy'si Host portunu korur; Origin varsa scheme/hostname/port eşleşir.
`Sec-Fetch-Site` varsa yalnız `same-origin` kabul edilir; `null` Origin reddedilir.

Decision 3: Sunucuda yapılandırılmış isteğe bağlı kullanıcı adı varsa yalnız o
aktif yönetici kullanılır; yoksa aktif home tenant'ında aktif `super_admin` rolü
olan tam bir hesap bulunmalıdır. Eksik veya birden çok adayda seçim yapılmaz.
Yapılandırılmış kullanıcı adı çözülemezse başka hesaba geri dönüş yapılmaz.
Parolalar, kullanıcı/tenant/rol kayıtları ve ses profilleri bu girişle değişmez.
İlk hesabın hazırlanması mevcut açık `create-super-admin.sh` kurulum adımıdır;
giriş çağrısı hesap oluşturmaz, silinmiş kaydı canlandırmaz veya yetki yükseltmez.

## Gereksinimler

Requirement 1: `GET /auth/options` yalnız `local_admin_login_enabled` boolean'ını
döndürür; hesap listesi veya kimlik bilgisi yayımlamaz. `POST /auth/local-admin`
istemciden hedef kullanıcı/parola almaz ve mevcut `LoginResponse` döndürür.
Kapalı/uygunsuz yerel erişim reddedilir; kullanılamayan yönetici için kararlı hata
kodu döner. Yanıtlar cache edilmez. Her POST güncel kullanıcı/tenant/rolü denetler.

Requirement 2: Giriş ekranı özellik açıkken “Admin olarak giriş yap” düğmesini
gösterir. Tıklama boyunca iki giriş eylemi de devre dışıdır; başarı ana sayfaya
götürür. Hatalar TR/EN çevrilir; options çağrısı başarısızsa normal giriş kullanılabilir.
Sayfa açılınca veya çıkıştan sonra kendiliğinden yeniden giriş yapılmaz.

Requirement 3: Oturum mevcut saklama, `/me`, yenilemede doğrulama, tenant başlığı,
RBAC ve çıkış davranışını kullanır. Genel API sözleşmesi ve üretilmiş frontend
tipleri aynı değişiklikte güncellenir.

Requirement 4: Backend `.env.example`, yerel Compose ve kurulum rehberleri yeni
ayarları taşır; chart mevcut tek Secret sınırını korur ve dağıtımda özellik kapalıdır.
Mevcut yerel uygulama yeniden yüklenip gerçek tarayıcıda doğrulanır. NVIDIA/Spark
model servisine veya kullanıcı şifrelerine müdahale edilmez.

## Veri, güvenlik ve eşzamanlılık

Yeni şema/migration/kalıcı veri: N/A — yalnız mevcut hesaplar okunur ve kısa ömürlü
JWT üretilir. Tekrar çağrı yeni geçerli oturum üretebilir; hesap veya profil yazmaz.
Kimlik bilgisi/JWT loglanmaz; HTTP durum ve mevcut istek korelasyonu korunur.
Yeni worker/cache/model bağımlılığı: N/A — kimlik doğrulama akışıdır.
Saklama politikası: N/A — yeni saklanan veri yoktur.

## Test ve kabul ölçütleri

- [x] Red/green backend testleri kapalı/yanlış ortamı, yabancı Origin/Host'u,
  geçersiz ve belirsiz yöneticiyi, pasif/silinmiş kayıtları ve normal giriş regresyonunu kapsar.
- [x] Gerçek PostgreSQL/HTTP testinde geçerli JWT ve `/me` doğrulanır; parola,
  tenant ve rol kayıtları değişmez; yönetici rolü kaldırılınca yeni giriş reddedilir.
- [x] TR/EN frontend testleri görünürlük, tek tık, bekleme, hata ve normal giriş akışını kapsar.
- [x] Kalıcı tarayıcı senaryosunda tek tık, korunan sayfa, yenileme, çıkış ve iki dil gözlenir.
- [x] OpenAPI/tipler, config ve tam kalite kapısı günceldir; güvenlik kapısı sonucu açık raporlanır.
- [x] Kod ve kanıtlar commit edilip istenen GitHub deposuna gönderilir; sırlar Git dışında kalır.

10 Eylül kanıtı: [Koşum raporu](../../../../docs/evidence/2026-09-10-local-admin-login/README.md).
153 backend/59 frontend testi, 12 gerçek HTTP kontrolü ve CUA ile iki dilde iki
tarayıcı akışı geçti. Kalıcı Playwright dosyasının bağımsız çalıştırıcısı kullanılmadı;
senaryo kabul adımları gerçek tarayıcıda elle otomasyonla uygulandı. Gitleaks
olmadığından güvenlik kapısı tamamlanamadı; fiziksel Mac testi bu koşumda yapılmadı.

Özellik yayını: `aa11e17f461d135b6e368e54a54111c74bdde9ae`; uzak `main` eşitliği
doğrulandı. [Yayın kaydı](../../../../docs/evidence/2026-09-10-local-admin-login/publication.json).
