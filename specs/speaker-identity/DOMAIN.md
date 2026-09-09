# speaker-identity domain

Status: Active; first capability Accepted

## Amaç

Konuşmacıya ait sayısal ses özelliklerini kullanarak kayıtlar arasında kalıcı kimlik
kurmak, yeni ve belirsiz sesleri ayırt etmek, kararın dayandığı model/örnek bilgisini izlemek.

## Aktörler ve terimler

Pilot kullanıcısı, tenant yöneticisi ve yerel analiz yürütücüsü aktörlerdir.
Profil kalıcı kişi kimliğini; örnek doğrulanmış tek konuşmacılı kaydı; embedding model
sürümüne bağlı ses vektörünü; analiz işi durum ve terminal sonucu temsil eder.
`recognized`, `unknown`, `ambiguous` kararları birbirinden ayrıdır; benzerlik yüzde güven değildir.

## Değişmezler

- Tenant ve model sürümleri arasında karışık arama yapılmaz.
- Kimlik kararı yeterli kanıt olmadan profil güncellemez.
- Kullanıcıya public kimlik verilir; model gerçek adı kendi başına öğrenmez.
- Ürün PostgreSQL/SQLAlchemy/Alembic ve tipli model adaptörü sınırında geliştirilir.
- Ses/model dosyası çalışma anında internetten alınmaz; kişisel içerik loglanmaz.

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
