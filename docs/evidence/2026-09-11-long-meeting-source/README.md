# Koşum raporu — 2026-09-11 · Uzun toplantı kaynaklarının sınırlı bellekle okunması ve yüklemenin süreç yeniden başlatılmasından sonra sürdürülmesi.

1. Sonuç: Uzun kaynak için 5 test ve ayrı bellek/işçi regresyonunda 41 test geçti; model doğruluğu bu koşumda ölçülmedi — birim 46 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; yerel Linux x86_64, Python 3.13, PostgreSQL 17, gerçek disk ve loopback TCP HTTP; GPU/model çağrısı yapılmadı. Son otomatik test kanıtları ve kaynak hash değerleri [results.json](results.json) içindedir.

   | Gerçek sessiz WAV | Kaynak bayt | Okunan pencere | Okuyucu tepe RSS | HTTP sunucusu tepe RSS | Tam kaynak doğrulama + bütün pencereleri okuma |
   |---|---:|---:|---:|---:|---:|
   | 1 saat | 115.200.044 | 60 | 41,62 MiB | 116,89 MiB | 1,50 saniye |
   | 2 saat | 230.400.044 | 120 | 41,78 MiB | 117,28 MiB | 2,94 saniye |
   | 4 saat | 460.800.044 | 240 | 41,62 MiB | 116,95 MiB | 5,96 saniye |

   | Kontrol | Gerçek komut / test | Sonuç |
   |---|---|---|
   | Uzun kaynak sınırları | `pytest -q tests/integration/test_long_meeting_sources.py --tb=line --show-capture=no --junitxml=/tmp/voiceup-long-source-tests.xml` | 5 başarılı; 48,18 saniye |
   | Bellek + işçi | `pytest -q tests/integration/test_meeting_memory.py tests/integration/test_meeting_worker.py --tb=line --show-capture=no --junitxml=/tmp/voiceup-memory-worker-green.xml` | Bellek 35 + işçi 6 başarılı; 26,75 saniye |
   | Statik | `ruff check`, `black --check`, `isort --check-only` → yeni uzun kaynak test dosyası | Başarılı |
   | Şema hazırlığı | `scripts/db.sh apply` → yalnız bu koşumun benzersiz `_test` veritabanı | `7e86c6c45b2a` uygulandı; koşum bitince veritabanı düşürüldü |

3. Maddeler:

   **KUSUR**

   M1 Bellek sonlandırma, örnek çıkarılamayan `inconsistent_audio` nedenini `insufficient_speech` ile değiştiriyordu; önce tek gerçek PostgreSQL regresyonu başarısız oldu, ana ajanın düzeltmesi sonrası 35 bellek testi geçti; koruma `test_inconsistent_track_keeps_its_reason_when_no_memory_sample_is_eligible`.
   M2 İlk uzun kaynak test yardımcısındaki dosya boyutu alanının yanlış çağrılması düzeltildi; ilk koşum 3 başarısız / 1 başarılıydı, ürün kodunda bu ölçüm hatası yoktu; son uzun kaynak paketi 5 başarılıdır.

   **TUZAK**

   M3 Linux `ru_maxrss`, fork öncesi ebeveynin geçmiş tepesini taşıyabildiğinden büyüyen ilk sayılar okuyucu belleği olarak kullanılmadı; son ölçüm yeni süreç adres uzayının `/proc/.../status` içindeki `VmHWM` değeridir, ilk gözlem ham çıktılarda korunur.
   M4 Kaynaklar gerçek ve tamamı okunmuş PCM16 sessizliktir; dosya sistemi destekliyorsa sıfır bölgeleri seyrek saklanabilir. Disk, kaynak ayrıştırma ve HTTP süreleri gerçek konuşmanın model işleme hızı, kelime doğruluğu veya konuşmacı başarısı değildir.
   M5 Yükleme yeniden başlatma testi iki ayrı Uvicorn işletim sistemi süreci kullanır; ilk 4 MiB onayından sonra ilk süreç kapatılır, aynı PostgreSQL kaydı ve dosya üzerinden ikinci süreç devam eder. Bu, model işçisinin uzun ses çıkarımının yeniden başlatılması değildir.

   **GÖZLEM**

   M6 1/2/4 saatlik kaynaklar 28/55/110 adet en fazla 4 MiB parçayla normal rol üzerinden yüklendi; kayıt oluşturma anahtarı, ilk parça tekrarı, hash ve toplam bayt korundu, tamamlama iki kez aynı `queued` sonucu verdi; sonra kuyruk kaydı iptal edildi.
   M7 Bütün 60/120/240 kaynak penceresinin bütün ses örnekleri okundu; en büyük pencere 70 saniye / 2.240.044 bayt, ana bölgelerin birleşimi kaynak süresine eşit; dört saat geçer, dört saat + bir PCM örneği `audio_limit` ile reddedilir.
   M8 Ayrı 70 saniye, 192 kHz, 8 kanal PCM16 kaynağı 215.040.044 bayttır; özgün bütün kanallar doğrulanır, 70 saniye pencere 26.880.044 bayt mono ve en fazla 60 saniye profil örneği 23.040.044 bayt mono üretilip bütünüyle okunur.
   M9 Üst kanal/hız deneyinde işçi modülleri yüklenmiş sürecin tepe RSS değeri 125,76 MiB'dir ve testteki 256 MiB sınırının altındadır; kapsam yalnız doğrulama/pencere/örnek okumadır, HTTP gönderme ve model çıkarımı dahil değildir.
   M10 Ayrı altı işçi testi gerçek PostgreSQL üzerinde tamamlanan parça checkpoint'i, eski lease/iptal, başarısız parçada yeniden deneme, commit sırasında lease dolması, kalıcı sınır sözcüğü birleştirme ve kısa yeni kişinin metnini koruma davranışlarını doğrular; çıkarım yanıtı sözleşme dublörüdür.

   **AÇIK**

   M11 Dört saat boyunca gerçek konuşma/model çıkarımı, gerçek GPU işçi yeniden başlatması, model HTTP yükleri dahil toplam Kubernetes bellek sınırı, Spark ARM64/Apple ve temsili Türkçe 50 kişi doğruluğu bu ölçümde yoktur.
   M12 Gerçek TCP HTTP kaynak yükleme gözlemi vardır; bütün 002 toplantı yeteneği için tamamlanma veya L2/L3 iddiası yoktur. Tam proje kalite kapısı, güvenlik taramaları ve tarayıcı kabulü ana teslimin ayrı kanıtlarıdır.

   **YAN-ETKİ**

   M13 Yalnız [yeni test dosyası](../../../app/backend/tests/integration/test_long_meeting_sources.py) ve bu kanıt dosyaları eklendi; geçici sentetik kaynaklar/test sunucuları ve sahipliği doğrulanmış geçici veritabanı kullanıldı, ana uygulama verisi veya modeller değiştirilmedi, commit/push yapılmadı.
