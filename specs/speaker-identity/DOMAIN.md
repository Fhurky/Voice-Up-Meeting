# speaker-identity domain

Status: Active; first capability Accepted

## Amaç

Konuşmacıya ait sayısal ses özelliklerini kullanarak kayıtlar arasında kalıcı kimlik
kurmak, yeni ve belirsiz sesleri ayırt etmek, kararın dayandığı model/örnek bilgisini izlemek.

Öncelikli doğruluk hedefi yaklaşık 50 katılımcılı kullanımdır; 50 kayıt kotası
değildir. Toplantıdaki katılımcı sayısı ile sistemde kayıtlı bütün kişilerin sayısı
ayrı ölçülür; 100–200 kayıtlı kişi varken de kullanım sayıya göre engellenmez.

## Aktörler ve terimler

Pilot kullanıcısı, tenant yöneticisi ve yerel analiz yürütücüsü aktörlerdir.
Profil kalıcı kişi kimliğini; örnek doğrulanmış tek konuşmacılı kaydı; embedding model
sürümüne bağlı ses vektörünü; analiz işi durum ve terminal sonucu temsil eder.
`recognized`, `unknown`, `ambiguous` kararları birbirinden ayrıdır; benzerlik yüzde güven değildir.
Kaynak platform katılımcısı, toplantı içindeki akustik konuşmacı kümesi ve kalıcı
ses profili ayrı kimliklerdir. `profile_pending`, toplantıda sözü görünen fakat
kalıcı ses profili için yeterli temiz kanıtı bulunmayan kişiyi belirtir.

## Değişmezler

- Tenant ve model sürümleri arasında karışık arama yapılmaz.
- Kimlik kararı yeterli kanıt olmadan profil güncellemez.
- Kullanıcıya public kimlik verilir; model gerçek adı kendi başına öğrenmez.
- Ürün PostgreSQL/SQLAlchemy/Alembic ve tipli model adaptörü sınırında geliştirilir.
- Ses/model dosyası çalışma anında internetten alınmaz; kişisel içerik loglanmaz.
- Kısa konuşmanın transkripti kalıcı biyometrik profil eksikliği nedeniyle engellenmez.
- Platformdaki görünen ad veya ses kaynağı kimliği kalıcı biyometrik kimlik yerine geçmez.
- Toplantı otomatik kaydı, aynı akustik kümeye güvenle atanmış tekil temiz konuşmaların toplamı 20 saniyeyi aşınca süre açısından yeterlidir; kalite, tutarlılık ve bilinmeyen kişi kararı ayrıca gerekir. 001 eşiği değişmez.
- Katılımcı üst sınırı ile gerçekten konuşan kişi sayısı ayrı bilgidir; global sayı her parçaya zorlanmaz ve en yakın iki sesi körce birleştirme gerekçesi olmaz.
- Elle değiştirilen gösterim adı kalıcı kimliği veya ses vektörünü değiştirmez; aynı adlı kişiler ayrı profiller olabilir.

## Sahip olunan veri ve sınırlar

Ses kaydı metadata'sı, profil, örnek/model sürümü ve analiz işi bu domain'e aittir.
Auth/tenant platform temeli kullanılır. Model çıkarımı yerel altyapı adaptörüyle çağrılır.
ASR, toplantı platformu bağlantısı ve canlı ses aktarımı bu domain'in ilk pilotuna dahil değildir.

## Mevcut durum

`app/backend/`, `app/frontend/` ve `app/inference/` içinde PostgreSQL/pgvector tabanlı
tek konuşmacı pilotu uygulanmıştır. `src/voiceup/` ayrı CPU/SQLite araştırma çekirdeğidir.
İlk [yerel pilot PRD'si](PRDs/001-local-speaker-pilot/PRD.md) Accepted durumundadır;
[görev listesi](PRDs/001-local-speaker-pilot/tasks.md) cihaz ve doğruluk kanıtını ayrı izler.
[Yol haritası](roadmap.md) sonraki yetenekleri tanımlar.

Uzun kayıt ve canlı işleme sırası 9 Eylül 2026 kararında kaydedildi: önce 001'in gerçek
kişi ölçümü, ardından 002 uzun kayıt ve 003 canlı analiz. Parça etiketi, toplantı kişi
kümesi ve kalıcı kimlik birbirinden ayrıdır; kapsamlar yol haritasında izlenir.

004, çıkarım sağlayıcısını Ethernet üzerinden yetkili Spark cihazına taşır.
Model servisi veritabanına erişmez; kalıcı kimlik ve iş kayıtlarının otoritesi aynı kalır.

10 Eylül ek isteğiyle 002, dosya veya durdurulmuş mikrofon kaydından konuşmacılı
transkript ve kaliteli yeni kişinin otomatik kalıcı kaydını kapsar. Bu ayrı toplantı
işlemi 001 `identify` çağrısını profil yazan bir işleme dönüştürmez. 002 kabul
edildiğinde model erişimi ve yeni Spark çalışma ortamı hazırlığı bekliyordu; uygulanmış
toplantı özelliği olduğu iddia edilmez. [Kullanıcı akışı](../../docs/MEETING_WORKFLOW.md).

10 Eylül sonraki Teams/parçalı konuşma kararıyla 002, aynı kişiye ait ayrı kısa
konuşmaları biriktirir; tam 20 saniye ve altındaki yeni kişi `profile_pending`
olarak kalır. Bağlam, tekrar ve kayıt boşlukları temiz süreyi artırmaz. Yetkili
Community-1 erişimi sabit revision yapılandırmasının HTTP 200 yanıtıyla
doğrulandı; sekiz dosyalı model paketi tamamlandı. Yerel RTX 4060/Python 3.13
üzerinde ayrı, çevrimdışı bir araştırma konteynerinde 12 örnek işlendi; uygulama
sağlayıcısı/decoder entegrasyonu, üretim bağımlılık kabulü ve Spark ARM64 hazırlığı açık.
Yerel geliştirme sağlayıcısı açık cihaz seçimiyle sınanır;
başka runtime araştırması veya yerel cihaz sonucu Spark kanıtı yerine geçmez.
Teams bağlantısı henüz uygulanmaz, 003 Draft kalır ve sabit FastAPI sınırı korunur.

Son kaynak yanıtı yüklenen kaydın yeterli olduğunu belirledi. 002'nin güncel
kabul akışı dosya → konuşmacı/metin → elle ad → kalıcı hafıza → farklı kayıtta
aynı beş profil → altıncı yeni kişidir. Önceki mikrofon isteği ayrı
[007 yeteneğinde](PRDs/007-microphone-meeting-capture/PRD.md) Accepted ve eksik
olarak korunur; dosya teslimi otomatik Teams bağlantısına veya mikrofon UI'sine
bağlanmaz. Model ön hazırlık kanıtı bu uçtan uca akışın tamamlandığı anlamına gelmez.
