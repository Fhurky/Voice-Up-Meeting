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
- Karar: mevcut referansın 0.75 kabul, 0.45 bilinmeyen ve 0.10 aday farkı geliştirme
  ayarları. Bunlar gerçek doğruluk garantisi veya kalibre olasılık değildir.
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
ve kalıcı Playwright paketi sağlanmadı. Gerçek kişi veri deneyi hâlâ eksiktir.

## Teslim akışı

Spec → açık kullanıcı kabulü → Accepted PRD → Plan → Tasks → Implement → kanıt.
Kapsam kabul edildi. Uygulama, bağlı plan ve görevlerden yürütülür; başarısız veya eksik kanıt açıkça raporlanır.
