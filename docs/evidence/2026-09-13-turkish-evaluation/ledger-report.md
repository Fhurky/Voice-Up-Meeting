# Koşum raporu — 2026-09-13 · Atomik deney günlüğü ve geçmiş sonuçların kaynak bağlı aktarımı

1. Sonuç: Günlük, gerçek dosya/CLI sınırlarında ve kimlik değerlendirme API koşucusunda çalışıyor; yayınlama uyumluluk kusuru düzeltildi — birim 259 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Sayı, 230 testlik regresyon koşumu ve son düzeltmeden sonraki 29 hedefli testin toplamıdır; tekrarlar bağımsız model deneyi sayılmaz.
2. Koşulan: Sabit `kt-vibecoding-python-web-v2`; yerel Windows/Python 3.12 araştırma araçları, pytest ve mevcut HTTP fikstürü. Ürün Python 3.13/FastAPI yığını bu dar koşumda değiştirilmedi.

   | Komut / dosyalar | Gözlenen sonuç |
   |---|---|
   | `.venv/Scripts/python.exe -m pytest tests/test_experiment_ledger.py tests/test_public_speaker_metrics.py tests/test_public_speaker_report.py tests/test_public_speaker_evaluation.py -q` | Çıkış 0; o kaynak anında 28 günlük + 98 metrik + 13 rapor + 91 gerçek HTTP/fikstür koşucu testi = 230 başarılı. |
   | `.venv/Scripts/python.exe -m pytest tests/test_experiment_ledger.py -q --junitxml=outputs/2026-09-13-turkish-evaluation/ledger-tests.xml` | Çıkış 0; uyumluluk regresyonu eklenmiş son 29 test başarılı; özel yerel JUnit dosyası test sayısını taşır. |
   | Altı değişen günlük/kimlik kaynak ve test dosyasında `ruff check` ve `ruff format --check` | Son kaynak biçim/lint denetimi başarılı. Son testin biçimi ilk denetimde kaldı; biçimlendirildikten sonra altı dosya geçti. |
   | `record-experiment.py --backfill-reviewed-history --results-md results.md` | Çıkış 0; açık envanterdeki 13 tarihsel kayıt eklendi. Gerçek CLI testinde aynı çağrı ikinci kez 0 kayıt ekledi ve dosya baytları korundu. |
   | Kaydedilmiş `asr-dev-auto.private.aggregate.json` için `record-experiment.py --kind asr_clips --experiment-metadata outputs/2026-09-13-turkish-evaluation/asr-dev-auto.public-metadata.json --results-md results.md` | Çıkış 0; tamamlanmış 40/40 model denemesinin eksik yayın kaydı eklendi; çıkarım tekrarlanmadı. |

3. Maddeler:

   **KUSUR**

   M1 İlk kırmızı koşumda günlük modülü bulunmadığından 22 test hata verdi; modül ve gerçek dosya davranışı eklenince geçti. Sonradan eklenen kimlik CLI testinin ters fikstür sırası düzeltilerek gerçek kanonik skor yolu doğrulandı.
   M2 Canlı ASR denemeleri sürerken yeni bütün-kayıt mühür alanı önceki v1 kayıtlara yanlışlıkla zorunlu tutuldu; ikinci ASR koşusu 40/40 tamamlandı fakat günlük yayını çıkış 1 oldu. Eski v1 için mevcut anlamsal hash, yeni kayıt için ek tam mühür doğrulaması korunarak uyumluluk düzeltildi; `test_earlier_v1_snapshot_without_optional_full_record_seal_still_accepts_append` korur.

   **TUZAK**

   M3 Eski düşük seviyeli komut metadata verilmeden günlük yazmaz; standart deney çağrısı `--experiment-metadata` ve `--results-md` içerir. Metadata değişikliği eski kimlik koşumuyla devam etmeyi reddettirir; başarısız günlük yazımı model sonucunu yok etmez.
   M4 Geçmiş 13 kayıt bütün eski debug dosyalarını skorlanabilir deney saymaz; kalibrasyon, reddedilen iki ASR adayı, 50 kişi başarısızlıkları ve referanssız Türkçe gözlem görünürdür. Real-TurnTurk zayıf otomatik referansı ile MediaSpeech klip WER'i ayrı protokollerdir.

   **GÖZLEM**

   M5 Aynı sonuçta dosya değişmez; değişen devam/terminal durum aynı deneyin yeni sürümüdür. Kilit, yazma hatası, bozuk blok, yanlış payda, özel alanlar, Unicode dil uyuşmazlığı, eski v1, gerçek CLI ve HTTP devamı sınandı; ham ses/metin/kimlik yayımlanmadı.

   **AÇIK**

   M6 Bu dar koşum ürünün tam profil/güvenlik kapısı veya gerçek model doğruluk kabulü değildir. Türkçe gerçek model sonuçları ve tamamlanmış günlüğün son bağımsız sayısal denetimi ana teslim raporunda ayrıca izlenir.

   **YAN-ETKİ**

   M7 Yeni `scripts/experiment_ledger.py`, `scripts/record-experiment.py`, `tests/test_experiment_ledger.py`, `docs/EXPERIMENTS.md`, `results.md` ve bu rapor; değişen kimlik koşucu/rapor bağlantısı, kimlik koşucu testi, `scripts/README.md` ve yalnız günlük geçici dosya ignore kuralları bu alt göreve aittir.
   M8 Geçmiş kaynak JSON'ları değiştirilmedi. Yerel test JUnit'i ve otomatik ASR yayın onarımı metadata'sı ignore edilen `outputs/2026-09-13-turkish-evaluation/` altında kaldı; commit/push ve uygulama verisi değişikliği yapılmadı.
