# Spark çıkarımı: doğrulanan dosyalar ve komutlar

Bu kayıt yalnız kabul edilen 004 yeteneğinin Spark servisidir. Windows'ta web/API,
veritabanı, kuyruk ve SSH tüneli ayrı kalır. Komutlar Spark'ta yetkili kullanıcıyla
çalıştırılır; Docker daemon ayarı, sudo veya ayrı `nvidia` runtime gerekmez.

## Değişmez imaj ve kaynak sürümü

- Yerel imaj ID: `sha256:4b409e3a894b9e719e9785517bab922a8f52a1f74e69f387d6c815a0e39d8db3`.
- Etiket: `voiceup-inference:spark-4dd1012e1ff3`. Etiket değiştirilebilir; kalıcı servis tam imaj ID'sini kullanır.
- Kaynak sürümü: `/home/lab_nvidia1/voiceup-runtime/releases/4dd1012e1ff3edf09ab04c49a70ab6c61f7638bf9f0a93907c784b71e32434e5`.
- Arşiv SHA256: `669e4a425365aa615d56215009e00c44d33a9c6cc0b99e6fb4535614a7c3b100`; 1.075.200 bayt.
- [Kaynak manifesti](source-manifest.json) her dosyanın boyutunu ve SHA256 değerini içerir.

Bu yerel imaj ID'si bir kurum kayıt deposuna yüklenmiş OCI digest kanıtı değildir.
Spark native imajı başka platformdaki imajla değiştirilmemelidir.

## Çevrimdışı build

48 wheel ve model paketinin önceden hazırlanıp doğrulanması gerekir. Bu komut
yalnız doğrulanmış yerel wheelhouse'u kullanır; yeni paket çözümlemesi yapmaz.
Tam sabit taban imaj önce bir kez hazırlandı; build aşaması ağsızdır.

```sh
docker pull --platform=linux/arm64 python:3.13.14-slim-bookworm@sha256:67a1e1f215ccda113cfc024e8639049257e88f273898f595b61476d128d387e8
docker build --progress=plain --platform linux/arm64 --network=none \
  --build-context wheelhouse=/home/lab_nvidia1/voiceup-runtime/artifacts/cp313-aarch64-cu129 \
  -f /home/lab_nvidia1/voiceup-runtime/releases/4dd1012e1ff3edf09ab04c49a70ab6c61f7638bf9f0a93907c784b71e32434e5/app/inference/Dockerfile.spark \
  -t voiceup-inference:spark-4dd1012e1ff3 \
  /home/lab_nvidia1/voiceup-runtime/releases/4dd1012e1ff3edf09ab04c49a70ab6c61f7638bf9f0a93907c784b71e32434e5
docker image inspect voiceup-inference:spark-4dd1012e1ff3 --format '{{.Id}} {{.Architecture}}'
```

Build çıktısı [native-build.txt](native-build.txt) içindedir. Gerçek model testi
[smoke-execution.json](smoke-execution.json) içinde tam komutuyla kayıtlıdır;
GPU seçimi Docker CDI `--device=nvidia.com/gpu=0` kullanır.

## Kalıcı servis dosyaları

`compose.spark.yml` ve `nginx.spark.conf`, doğrulanmış `models/speaker-pilot`
dizininin yanına, `/home/lab_nvidia1/voiceup-runtime` içine kopyalanır.
Depodaki boş `.env.spark.example` bir şablondur. Hedefteki özel `.env.spark`
dosyasının izni `0600` olmalı ve yalnız şu iki değer bulunmalıdır:

- `SPARK_INFERENCE_IMAGE`: doğrulanmış `sha256:<64 hex>` imaj ID'si.
- `INFERENCE_INTERNAL_KEY`: Windows iç istemcisiyle aynı, en az 32 baytlık özel anahtar.

Bu koşumda anahtar `scripts/local_runtime_config.py` ayrıştırıcısı üzerinden
yalnız ilgili Windows alanından okundu ve SSH'nin şifreli standart girdisiyle
aktarıldı. Tam web `.env` dosyası, GitHub tokeni veya kullanıcı kimlik bilgisi
kopyalanmadı. `docker compose config` ve tam `docker inspect` çıktısı gerçek
ortamda sır içerir; herkese açık kanıta yalnız seçilmiş alanlar yazılır.

Relay aynı kabul edilmiş nginx digest'inin ARM64 varyantını kullanır. İmaj
hazırlığında bir kez çekildi; çalışma sırasında `pull_policy: never` uygulanır.

```sh
docker pull --platform=linux/arm64 nginx:alpine@sha256:4a73073bd557c65b759505da037898b61f1be6cbcc3c2c3aeac22d2a470c1752
docker compose --project-directory /home/lab_nvidia1/voiceup-runtime \
  --env-file /home/lab_nvidia1/voiceup-runtime/.env.spark \
  -p voiceup-spark -f /home/lab_nvidia1/voiceup-runtime/compose.spark.yml \
  up -d --no-build --pull never
curl --fail --silent http://127.0.0.1:8090/ready
ss -H -ltn 'sport = :8090'
```

İlk oluşturma öncesinde hedef dosyaların, Compose proje/kapsayıcı/ağ adlarının
ve 8090 portunun boş olduğu doğrulandı. Tekrarlama yalnız aynı projeye ait
nesnelerde yapılmalıdır; bu komutlar başka projeleri temizlemez.

Model yalnız `voiceup-spark_inference` iç ağına bağlıdır. Tek yayımlanan port
relay'in `127.0.0.1:8090` portudur. Relay yalnız GET `/ready` ve POST
`/v1/embeddings` yollarını iletir; Docker DNS çözümünü 5 saniyede yeniler.
Bu ayrım gereklidir: Docker 29.2.1 iç ağa tek başına bağlı kapsayıcının port
isteğini kabul etti fakat çalışan host eşlemesi üretmedi. [Docker ağ belgesi](https://docs.docker.com/compose/how-tos/networking/),
[gözlenen hedef durumu](service-internal-publish-failure.json).

## Verinin kapsamı

Aktarılan tek ses dosyası 2,87 saniyelik bir
[SpeechBrain test örneğinin](https://raw.githubusercontent.com/speechbrain/speechbrain/v1.1.1/tests/samples/ASR/spk1_snt1.wav)
değiştirilmeden tekrarlanıp 30 saniyede kesilmiş biçimidir. Kaynak SHA256
`2f7315ccf543b6368528b098cd895098c154f222cd55ff7b5f66b50feb383c56`,
kurgu WAV SHA256
`bdc68e3362aed22d18a5b9f50b7467323ed13db7871452c3c6972bb1a7f13ff9`.
Bu dosya aktarım ve sayısal uyum kontrolüne uygundur; kişi tanıma doğruluğu
ve doğal toplantı başarısı ölçümü değildir.
