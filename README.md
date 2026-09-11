# VoiceUp

Toplantılar arasında aynı konuşmacıyı yeniden tanımak için kalıcı ses profilleri.
**Yerel RTX 4060 üzerinde toplantı kaydı → konuşmacılı metin → kalıcı kişi hafızası**
akışı çalışır. İlk toplantıda öğrenilen kişilere isim verilir; farklı sonraki
kayıtta aynı kişiler tanınır ve yeterli temiz sesi bulunan yeni kişi eklenir.
Tek konuşmacılı profil oluşturma ve karşılaştırma akışı da korunur.

## Yerel uygulama

MacBook üzerinde tek konuşmacılı pilotun bütün servislerini ve modelini yerel CPU ile çalıştırmak için
[Mac kurulum rehberini](docs/MACOS_SETUP.md) kullanın. Apple Silicon/Intel paketleri
ayrıdır; yeni çok konuşmacılı toplantı modeli henüz native Apple/Spark üzerinde doğrulanmadı.

Hazırlanmış ortamda Docker Desktop açıkken:

```powershell
./scripts/start-local.ps1
```

Uygulama: **http://127.0.0.1:8081**. Yerel giriş bilgileri Git dışında
`outputs/local-pilot-credentials.json` içindedir.

Çok konuşmacılı kayıt için önce [toplantı modelini hazırlayın](docs/MEETING_WORKFLOW.md),
ardından `Toplantılar` ekranında WAV/FLAC yükleyin. Kişi sayısı isteğe bağlıdır.
Kayıt parçalar halinde işlenir; metin, konuşmacılar ve hafıza durumu sonuçta görünür.
İlk hazırlık seçili model dosyalarını indirir; normal çalışmada ses buluta gönderilmez.

Tek konuşmacılı pilotta Konuşmacılar ekranında temiz sesle profil oluşturun; Ses analizi ekranında
başka bir kaydı karşılaştırın. Sonuç tanınan kişi, bilinmeyen veya belirsiz olur.
Sayfa yenilendiğinde iş korunur. Pilotun karşılaştırma işlemi profil oluşturmaz;
toplantıdaki otomatik hafıza seçeneği ayrı bir akıştır.

[Kurulum, kullanım ve veri davranışı](docs/LOCAL_PILOT.md),
[uygulama kapsamı](specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md) ve
[doğrulama kanıtları](docs/evidence/2026-09-08-local-speaker-pilot/README.md).
Gerçek RTX 4060/CUDA çıkarımı ve tarayıcı akışı doğrulandı. Tekrarlı 30 saniyelik
teknik örnekle 20 işte işlem p95 0,87 sn, kuyruk dahil p95 2,72 sn ölçüldü.
Bu ölçüm gerçek kişi doğruluğu veya onlarca konuşmacı kapasitesi kanıtı değildir.

## Doğrulanan toplantı akışı ve açık hedefler

Sabit dört gerçek ses kaydında **5 yeni kişi → aynı 5 kişi → kısa altıncı kişi beklemede
→ yalnız altıncı kişi eklenir** senaryosu API ve tarayıcıdan geçti. Yeniden başlatma
adları/kimlikleri korudu. [Canlı ölçümler](docs/evidence/2026-09-10-meeting-delivery/frozen-meeting-flow-report.md)
ve [kullanım rehberi](docs/MEETING_WORKFLOW.md) kapsamı ve sınırları açıklar.

50 kişi kalite hedefidir, kayıt kotası değildir. Temsil edici Türkçe/50 kişilik
toplantı doğruluğu, native Spark/Apple toplantı ortamı ve bağımsız güvenlik taraması
henüz tamamlanmadı. Teams kaydı dosya olarak yüklenir; otomatik Teams bağlantısı
ve canlı analiz uygulanmadı. [Veri hazırlama rehberi](docs/DATA_COLLECTION.md).

## İki bilgisayardan geliştirme

[GitHub ve ikinci bilgisayar rehberi](docs/GIT_WORKFLOW.md). Kaynak kodu Git ile
eşitlenir; yerel sırlar, model paketleri, sesler ve PostgreSQL verisi ayrı hazırlanır.

## Yapı

| Yol | Sorumluluk |
| --- | --- |
| `app/backend/` | Python 3.13/FastAPI; tenant/RBAC; kalıcı profil, parçalı toplantı yükleme, metin ve checkpoint worker |
| `app/frontend/` | React 19/Vite 8; Türkçe/İngilizce profil, toplantı, metin ve isim düzenleme ekranları |
| `app/inference/` | CUDA toplantı veya CPU/CUDA pilot servisi; sabit Community/Whisper/ECAPA/Silero paketleri; çalışma anında indirme yok |
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
