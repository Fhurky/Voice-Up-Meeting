# PRD — Genişletilmiş Türkçe test kapsamı

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [010](../../roadmap.md)
Sabit profil: `kt-vibecoding-python-web-v2`.
Kabul kaydı: 13 Eylül 2026 tarihli kullanıcı talimatı, başka verilerle ve çok
daha fazla test kaydıyla uygulamanın doğruluğunu sınamayı yetkilendirir.

## Amaç ve aktörler

Değerlendirme sorumlusu, 009'un sınırlı örneklerini yeni Türkçe kaynaklar ve
daha önce işlenmemiş kayıtlarla genişletir. Geliştirici hangi koşullarda
metin ve kalıcı kişi hafızası hatası oluştuğunu toplu kanıtlardan görür.
Kaynak sayısı, farklı klip sayısı, ses süresi, gerçek kişi sayısı ve yeniden
işlenen ses ayrı tutulur. Daha fazla klip 50 kişi başarısı yerine geçmez.

## Kararlar

Decision 1: 009 ölçümleri, kaynakları ve günlük sürümleri korunur. Yeni deney
kimlikleri ve ayrı özel manifestler kullanılır. Model, üretim ayarı ve kimlik
eşikleri bu test kapsamı için değiştirilmez; sonuçlar ayar seçmeden ölçülür.

Decision 2: Resmî MediaSpeech Türkçe arşivinden önceki 80 dosya kimliği ve ses
hash'i hariç kalan 2.433 farklı klibin tamamı sabit seçimle yeni test olur. Arşiv aynı
kaynaktır; yeni veri seti diye sayılmaz. Önceki 40/40 ayrımı değişmez. Seçim
model sonuçlarına bağlı olmaz, reddedilen dosyalar ve nedenleri kaydedilir.

Decision 3: FLEURS Türkçe resmî test bölümü ikinci ASR kaynağıdır. Yayımlanan
revision, arşiv/etiket hashleri, lisans ve bölüm kapsamı hazırlamadan önce
kaydedilir. Hedef bölümün tamamıdır; erişim veya kaynak uyumsuzluğu varsa
gerçek sayı ve engel açıklanır. Kişi kimliği olmayan veri hafıza ölçmez.

Decision 4: Real-TurnTurk altı görüşmesinden ilk 180 saniyeyle örtüşmeyen
`[300,600)` ve `[600,900)` aralıkları, mevcut kişi sayısı girdisiyle iki yeni
boş deney tenantında aynı doğal görüşme sırası üzerinden sınanır. On iki
kesit toplam 60 dakika yeni içerik sağlar. En kısa kaynak kanalı 959,720
saniye olduğundan bütün kaynaklar iki pencereyi de kapsar. Seçim model
sonuçları görülmeden dondurulur. Aynı altı kişi ve aynı kaynak oturumları korunur; temporal ayrım
yeni kişiler veya bağımsız oturumlar diye sunulmaz. 009'un zayıf referans ve
örnek saati uyarıları sürer; etiketler modele gönderilmez.

Decision 5: ASR kelime hataları klip başına hesaplanıp toplam referans kelime
sayısına bölünür. Türkçe normalizasyon sürümü değişmez. Kaynak başına ayrı
sonuçlar, süre, tam eşleşen klip ve hata dağılımı raporlanır; güven aralığı
verilirse klip düzeyinde tekrar örnekleme olduğu, kişi/oturum bağımsızlığı
kanıtlamadığı ve kaynak bütününe genellenemediği açık belirtilir.

Decision 6: Uzun değerlendirme kesintiye dayanıklı ve kaynak/ayar bağlıdır.
Mevcut tamamlanmış deney üzerine yazılmaz. Açık devamda tamamlanan klipler
tekrar modelden geçirilmez; yanlış manifest, model, ayar veya kaynakla devam
reddedilir. Eksik koşum ve planlı kapsam görünürdür. Başarısız klip sessizce
paydadan çıkarılmaz. GPU koşumları sırayla yürütülür.

Decision 7: Hazırlama açık ağ işlemi; çıkarım mevcut sabit yerel model ve
imajla çevrimdışıdır. Yeni paket, model ağırlığı veya çalışma anında indirme
gerekmez. Ham ses/metin, kimlik eşlemeleri ve hesap bilgileri `data/` ve
`outputs/` içinde Git dışında kalır. Günlük yalnız 009 izinli toplu alanları
içerir; ek toplu tanılar ayrı kaynak bağlı kanıtlara yazılır.

Decision 8: FLEURS revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`
Türkçe test arşivi 464.259.241 bayt ve SHA-256
`a7db7a681e4460d2922626bf2037ddc1a9146efba27d78bfc9543250eabc3a09`;
`test.tsv` 447.909 bayt ve SHA-256
`52adb452a258976a2428da88fe7ac4d9bce27d4c10f9358ba3acf48a9b59577a`
olarak sabitlenir. 743 dosya, 329 cümle kimliği ve 9.380,22 saniye vardır.
Metadata bu testin tamamını MALE olarak işaretler; geniş Türkçe nüfusu veya
kadın sesleri kapsadığı iddia edilmez. Cümle kimliği kişi kimliği değildir.
Özgün mono 16 kHz float WAV sesleri dönüştürülmeden okunur.

Decision 9: İlk büyük kaynak başlangıcında Windows–Docker dosya bağında
aynı hedef/kaynak yollarının yinelenen çözülmesi model öncesi dakikalar
sürdü. Henüz kontrol noktası veya model hesaplaması oluşmadan iki girişim
durduruldu; 0/2.433 kapsam ve skor yok olarak günlüğe kaydedilir. İlk komutta
yanlış yazılmış model dizini ayrıca vardı. Yol/bağ denetimleri her kilitli
geçişte tek sefer hesaplanan yol ve dosya kimliği kümeleriyle korunur;
model dizini ön koşulu erken doğrulanır. Tüm dosya içerik hashleri ve ses
örnek kontrolleri sürer. Kaynak doğrulama ilerlemesi model ilerlemesinden
ayrı yazılır. Bu yürütücü düzeltmesi yeni kaynak hash'i ve yeni deney
kimlikleriyle çalışır; model ayarı veya ölçüm protokolü değiştirilmez.

## Gereksinimler

Requirement 1: İki ASR kaynağının hazırlaması hashli, yol güvenli, boyut
sınırlı ve tekrar üretilebilir olmalı; eski manifest ve sesler korunmalıdır.
En az 1.000 yeni MediaSpeech klibi ve erişilebilir FLEURS test bölümünün
tamamı gerçek yerel modelle değerlendirilmelidir.

Requirement 2: On iki kullanılmamış görüşme penceresi gerçek yükleme/analiz/
hafıza HTTP akışından geçirilmelidir. İlk kayıt ve geri dönüş paydaları,
eksik ilk kayıt, belirsizlik ve varsa yeniden kayıt ayrı görünmelidir.

Requirement 3: Her yeni koşum `results.md` içinde uygun referansın izin
verdiği skorlarla, kaynak/ayar/protokol hashleri ve kapsamıyla yer almalıdır.
Kaynaklar arası tek bir yanıltıcı başarı oranı oluşturulmamalıdır.

Requirement 4: Hazırlama, kesinti/devam ve skor toplama sınırları gerçek
dosyalar ve kısıtlı model taklidiyle test edilmeli; tam profil kapısı ve
güvenlik kapısı denenip gerçek sonuçları sabit koşum raporuna yazılmalıdır.

## Etkilenen katmanlar ve sınırlar

API/OpenAPI/UI N/A — mevcut toplantı HTTP sözleşmesi kullanılır, yeni ürün
ekranı veya uç eklenmez. Şema/migrasyon N/A — geliştirme kanıtları dosyadır,
mevcut domain/persistence otoritesi değişmez. Yetki/tenant mevcut sıradan
hesap üzerinden sınanır; eski kullanıcı galerisi temizlenmez. Gözlem toplu
ilerleme, süre, durum ve içerik hashleridir; ham içerik loglanmaz.
Dağıtım/işçi/önbellek N/A — yeni servis, sürekli işçi veya runtime ayarı yok.
Bağımlılık N/A — kabul edilmiş yerel Python/ses/model araçları kullanılır.
Veri saklama özel yerel artefaktlarla sınırlıdır; silme bu kapsamda yoktur.

## Test ve kabul

- [x] İki ASR kaynağı eski 80 klibi koruyarak hazır; 3.176 yeni klip, 44.232,32 saniye ve tam kopya bulunmadığına dair kaynak/rol/hash kanıtı var.
- [x] MediaSpeech 2.433/2.433 ve resmî FLEURS test bölümünün 743/743 kaydı gerçek RTX 4060 modeliyle tamamlandı; WER %14,1249 ve %6,5046. [Nihai rapor](../../../../docs/evidence/2026-09-13-expanded-turkish/README.md).
- [x] On iki yeni görüşme penceresinin gerçek HTTP hafıza sonuçları günlüğe yazıldı; bağımsız 274/274 canlı denetim başarılı. Her zincirde 6 yeni kişi görünümü ve 6 bilinen geri dönüş doğru; altı kişi/aynı oturum/zayıf referans sınırları [canlı raporda](../../../../docs/evidence/2026-09-13-expanded-turkish/meeting-live-report.md) görünür.
- [x] Kesinti/devam, kaynak koruması ve toplama regresyonları geçti; son Windows kök koşumu 493 başarılı / 2 atlanan, tam profil kapısı 738 başarılı. İki sembolik bağ sınırının ayrı Linux başarısı [son doğrulamada](../../../../docs/evidence/2026-09-13-expanded-turkish/post-performance-verification-report.md), güvenlik kapısının `gitleaks` eksikliği nedeniyle çıkış 2 sonucu [kapı raporunda](../../../../docs/evidence/2026-09-13-expanded-turkish/quality-report.md) açık kayıtlıdır; güvenlik taraması başarılı sayılmaz.
- [x] Kullanım belgeleri ve `results.md` güncel; 24 günlük kaydı ve önceki 18 kaydın korunması doğrulandı. Türkçe yazım/sınır tanıları, eksik güvenlik aracı ve ölçülmeyen 50 kişi/cihaz/insan referansı koşulları [nihai raporda](../../../../docs/evidence/2026-09-13-expanded-turkish/README.md) açık.
