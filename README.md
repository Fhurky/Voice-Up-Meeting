# VoiceUp

Toplantılar arasında aynı konuşmacıyı yeniden tanımak için kalıcı ses profilleri.
İlk ürün pilotu **RTX 4060 üzerinde tek konuşmacılı WAV/FLAC** akışını hazırlar.
Çok kişili toplantı bölümleme, metne çevirme ve toplantı entegrasyonu sonraki aşamadır.

## Yerel uygulama

MacBook üzerinde bütün servisleri ve modeli yerel CPU ile çalıştırmak için
[Mac kurulum rehberini](docs/MACOS_SETUP.md) kullanın. Apple Silicon/Intel paketleri
ayrıdır; gerçek Mac cihazındaki doğrulama durumu rehberde belirtilir.

Hazırlanmış ortamda Docker Desktop açıkken:

```powershell
./scripts/start-local.ps1
```

Uygulama: **http://127.0.0.1:8081**. Yerel giriş bilgileri Git dışında
`outputs/local-pilot-credentials.json` içindedir.

Konuşmacılar ekranında 20–30 saniye temiz sesle profil oluşturun; Ses analizi ekranında
başka bir kaydı karşılaştırın. Sonuç tanınan kişi, bilinmeyen veya belirsiz olur.
Sayfa yenilendiğinde iş korunur. Tanıma kendi kendine profil oluşturmaz veya değiştirmez.

[Kurulum, kullanım ve veri davranışı](docs/LOCAL_PILOT.md),
[uygulama kapsamı](specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md) ve
[doğrulama kanıtları](docs/evidence/2026-09-08-local-speaker-pilot/README.md).
Gerçek RTX 4060/CUDA çıkarımı ve tarayıcı akışı doğrulandı. Tekrarlı 30 saniyelik
teknik örnekle 20 işte işlem p95 0,87 sn, kuyruk dahil p95 2,72 sn ölçüldü.
Bu ölçüm gerçek kişi doğruluğu veya onlarca konuşmacı kapasitesi kanıtı değildir.

## Sıradaki çalışma

Önce farklı oturumlardan gerçek seslerle doğruluk, ardından uzun toplantı dosyaları,
sonra canlı kimlik analizi. [Uzun kayıt kararı](docs/LONG_RECORDING_STRATEGY.md) ve
[32 kayıtlık veri hazırlama rehberi](docs/DATA_COLLECTION.md) hazır.
Dosya/oturum doğrulayıcısı doğruluk puanı üretmez; gerçek kişi deneyi henüz tamamlanmadı.

## İki bilgisayardan geliştirme

[GitHub ve ikinci bilgisayar rehberi](docs/GIT_WORKFLOW.md). Kaynak kodu Git ile
eşitlenir; yerel sırlar, model paketleri, sesler ve PostgreSQL verisi ayrı hazırlanır.

## Yapı

| Yol | Sorumluluk |
| --- | --- |
| `app/backend/` | Python 3.13/FastAPI; tenant/RBAC; kalıcı profil, kayıt ve iş API'si; worker |
| `app/frontend/` | React 19/Vite 8; Türkçe/İngilizce profil, analiz ve iş ekranları |
| `app/inference/` | Ayrı CUDA veya açık CPU servisi; sabit ECAPA/Silero paketi; çalışma anında indirme yok |
| `schema/` | PostgreSQL 17/pgvector; SQLAlchemy authority ve Alembic migrasyonları |
| `app/infra/`, `app/devops/` | Yerel Compose ve ağ erişimi kısıtlı Helm tanımları |
| `src/voiceup/`, kök `pyproject.toml` | Ayrı tutulan önceki CPU/SQLite araştırma çekirdeği |
| `tools/boilerplate/` | Kullanıcının BoilerPlate / kt-scaffold 0.3.0 kaynak kopyası |

Ses vektörleri aynı PostgreSQL'de model revision ve tenant ile saklanır; her kişiyi
kaydetmek model ağırlıklarını yeniden eğitmek değildir. Web/worker veritabanı rolü
DML yetkilidir; schema değişiklikleri ayrı migration sürecinden uygulanır.

## İlerleme ve hedef

Yerel pilot kapsamı kabul edildi; plan/görevler [burada](specs/speaker-identity/PRDs/001-local-speaker-pilot/tasks.md).
Gerçek Türkçe başarı ölçümü için beş kişiden ayrı oturum kayıtları ve kayıtsız kişilerin
sorguları gerekir. Tekrar edilmiş açık örnek, yalnız teknik bağlantı testi olabilir.

Nihai hedef **DGX Spark / GB10, Linux ARM64, 128 GB CPU/GPU ortak bellek**.
Spark kurulumu, daha güçlü modeller ve onlarca kişi doğruluğu ayrıca doğrulanacak:
[proje planı](docs/PROJECT_PLAN.md), [Spark planı](docs/DGX_SPARK_PLAN.md),
[değerlendirme protokolü](docs/EVALUATION_PLAN.md), [model araştırması](docs/MODEL_RESEARCH.md).

Önceki araştırma komutları: `uv run --no-sync voiceup demo` ve `uv run --no-sync pytest`.
[Boilerplate aktarımı](docs/boilerplate-import/README.md) ve [Türkçe rehberi](docs/tr/README.md).
Kişisel ses, model ağırlığı, yerel sır, cache ve veritabanları Git'e alınmaz.
