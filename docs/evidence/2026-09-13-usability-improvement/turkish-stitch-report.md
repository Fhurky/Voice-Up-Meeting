# Koşum raporu — 2026-09-13 · Türkçe parça sınırında sözcük eşleştirmesi

1. Sonuç: Türkçe büyük/küçük harf ve kanonik Unicode farkının ürettiği sahte tekrar düzeltildi — birim 42 başarılı / PostgreSQL bütünleşme 20 başarılı / korunmuş sınır karşılaştırması 28 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Bu raporun kanıt düzeyi dar kapsamlı L1'dir.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows üzerindeki Docker/Python 3.13, gerçek FastAPI uygulamasına ASGI HTTP istekleri, gerçek ses dosyaları ve yalnız `voiceup_stitch_d25_a7d296_test` PostgreSQL veritabanı kullanıldı. Yeni GPU/model çıkarımı yapılmadı; gerçek port imzasını kullanan test sağlayıcısının çıktısı `MeetingChunkResult` doğrulamasından geçti. [Makine özeti ve dosya karmaları](turkish-stitch-tests.json), [korunmuş sonuç karşılaştırması](turkish-stitch-replay.json).

   | Koşum | Dosya veya kapsam | Başarılı | Başarısız | Atlanan |
   |---|---|---:|---:|---:|
   | Kırmızı — domain | `tests/unit/test_meeting_timeline.py` | 29 | 13 | 0 |
   | İlk bütünleşme fikstürü | `tests/integration/test_meeting_turkish_stitch.py` | 1 | 9 | 0 |
   | Kırmızı — sağlayıcı sözleşmesine uygun fikstür | Aynı bütünleşme dosyası | 5 | 5 | 0 |
   | İlk yeşil denemesi | Domain, yeni bütünleşme ve mevcut `test_meeting_worker.py` | 57 | 5 | 0 |
   | Son yeşil | Aynı üç dosya: 42 domain + 10 yeni bütünleşme + 10 mevcut worker | 62 | 0 | 0 |
   | Korunmuş model çıktısı | 8 parçalık kaynağın iki eski kopyası, varsayılan ve `en` çağrıları | 28 sınır | 0 | 0 |
   | Doğrudan bağlanmış dosyalarda statik kontrol | Black/isort başarılı; Ruff dört `EXE002` bildirdi | 2 kontrol | 1 kontrol | 0 |
   | Geçici kopyada ilk statik kontrol | Ruff/Black/isort başarılı; son mypy argümanında CR aktarım hatası | 3 kontrol | 1 kontrol | 0 |
   | Geçici kopyada son statik kontrol | Ruff/Black/isort dört dosya; mypy iki üretim dosyası | 4 kontrol | 0 | 0 |
   | Son kaynak bağlama kontrolü | Dört kod/test dosyasının kaydedilmiş SHA-256 değerleri | 4 dosya | 0 | 0 |

   Testler `scripts/stack.sh exec -T backend pytest -q` üzerinden `--tb=short`, bütünleşmede `RUN_POSTGRES_INTEGRATION=1` ve izole veritabanı geçersiz kılmasıyla çalıştı; son koşum üç dosyayı birlikte kullandı. Yalnız test veritabanına `scripts/db.sh apply` uygulandı ve koşum sonunda yalnız bu veritabanı kaldırıldı. Statik doğrulamada `scripts/quality-gate.sh` içindeki geçici kopya ve normal dosya izinleri yöntemi kullanıldı. Beş JUnit belgesi `outputs/2026-09-13-usability-improvement/turkish-stitch-*.xml` altında korundu; sayıları ve SHA-256 değerleri makine özetine işlendi.

3. Maddeler:
   **KUSUR**
   M1 `IŞIK YENİ` / `ışık yeni` komşu kaynak gözlemleri dört belirsiz sözcük yerine özgün iki sözcüğü koruyor; NFC ve Türkçe I/İ yalnız eşleştirme anahtarına uygulanıyor (DÜZELTİLDİ, `meeting_timeline.py`, `meeting_chunks.py`, 13 yeni domain ve 10 yeni bütünleşme testi).
   **TUZAK**
   M2 İlk fikstür otomatik dil için sağlayıcıya `auto` bekledi; gerçek sözleşme `None` kullanıyor. Sonraki fikstür düzeltmeleri mevcut `start_seconds/end_seconds` alanlarını ve finalizasyonda değişebilen profil adlarını esas aldı; özgün metin/zaman/belirsizlik/kalıcı satır kimliği kontrolleri korundu.
   M3 Windows bağlama izinleri doğrudan Ruff kontrolünü yanıltır; Git Bash `--junitxml=/tmp/...` argümanını da çevirdi. Beş belge gerçek oluşturuldukları test ağacından çakışmasız taşındı; geçici kopya ve son satır CR aktarımını engelleyen komut akışıyla statik kontroller geçti.
   **GÖZLEM**
   M4 Açık `tr`, iki komşuda `tr` üzerinde anlaşan otomatik dil, uyuşmayan diller, açık `en`, dili/sağlayıcısı eksik eski checkpoint, başarısız parça sonrası retry ve tamamlanmış metnin korunması gerçek PostgreSQL ile doğrulandı; `I/i` ayrımı, gerçek tekrarlar, ayrı zamanlar ve NFKC uygulanmaması domain testlerinde korundu.
   M5 SHA-256 ile eski özete, protokole ve gerçek ses dosyasına bağlanan 2.129,659875 saniyelik İngilizce kaynağın 8 parçası yeniden oynatıldı: her dil koşumunda 5.914 bağlam sözcüğü, 5.732 kaynak-zaman sahipli sözcük ve bütün zaman/olasılık/belirsizlik değerleri birebir aynı kaldı; iki kopya bağımsız veri sayılmadı.
   **AÇIK**
   M6 Bu koşum Türkçe gerçek çok parçalı toplantıda model doğruluğunu veya elli kişilik doğruluğu ölçmez. Korunmuş Türkçe örnekler tek parçalıdır; model tarifleri, mevcut WER normalizasyonu ve deney skorları değiştirilmedi.
   M7 `scripts/quality-gate.sh all` ana görev tarafından iki bağımsız düzeltme birleştikten sonra çalıştırılacaktır; bu dar rapor tam kapı, gerçek tarayıcı veya kullanıcı kabulü iddiası taşımaz.
   **YAN-ETKİ**
   M8 İki üretim dosyası, ilgili domain testi ve yeni bütünleşme testi değişti; yalnız yeni izole test veritabanı oluşturulup kaldırıldı. Kamuya açık raporlar ses, gerçek metin, kişi/tenant kimliği veya erişim bilgisi içermez; tamamlanmış uygulama kayıtları ve eski deney kanıtları yeniden yazılmadı.
