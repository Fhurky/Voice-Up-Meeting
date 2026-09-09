# İki bilgisayardan geliştirme

Kod deposu: [Fhurky/Voice-Up-Meeting](https://github.com/Fhurky/Voice-Up-Meeting).
Ana dal `main`; depo özeldir. Her bilgisayarın ayrı klonu ve yerel çalışma ortamı olur.
Sabit teknoloji profili `kt-vibecoding-python-web-v2` değişmez.

## İkinci bilgisayarda

GitHub hesabıyla Git/credential manager veya GitHub CLI üzerinden oturum açın;
tokeni URL'ye, komuta veya Git yapılandırmasına yazmayın. Sonra:

```sh
git clone https://github.com/Fhurky/Voice-Up-Meeting.git
cd Voice-Up-Meeting
git status --short --branch
```

Klon kaynak kodunu, kilit dosyalarını, gereksinimleri, testleri ve rehberleri getirir.
[Yerel pilot kurulumu](LOCAL_PILOT.md) yeni ortamın model, image, Python ve yerel ayar
adımlarını açıklar; `start-local.ps1` yalnız hazırlanmış ortamı başlatır.

Yerel kurulum komutlarının kullandığı `.venv` ve `app/backend/.venv` Python ortamları
ile doğrulanmış model kaynakları ayrıca hazırlanmalıdır; bu klon tek komutla
çalışan yeni cihaz kurulumu iddiası taşımaz.

`.env`, `app/infra/.env`, `models/`, `data/`, `outputs/`, sanal ortamlar ve Docker
veri volume'leri Git ile taşınmaz. İkinci cihazın sırlarını yerelde oluşturun;
onaylı model/image/cache paketlerini kurulum rehberine göre ayrıca hazırlayın.
GitHub tokeni model/API anahtarı değildir; uygulamanın çalışma ortamına eklenmesi gerekmez.
Bu gönderimde token yalnız GitHub kimlik doğrulama işleminin belleğinde kullanılır.

**Ses profilleri ve iş geçmişi PostgreSQL'dedir. Git pull bunları eşitlemez.**
Bu bilgisayarda oluşturulan kullanıcılar, sesler ve profil kayıtları ikinci klonda
kendiliğinden görünmez. Veri taşımak gerektiğinde veritabanı ve ses volume'ü birlikte,
ayrı bir yedekleme/geri yükleme işiyle taşınmalı; çalışan veri dizinini Git'e eklemeyin.

4060/Linux x86_64 için doğrulanan CUDA paketi Spark/Linux ARM64 kurulumu sayılmaz.
Spark cihazında [ayrı uyumluluk planını](DGX_SPARK_PLAN.md) uygulayın.

## Günlük akış

Çalışmaya başlamadan önce:

```sh
git status --short --branch
git pull --ff-only
```

Yerel değişiklik varsa önce inceleyip kendi çalışmanızı commit edin veya saklayın;
`pull --ff-only` durursa geçmişi zorla değiştirmeyin. İki cihaz aynı anda değişiklik
üretiyorsa ayrı çalışma dalları kullanıp değişiklikleri birleştirin.

Çalışma sonunda:

```sh
git status --short
git diff
# Yalnız bu çalışmanın dosyalarını seçin.
git add <dosya-yollari>
git diff --cached
# Hazır yerel Compose ortamında Git Bash/Linux kabuğuyla:
sh scripts/quality-gate.sh all
git commit -m "Somut değişiklik açıklaması"
git push
```

İlk depo aktarımında Unix kabuk betiklerinin Git çalıştırma bitleri de kaydedilir;
Windows ve Linux klonlarında satır sonları `.gitattributes` ile yönetilir.
Her gönderimde `.env` ve gerçek ses/model/veritabanı dosyalarının kapsam dışında
kaldığını kontrol edin. İki bilgisayardaki `.git` klasörlerini bulut dosya eşitlemeyle
birbirinin üzerine kopyalamayın; kod eşitlemesi GitHub üzerinden yapılır.
