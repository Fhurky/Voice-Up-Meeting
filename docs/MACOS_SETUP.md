# MacBook üzerinde yerel kullanım

Bu kurulum web arayüzünü, API'yi, PostgreSQL'i ve ses modelini aynı MacBook'ta
çalıştırır. Spark gerekmez. Apple Silicon ve Intel için Docker'ın Linux mimarisine
uygun **CPU** paketi seçilir; Apple GPU/Metal kullanılmaz. Sabit
`kt-vibecoding-python-web-v2` uygulama yapısı korunur.

Bu Mac CPU kurulumu tek konuşmacılı WAV/FLAC kayıtlarıyla profil oluşturur ve ayrı kaydı
tanır. 20–30 saniye temiz, tek kişilik konuşmayla başlayın; sınır 50 MiB/120 saniyedir.
Çok kişili toplantı dökümü ve hafızası [002 kapsamında](../specs/speaker-identity/PRDs/002-long-recording-analysis/PRD.md)
yerel x86_64 NVIDIA üzerinde doğrulandı; bu CPU paketi o toplantı modelini içermez.
Mikrofon yakalama ayrı [007 gereksiniminde](../specs/speaker-identity/PRDs/007-microphone-meeting-capture/PRD.md)
izlenir. Native Apple toplantı çalışma zamanı ve mikrofon özelliği bu rehberle tamamlanmış sayılmaz.

## Önkoşullar

- Kendi GitHub hesabınıza private repo erişimi verilmiş olmalı.
- Mac modelinize uygun [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/)
  açık olmalı; Compose en az 2.24.4 ve Linux konteynerleri kullanılmalı.
- Git ve Python 3.11 veya üstü gerekir; [Python 3.13](https://www.python.org/downloads/)
  tercih edilebilir. Uygulama konteynerleri sabit Python 3.13 kullanır.
- İlk kurulum internet, imaj/model paketleri için boş disk ve Docker'a yeterli
  bellek gerektirir. Bu depoda gerçek Mac bellek/hız ölçümü henüz yoktur.

```bash
git clone https://github.com/Fhurky/Voice-Up-Meeting.git
cd Voice-Up-Meeting
python3 --version
docker compose version
```

Kendi GitHub hesabınızla giriş yapın. Repo sahibinin token'ını, `.env` dosyasını veya
SSH özel anahtarını almanız gerekmez. Erişim ayrıntısı [Git rehberinde](GIT_WORKFLOW.md).

## İlk kurulum

Repo kökünde:

Modeli başka bir kurulumdan alacaksanız, doğrulanmış `models/speaker-pilot`
klasörünü `manifest.json` ve bütün alt dosyalarıyla yeni klondaki aynı konuma
kopyalayın. Aşağıdaki kurulum komutu mevcut paketin hashlerini doğrular ve modeli
yeniden indirmez; eksik diğer bağımlılıkları hazırlamaya devam eder. Model paketi
kullanıcı hesabı veya ses profili taşımaz; eski `.env` ve veritabanını kopyalamayın.

```bash
python3 scripts/setup-local-cpu.py
sh scripts/create-super-admin.sh
```

İlk komut Docker mimarisini denetler; eksik sırları oluşturur, sabit model/paketleri
hash ile doğrular, imajları hazırlar ve mevcut yerel veritabanı migration'larını
uygular. Tekrar çalıştırmak mevcut sırları/verileri korur. İkinci komut ilk yönetici
adını ve parolasını terminalden sorar; parola yazdırılmaz.

Kurulum sonunda verilen adresi açın; varsayılan **http://127.0.0.1:8081**.
**Admin olarak giriş yap** düğmesine basıp `Konuşmacılar` ekranında profil oluşturun; `Ses analizi`
ekranında başka kaydı karşılaştırın. Bugünkü pilotta profil oluşturma açık kullanıcı
işlemidir; tanıma yeni kişiyi kendiliğinden kaydetmez.

Yerel Compose bu düğmeyi varsayılan olarak etkinleştirir. Düğme mevcut aktif
`super_admin` hesabıyla normal oturum açar; hesap oluşturmaz, parola sıfırlamaz
ve yetki eklemez. İlk hesabı hazırlamak için yukarıdaki `create-super-admin.sh`
adımı yine gereklidir. Normal kullanıcı adı/parola formu kullanılabilir; çıkıştan
sonra kendiliğinden yeniden giriş yapılmaz.

Tek bir aktif yönetici varsa ek ayar gerekmez. Birden çok aktif yönetici varsa
`app/infra/.env` içindeki isteğe bağlı `LOCAL_ADMIN_USERNAME` değerine kullanmak
istediğiniz mevcut hesabın kullanıcı adını yazın. Bu ad çözülemezse veya hesap
kullanılamazsa başka yöneticiye otomatik geçilmez. Düğmeyi kapatmak için
`LOCAL_ADMIN_LOGIN_ENABLED=false` ayarlayıp `sh scripts/start-local-cpu.sh`
komutunu yeniden çalıştırın; ayar değişiklikleri servisler yeniden oluşturulunca uygulanır.

Bu giriş yalnız `development` ortamında ve yerel loopback adresinden kullanılabilir.
Uygulamanın genel ayar varsayılanı kapalıdır; staging/production/test ortamında
etkinleştirme reddedilir. Mac CPU ve NVIDIA/Spark yerel modları aynı giriş kurallarını kullanır.

İlk hazırlık resmî model dosyalarını indirir. Çalışan model servisi internet erişimi
kapalı özel ağdadır; günlük başlangıç paket/model indirmez. Proxy kullanıyorsanız
[Hugging Face resmî indirme adreslerinin](https://huggingface.co/docs/hub/models-downloading)
erişilebilir olması gerekir; yönlendirme sonrası dosya hash kontrolü de korunur.

## Günlük kullanım ve güncelleme

Docker Desktop açıkken:

```bash
sh scripts/start-local-cpu.sh
```

Bu komut hazır dosya/imajları doğrular; build veya indirme yapmaz. Kod güncellemesinden
sonra yeni kaynakları imajlara almak için kurulum komutu tekrar gerekir:

```bash
git pull --ff-only
python3 scripts/setup-local-cpu.py
```

Git yerel değişiklikler nedeniyle durursa onları koruyarak uzlaştırın. Git kullanıcı,
ses veya profil taşımaz: veriler yerel PostgreSQL Docker volume'larında, sırlar
`app/infra/.env` içinde, model/paketler `models/` altındadır.

Servis durumunu görmek veya yalnız bu projeyi durdurmak için:

```bash
sh scripts/stack.sh --mode cpu ps
sh scripts/stack.sh --mode cpu stop
```

Bu durdurma veritabanını silmez. Aynı bilgisayarda önceden CUDA/Spark kullanılmışsa
önce o modun servislerini kendi başlatıcısıyla durdurun; sonra
`python3 scripts/setup-local-cpu.py --switch-mode` ile açıkça CPU'ya geçin. Başlatıcı
çalışan başka moda veya başka Docker projesine otomatik müdahale etmez.

## Sorunlar ve kanıt sınırı

Başlatıcı hata aldığı adımı gösterir. Docker kapalıysa açın; sürüm/mimari hatasında
önkoşulları kontrol edin. Eksik model/imaj için ilk kurulum komutunu tekrar çalıştırın.
Hash uyuşmazlığında dosya sessizce değiştirilmez; yerel paketi inceleyin. 8081 doluysa
`app/infra/.env` içindeki `APP_HTTP_PORT` değerini boş bir porta ayarlayın.
Alt komut çıktısı sır içerebileceğinden ekrana dökülmez; `.env`, tam Compose çıktısı
ve kimlik bilgilerini hata raporuyla paylaşmayın.

CPU aynı model/eşikleri kullanır; hız donanıma bağlıdır. 300 saniyelik iş sınırı veya
ses kalite reddi başarı sayılmaz. Gerçek Mac kurulumu ve kişi doğruluğu Linux CPU
testinden çıkarılamaz. Kontroller ve açık Mac testi [kanıt raporundadır](evidence/2026-09-10-local-cpu-runtime/README.md).

10 Eylül 2026 doğrulaması: x86_64 ve gerçek Linux ARM64 donanımında ayrı ayrı dokuz
CPU HTTP kontrolü geçti; CPU ile kalıcı profil oluşturma/tanıma entegrasyonu da geçti.
ARM deneyi Spark üzerinde GPU erişimi kapalı bir test konteynerindeydi; Spark bu
Mac kurulumunun bir parçası değildir. Docker ARM emülasyonundaki başarısız ses deneyi
ayrı raporlandı. Fiziksel MacBook ilk kurulum ve tarayıcı kabulü hâlâ açıktır.

Aynı gün ayrı, başlangıçta boş bir Docker motorunda GitHub kopyasından ilk kurulum
ve günlük yeniden başlatma da doğrulandı: [temiz kurulum raporu](evidence/2026-09-10-fresh-cpu-install/README.md).
Bu deneydeki Linux başlangıç düzeltmesi ve kopyalanan model ayrıntıları raporda kayıtlıdır;
fiziksel Mac kabulünün yerini tutmaz.
