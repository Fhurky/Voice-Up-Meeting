# Koşum raporu — 2026-09-09 · Windows özel aktarıcısının IPv4 seçimi

1. Sonuç: Son pakette toplam 13 test başarılı — birim 5 başarılı / Docker 8 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Gerçek aktarıcı üzerinden 71 HTTP kontrolü geçti; model çalıştırılmadı.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows Python 3.12, Docker Desktop ve mevcut digest ile sabitlenmiş nginx imajı kullanıldı.

   | Komut veya kontrol | Gözlenen sonuç |
   | --- | --- |
   | `RUN_DOCKER_TRANSPORT=1 .venv/Scripts/python.exe -m pytest tests/test_spark_transport_config.py -k reaches_all_workers -q -o addopts=` — eski yönlendirme | 1 başarısız test, 6 seçilmeyen test; gerçek 50 POST isteğinin 4'ü HTTP 502, 46'sı HTTP 200. |
   | Aynı dört süreçli regresyon — IPv4 düzeltmesinden sonra | 1 başarılı test; 50/50 POST HTTP 200, dört nginx sürecinin tamamı görüldü, upstream'e tam 50 farklı istek ulaştı. |
   | `RUN_DOCKER_TRANSPORT=1 .venv/Scripts/python.exe -m pytest tests/test_spark_transport_config.py -q -o addopts= -s` | 13 başarılı, 0 atlanan; 16,35 saniye. Beş Compose kontrolü, altı hatalı adres dosyası kontrolü ve iki gerçek HTTP testi. |
   | Önceden var olan özel worker → aktarıcı akışı | 21 HTTP kontrolü; yöntem/yol/boyut reddi, gövde ve kimlik başlıkları, sırların logda bulunmaması ve upstream kapanınca sınırlı HTTP 502 davranışı geçti. |
   | `ruff check` ve `ruff format --check tests/test_spark_transport_config.py` | Son durumda başarılı; ilk biçim kontrolündeki import sırası ve açık `check=False` eksikleri düzeltildi. |
   | `bash -n app/infra/nginx/start-spark-proxy.sh` | Başarılı; başlangıç betiği gerçek Alpine nginx imajında da çalıştı. |
   | `python scripts/check-dependency-admission.py` | 119 koordinat güncel; envanter özeti `abf1a5d81b9344531dd52f334a62404b4a49955831ad3b4504760fe320102ba9`. |

   | Son kaynak | SHA256 |
   | --- | --- |
   | `app/infra/docker-compose.spark.yml` | `23d740e0369906ffa65fb6563f1e66e1aa5799437d52684eb8575c0c5181d590` |
   | `app/infra/nginx/nginx.spark.conf` | `87429a7621f5b8076f5999c225d7f8fed50c32a3886076afe6756bf51892ad33` |
   | `app/infra/nginx/start-spark-proxy.sh` | `dab7b443c68667ac88321cfac121ed959060c79a48605e18ca9ec23d787a029e` |
   | `tests/test_spark_transport_config.py` | `2bc273f01ceee8bb58c8eee4c134433371d98971cb5e2ebfe0824edec5f4c121` |

3. Maddeler:
   **KUSUR**
   M1 Docker host alias'ının IPv4 ve ulaşılamayan IPv6 adreslerini birlikte çözmesi bazı nginx süreçlerinde HTTP 502 üretti; dört süreçli gerçek kırmızı/yeşil regresyonla düzeltildi. İlk uygulama ölçümü [application-benchmark-first-attempt.json](application-benchmark-first-attempt.json) içinde korunur.
   **TUZAK**
   M2 Başlangıç betiği `/etc/hosts` içinden tam bir geçerli IPv4 seçer; eksik, bozuk veya birden fazla adres varsa başlamaz. Genel nginx şablonunu değiştirmez; özel upstream'i 0600 dosya ve 0700 geçici dizinde üretir, POST yeniden denemesi yapmaz.
   M3 Canlı testler `RUN_DOCKER_TRANSPORT=1` ister; nonce sunucusu rastgele boş loopback portuna bağlanır. Gerçek SSH'nin 18090 portu kullanılmaz; üretim şablonundaki iki upstream'in 18090 kullandığı ayrıca doğrulanır.
   **GÖZLEM**
   M4 Dört nginx sürecinde toplam 50 başarılı POST ve tam 50 upstream isteği, IPv6 hatasının tekrar deneme ile gizlenmediğini gösterir; kaynak ve sonuçlar yalnız ağ taşıma davranışını kanıtlar.
   **AÇIK**
   M5 Gerçek uygulama aktarıcısının yeniden oluşturulması, yeni Spark ölçümü ve tam uygulama kalite kapısı ana ajanın ayrı koşumundadır; bu paket onları çalıştırmadı veya kişi tanıma doğruluğu ölçmedi.
   **YAN-ETKİ**
   M6 Spark Compose eki, özel nginx şablonu ve testleri güncellendi; sınırlı başlangıç betiği eklendi. Teste ait nginx konteynerleri, geçici dosyalar ve nonce sunucuları kullanıldı; konteynerler/sunucular kapatıldı. Gerçek uygulama, tünel, modeller, profiller ve kayıtlar değiştirilmedi.
