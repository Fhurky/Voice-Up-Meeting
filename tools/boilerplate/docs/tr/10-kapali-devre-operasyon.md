# Kapalı devre operasyon

## Çalışma modeli

Üretilen uygulamanın runtime'ı internete çıkmaz. Gerekli wheel, npm cache, Playwright Chromium ağacı,
OCI image ve scanner materyali kontrollü yazılım tedarik zincirinden içeri alınır, digest ile kabul
edilir ve kapalı ortama taşınır.

Kapalı devre iddiası yalnız model endpoint'inin yerel olması değildir. Şunların tamamı kapsamdadır:

- kodlama istemcisinin auth, telemetry, update ve extension davranışı;
- model sağlayıcısı/gateway ve log retention politikası;
- paket yöneticilerinin index/mirror yapılandırması;
- container image ve workflow action kaynağı;
- browser binary ve scanner veritabanı;
- DNS, proxy ve egress-denied runner/network policy kanıtı.

## Offline bundle

`packaging/offline-bundle.sh`, kabul sürecine girecek taşınabilir envanteri hazırlar. Üretilen proje
`scripts/verify-offline-bundle.sh` ile:

- dışarıdan sağlanan `SHA256SUMS` admission digest'ini;
- iç envanterdeki her artifact hash'ini;
- host platform/mimari eşleşmesini;
- gerekli Python, npm, browser ve image öğelerinin tamlığını

doğrular. Trust anchor ile bundle'ı aynı kontrolsüz kanaldan almak bütünlük iddiasını zayıflatır.

## Bağımlılık kabulü

`dependency-admission.json`, doğrudan package authority, OCI digest ve workflow action envanterini
tek gözden geçirilmiş digest'e bağlar. Lock değişikliği otomatik olarak kabul edilmiş sayılmaz;
maturity/security/lisans kanıtı güncellenip kalite ve security gate yeniden çalıştırılır.

Paket yöneticileri no-index/offline moda zorlanır. “Cache'te yoksa internetten indir” fallback'i
kapalı profilin parçası değildir.

## MCP dağıtımı

Streamable HTTP prosesi `127.0.0.1` üzerinde gateway sidecar yanında çalışır. Gateway:

- OAuth 2.1 kimlik ve scope kontrolü;
- TLS veya kurum politikasına göre mTLS;
- request/body limit, rate limit ve audit identity;
- iç DNS/service discovery

sağlar. Token ve sertifikalar proje dosyasına değil, banka tarafından yönetilen runtime secret
yüzeyine konur.

## Yerel model ve istemci kabulü

VS Code Local Agent + banka içi Ollama/Qwen kombinasyonu tam kapalı profilin varsayılanıdır; fakat her
istemci, model, quantization, context boyutu ve donanım kombinasyonu için kontrollü kabul testi
tekrarlanır. En azından instruction discovery, tool use, çok dosyalı edit, unit test, uzun görevde
repo hafızasından devam ve doğru kanıt raporlama ölçülür.

Modelin büyük context ilanı, istemcinin aynı miktarı etkin kullandığını veya session history'nin
kalıcı olduğunu kanıtlamaz. Uzun görev durumu PRD/plan/tasks ve repo manifestlerinde tutulur.

## Operasyon kayıtları

Kabul kaydı en az sürüm, platform, model kimliği, model digest/quantization, istemci ayarı, test
senaryosu, tarih, sonuç ve bilinen kısıtları içerir. UI sürümü veya model değişince önceki PoC
kanıtının hangi kısmının yeniden çalıştırıldığı açıkça yazılır.
