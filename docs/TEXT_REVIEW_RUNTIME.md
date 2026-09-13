# Yerel metin modeli bağlantısı

Bu isteğe bağlı özellik `kt-vibecoding-python-web-v2` profilindeki FastAPI
uygulamasından, önceden kurulmuş Ollama modeline erişir. Model kurulumu veya
indirmesi yapmaz; konuşmacı/ASR çalışma modunu değiştirmez.

Ollama bilgisayarda açıkken, proje kökünden mevcut Python ile çalıştırın:

```powershell
python scripts/setup-local-text-review.py --check --model qwen3.5:27b
python scripts/setup-local-text-review.py --enable --model qwen3.5:27b
```

macOS üzerinde aynı komutlarda `python3` kullanılabilir. Yardımcı yalnız
`127.0.0.1:11434` üzerindeki kurulu model listesini ve model bilgisini okur;
bulut/uzak model işaretlerini reddeder ve dosyanın SHA-256 kimliğini sabitler.
Bu komut kurulumun varsayılan modelini sabitler. Varsayılan modelin dosyaları
değiştiğinde aynı etkinleştirme komutuyla yeni kimliği açıkça seçmek gerekir.
Diğer kurulu modeller inceleme panelinden her istek için seçilebilir; bunun
için varsayılan ayarı değiştirmek gerekmez. Eski kimlikle uygulama otomatik
başka modele geçmez.

Mevcut kurulumu kaydedilmiş düzeltme desteğine güncellerken, çalışan yerel
PostgreSQL'e eklemeli migration'ı arka ucu yeniden başlatmadan önce uygulayın:

```sh
sh scripts/db.sh apply
sh scripts/db.sh validate
sh scripts/db.sh status
```

Bu sürümün şema head'i `8283cb0d9e4b`'dir. Özgün transcript metni değişmez;
düzeltmeler ayrı tabloda tutulur. Kümede aynı migration dağıtımın migration
release adımıdır; geliştirici bilgisayarından küme veritabanına uygulanmaz.

Ardından mevcut başlatıcıyı çalıştırın: Windows'ta `scripts/start-local.ps1`,
diğer yerel ortamlarda `sh scripts/stack.sh up -d --no-build --pull never`.
Çalışan ortamda yalnız bağlantı ve API'yi yenilemek için:

```sh
sh scripts/stack.sh up -d --no-deps --no-build --pull never nginx backend
sh scripts/stack.sh restart backend
```

Son komut nginx'in etkin yapılandırmasını ve değişen arka uç adresini yeniden
yükler. Yerel GPU, CPU ve Spark seçimleri korunur; Spark modunda mevcut kapalı
9080 köprüsü aynı nginx yapılandırmasına eklenir. Bu komutlar model indirmez.

Kapatmak için `python scripts/setup-local-text-review.py --disable` ve ardından
aynı yenileme komutları kullanılır. Model ve diğer yerel ayarlar korunur.

Yerel nginx `correction-preview` ve `correction-suggestion` metin inceleme yollarında 110 saniye bekler; uygulama sınırı
100, istemci sınırı 120 saniyedir. Diğer yerel API yollarının bekleme süresi
değişmez. Bu ayar, model yavaş olsa da uygulamanın yanıt veya hata kararının
önce proxy tarafından kesilmesini önler; model yanıtını hızlandırmaz.

## Bağlantı ve ayarlar

Yardımcı Git dışında tutulan `app/infra/.env` içinde yalnız `TEXT_REVIEW_*`
ayarlarını ve `outputs/local-text-review-enabled.txt` seçimini günceller;
diğer satırları ve sırları yazdırmaz. Compose bunları uygulamaya şu adlarla verir:

| Ayar | Varsayılan | Anlamı |
|---|---|---|
| `VOICEUP_TEXT_REVIEW_ENABLED` | `false` | İsteğe bağlı incelemeyi açar. |
| `VOICEUP_TEXT_REVIEW_URL` | `http://nginx:9081` | Operatörün seçtiği model servisinin kök adresi. |
| `VOICEUP_TEXT_REVIEW_MODEL` | `qwen3.5:27b` | Kurulumun sabit varsayılan model adı. |
| `VOICEUP_TEXT_REVIEW_MODEL_DIGEST` | boş | Açık modda zorunlu 64 küçük onaltılık SHA-256 karakteri. |

9081 Docker içinde özeldir, bilgisayara yayımlanmaz. Yalnız `/api/tags`,
`/api/show` ve `/api/chat` belirli HTTP yöntemleriyle iletilir. Model indirme,
silme ve oluşturma uçları kapalıdır. İş/veri servisleri yalnız iç ağda kalır;
mevcut nginx host-gateway takma adını kullanır. Ollama'nın localhost dinlemesi,
güvenlik duvarı veya genel internet çıkış kuralları değiştirilmez.

Docker Desktop'ın host-loopback erişimi gerekir. Windows Docker Desktop ile
bağlantı gözlendi; macOS/native Linux cihaz doğrulaması ayrıca gerekir. Native
Linux'ta host-gateway'in loopback servisine erişebileceği varsayılmaz. Bağlantı
kurulamıyorsa orijinal transkript kullanılabilir; bu helper adresi LAN'a açmaz.

## Küme

Mevcut kurum içi Ollama servisi aynı namespace içinde önceden hazırlanmalıdır.
Model pod'una `app.kubernetes.io/part-of: voiceup` ve
`app.kubernetes.io/component: text-review` etiketleri verilir. Ortam
`platform.yaml` içindeki `textReview.enabled: true`, yalnız bu pod seçicisine
TCP 11434 çıkışını ekler. Başka namespace/IP veya internet izni oluşturulmaz.
Ollama servisine giriş izni kendi iş yükünün sahibine aittir.

Kümede `textReview.enabled: true`, mevcut arka uç Ingress'inin okuma süresini
110 saniye olarak ayarlar. Bu anotasyon yalnız seçilen Ingress'e uygulanır;
yereldeki yol kapsamından farklı olarak arka ucun `/api` yollarını kapsar.
Mevcut `Prefix` eşleştirmesi korunur; regex/snippet eklenmez. ingress-nginx'te
bir Ingress'in `use-regex` seçimi aynı host'taki bütün yolları etkilediği için
ayrı regex rotası kullanılmadı. [Denetleyici belgesi](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/#use-regex).

Dört `VOICEUP_TEXT_REVIEW_*` değeri arka ucun mevcut `existingSecret` ile
seçilen, önceden oluşturulmuş tek Secret'ında bulunur. URL kurum içi servisin
adresidir; yerel Docker nginx adresi kümeye taşınmaz. Secret içeriği chart veya
overlay dosyasına yazılmaz. `textReview.enabled` ağ izni ile uygulamanın
`VOICEUP_TEXT_REVIEW_ENABLED` seçimi birlikte hazırlanmalıdır. Model çalışma
zamanında indirilmez; bu değişiklik yeni image veya bağımlılık içermez.

[English](TEXT_REVIEW_RUNTIME_EN.md)
