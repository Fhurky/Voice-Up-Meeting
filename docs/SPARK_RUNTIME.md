# Spark ile geliştirme

Bu düzen `kt-vibecoding-python-web-v2` profilini korur. Web, API, PostgreSQL ve iş
kuyruğu Windows'ta; ses çözme, ses etkinliği algılama (VAD) ve konuşmacı vektörü
çıkarımı Spark'ta çalışır. Profil vektörlerinin küçük karşılaştırmaları Windows'tadır.

## Başlatma

Spark açık ve Ethernet kablosu bağlıyken proje kökündeki
[Start-VoiceUp.cmd](../Start-VoiceUp.cmd) dosyasına çift tıklayın.

Bu bilgisayarda aynı dosyaya giden **VoiceUp Spark** masaüstü kısayolu da vardır.
Alternatif olarak PowerShell'de:

```powershell
.\scripts\connect-spark.ps1
```

Başlatıcı fiziksel Ethernet rotasını doğrular; Docker Desktop kapalıysa açıp yerel
Linux motorunu bekler. SSH üzerinden hazırlanmış Spark model servislerini başlatır,
GPU hazırlığını doğrular, kendi tünelini kurar ve Windows uygulamasını açar. Web/API
hazır olduğunda varsayılan tarayıcıda uygulamayı gösterir. Tarayıcı açılmasın isterseniz
`-NoBrowser` kullanın. Betik başka bir çalışma dizininden de çağrılabilir.

Sağlıklı bağlantı tekrar kullanılır; iki kez tıklamak ikinci bir başlatma oluşturmaz.
Hata halinde adım ve tanı kodu gösterilir, CMD penceresi açık kalır. Kabloyu veya
cihazı düzelttikten sonra aynı dosyayı tekrar çalıştırın. Başlatıcı yalnız kendi
kullanılamayan tünelini yeniler; başka süreçleri ve Docker projelerini durdurmaz.

İlk kurulumun Ethernet adresleri, SSH anahtarı, özel ayarlar, yerel uygulama imajları
ve Spark imajı/model paketi bu iki cihazda hazırlanmıştır. Başlatıcı günlük açılışta
bunları yeniden indirmez veya yönetici parolası istemez. Yeni bir Windows bilgisayarına
ilk kurulum dosyaları gerekir. Spark işletim sistemi açık olmalıdır; elektrik kapalı
cihazı açma veya kablo takma olayıyla arka planda sürekli izleme yapılmaz.

Alt düzey `start-local.ps1 -Mode Spark`, hazırlanmış Docker/model ortamında yalnız
uygulama ve tünel katmanını başlatmak için kalır. Spark seçimi Git dışındaki
`outputs/local-runtime-mode.txt` içinde korunur; bağlantı hatası yerel GPU'ya dönmez.

```powershell
.\scripts\spark-tunnel.ps1 -Action Status
.\scripts\spark-tunnel.ps1 -Action Stop
.\scripts\spark-tunnel.ps1 -Action Start
```

Tüneli durdurmak Spark modelini veya uygulama verilerini silmez. Yeni işler bağlantı
hatasıyla en fazla iki denemeden sonra başarısız olur; yerel GPU/CPU devreye girmez.
Her deneme 300 saniyeyle sınırlıdır; bu, iki denemenin toplam süre sınırı değildir.
Tünel geri geldiğinde yeni işler çalışabilir. Windows yeniden açıldıktan sonra
başlatıcı tekrar çalıştırılır; Windows için otomatik görev kurulmuş değildir.

Hazırlanmış Spark dosyaları değiştirildiyse `ensure-spark-runtime.py` bunların
incelemeden geçmiş hashleriyle uyuşmadığını bildirir. Yeni sürümde bu dosyalar ve
koruyan test/kayıt birlikte güncellenmelidir; günlük başlatıcı dağıtım veya imaj
güncelleme aracı değildir. Spark'taki `docker.service` açılışta etkin durumdadır.

Git Bash içindeki `bash scripts/stack.sh ps` ve diğer bakım komutları kayıtlı modu
kullanır. Spark modunda yerel inference profilini etkinleştirme girişimleri reddedilir.
Yerel model ve uygun GPU yeniden kullanılacaksa açık seçim
`.\scripts\start-local.ps1 -Mode Local` gerekir.

## Bağlantı ve sırlar

Git dışında kalan `outputs/spark-access/connection.json` dosyası şu yedi alanı taşır:

```json
{
  "host": "192.168.137.2",
  "user": "lab_nvidia1",
  "identity_file": "C:\\absolute\\private-key",
  "known_hosts": "C:\\absolute\\known_hosts",
  "host_key_alias": "10.19.57.150",
  "local_port": 18090,
  "remote_port": 8090
}
```

Örnekteki dosya yollarını bu bilgisayardaki mevcut mutlak yollarla değiştirin.
Host anahtarı takma adı, ilk bağlantıda doğrulanan aynı Spark anahtarını kullanır;
anahtar uyuşmazlığında kontrolü kapatmayın. Yeni bilgisayar kendi SSH anahtarını
kullanır ve Spark kullanıcısına onun açık anahtarı eklenir. Özel anahtar, gerçek
`.env` dosyaları ve GitHub tokeni repoya veya başka bilgisayara kopyalanmaz.

Windows tüneli `127.0.0.1:18090` adresindedir. Docker worker yalnız iç ağından
nginx'in yayınlanmayan 9080 portuna ulaşır. nginx, Docker host eşlemesindeki tek
IPv4 adresini başlarken doğrular ve geçici bellekteki özel ayarına yazar; böylece
erişilemeyen IPv6 adresi seçilmez. Bu adresle tünele
bağlanır. Spark'ta ayrı nginx aktarıcısı yalnız `127.0.0.1:8090` yayınlar; model
servisi internete çıkamayan iç ağındadır. İki aktarıcı yalnız `GET /ready` ve
`POST /v1/embeddings` uçlarını iletir. Ses ve iç API anahtarı Ethernet'te SSH
şifrelemesi içinde taşınır. Tarayıcı modeli doğrudan çağıramaz.

## Spark servisi

Doğrulanan kurulum Spark kullanıcısının `~/voiceup-runtime` dizinindedir.
[compose.spark.yml](../app/inference/compose.spark.yml) ve
[nginx.spark.conf](../app/inference/nginx.spark.conf) bu dizine konur; doğrulanmış
model paketi `models/speaker-pilot` altındadır. Özel `.env.spark`,
[boş şablondaki](../app/inference/.env.spark.example) iki değeri içerir:
doğrulanmış değişmez imaj kimliği ve uygulamayla aynı iç inference anahtarı.
Dosya izni 0600 olmalıdır; web uygulamasının bütün `.env` dosyası aktarılmaz.

```sh
cd ~/voiceup-runtime
docker compose --env-file .env.spark -f compose.spark.yml up -d --no-build --pull never
docker compose --env-file .env.spark -f compose.spark.yml ps
docker compose --env-file .env.spark -f compose.spark.yml restart inference relay
```

Servisler Docker yeniden başladığında `unless-stopped` ilkesiyle açılır. GPU,
CDI üzerinden `nvidia.com/gpu=0` olarak verilir. İmaj Python 3.13 / ARM64 / CUDA
12.9 için ayrı hash kilidiyle, ağ kapalı kurulur; çalışma sırasında indirme yapmaz.
Yeni kaynak sürümünde önce ayrı imaj oluşturulup gerçek GPU testi yapılır; ardından
özel yapılandırmadaki değişmez imaj kimliği açıkça güncellenir.

## Ölçümün sınırı

[Çalışma raporu](evidence/2026-09-09-spark-runtime/README.md) gerçek GPU, uygulama,
kesinti ve kalite kapısı kanıtlarını içerir. Aynı modelin iki cihazdaki sayısal
benzerliği, Türkçe kişi tanıma doğruluğunu kanıtlamaz. Mevcut pilotun 120 saniye ve
50 MiB sınırı devam eder; uzun toplantı ve canlı akış ayrı 002/003 taslaklarıdır.

[Tek tıklama koşumu](evidence/2026-09-09-spark-one-click/README.md), durmuş servislerden
geri dönüşü ve yeniden kullanımı doğrular; gerçek soğuk Docker Desktop açılışının
bu koşumda çalıştırılmadığını ayrıca belirtir.
