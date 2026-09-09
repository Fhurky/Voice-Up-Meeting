# Boilerplate aktarımı

Tarih: 8 Eylül 2026. Kullanıcının Masaüstü/BoilerPlate klasörünü temel alma talebiyle
kaynak kopyalandı ve VoiceUp uygulama iskeleti üretildi.

## Ne aktarıldı?

Sağlanan klasör hazır bir ürün uygulaması değil, **kt-scaffold 0.3.0 proje
oluşturucusudur**. Oluşturucunun 496 kaynak dosyası `tools/boilerplate/` altında
korundu. Ayrı `.git` geçmişi, sanal ortamlar ve geçici önbellekler aktarılmadı.
Her dosya SHA-256 ile doğrulandı; kaynak envanteri
[source-manifest.json](source-manifest.json) içindedir.

Bu kaynakta Python 3.13.14 ile kurulan oluşturucu, boş bir hazırlık klasöründe
VoiceUp için 388 dosya üretti. Girdiler:

| Alan | Değer |
| --- | --- |
| Ürün | VoiceUp / `voiceup` |
| Ana domain | `speaker-identity` |
| Backend | `python-fastapi` |
| Persistence | `sqlalchemy-alembic` |
| Ortam değişkeni öneki | `VOICEUP_` |
| API öneki | `/api/voiceup/v1` |
| Diller | `tr`, `en` |
| Agent Platform çıktısı | Codex; inert, etkinleştirilmemiş |

Üretilen ağaç proje köküne aktarıldı. Taşınabilir göreli yollar ve orijinal üretim
manifestleri korundu. `app/`, `schema/`, `e2e/`, `rules/`, `.kt-scaffold/`, agent
yönergeleri, kalite betikleri ve dağıtım dosyaları artık uygulama temelidir.

## Mevcut kod ve çakışmalar

Mevcut `src/voiceup/`, kök testleri, `pyproject.toml`, `uv.lock`, sesler, modeller ve
veritabanları değiştirilmedi. Çakışan yalnız iki dosya vardı:

- `README.md`: önceki içerik [SPEAKER_ENGINE.md](../SPEAKER_ENGINE.md) rehberine
  taşındı; kök README yeni uygulama haritasıyla güncellendi.
- `.gitignore`: kurallar birleştirildi. Araştırmaya ait `/models/`, `/data/`,
  `/outputs/` köke sabitlendi; böylece `app/backend/app/domain/models/` yanlışlıkla
  yok sayılmıyor.

Eski iki dosyanın birebir kopyası `pre-import/`, oluşturulmuş README'nin ilk hali
`generated-README.md` altında. Güncellenen README/.gitignore proje düzenlemesi olarak
kaydedildi; `.kt-scaffold/manifest.json` orijinal üretim hashleriyle bırakıldı.
Yeni aktarım envanteri [generated-manifest.json](generated-manifest.json), son
kopya kontrolü [copy-verification.json](copy-verification.json) içindedir.

## Ne tamamlandı, ne henüz yapılmadı?

Kaynak aktarımı, VoiceUp'a özel scaffold üretimi ve mevcut araştırma çekirdeğinin
korunması tamamlandı. Bunlar ses motorunun platform API/ekranlarına bağlandığı veya
Spark CUDA ortamının hazır olduğu anlamına gelmez. Sağlanan platformdaki FastAPI,
React, PostgreSQL ve Alembic kararları korunacak. Ses profili ürün gereksinimleri,
PGVector ihtiyacı ve GPU çıkarım sınırı ilgili domain sözleşmesinde somutlaştırılacak.

Oluşturucunun web image'ları Alpine kullanır; Spark ses çıkarım ortamı ayrı
NVIDIA/Ubuntu tabanıyla doğrulanacak. Ayrıntı [DGX_SPARK_PLAN.md](../DGX_SPARK_PLAN.md).
Windows sanal ortamları Spark'a taşınmaz. Model dosyaları yeniden internetten çalışma
anında indirilmek yerine denetlenmiş, revision/hash bilgili paket olarak hazırlanır.

Aktarım sonrasında gerçek servisler başlatılmadı. Docker Linux daemon'una erişilemediği
için tam kalite kapısı geçmedi. Kontrol edilenler ve açıklar
[Koşum raporu](RUN_REPORT.md) içinde ayrı kaydedildi.
