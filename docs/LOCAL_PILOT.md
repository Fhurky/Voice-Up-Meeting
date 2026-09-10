# Yerel konuşmacı pilotu

Kapsam: [Accepted PRD](../specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md).
Bu sürüm tek konuşmacılı WAV/FLAC dosyalarıyla çalışır. Çok kişili toplantı kaydını
bölümleme, metne çevirme ve toplantı platformlarına bağlanma sonraki yeteneklerdir.

## Hazırlanmış bilgisayarda kullanma

1. Spark açık ve Ethernet bağlıyken proje kökündeki `Start-VoiceUp.cmd` dosyasına çift tıklayın; Docker, model bağlantısı ve uygulama hazırlanır. Yalnız yerel GPU modu için `./scripts/start-local.ps1 -Mode Local` kullanılır.
2. `http://127.0.0.1:8081` adresini açın. Yerel yönetici bilgileri Git dışında
   `outputs/local-pilot-credentials.json` dosyasındadır. Salt okunur deneme hesabı
   `outputs/local-reader-credentials.json` içindedir.
3. Konuşmacılar ekranında kişiye bir ad verin ve 20–30 saniyelik temiz, tek kişilik
   ses yükleyin. En az 10 saniye kullanılabilir konuşma ve iki tutarlı pencere gerekir.
4. Ses analizi ekranına aynı kişinin başka bir kaydını yükleyin. İşin adresi kalıcıdır;
   sayfayı yenilemek yeni iş oluşturmaz. Tanınan kişi, bilinmeyen veya belirsiz sonucu görünür.
5. Yeni kişiyi açıkça profil oluşturarak ekleyin. Tanıma işlemi kendi kendine profil
   oluşturmaz veya kayıtlı kişinin ses örneklerini değiştirmez.

Kurulumda bir `Teknik deneme (tekrarlı örnek)` profili bırakıldı. Ona ait
`outputs/live-browser/repeated-public-sample-30s.wav` dosyasıyla analiz akışını hemen
deneyebilirsiniz. Bu kayıt açık bir kısa örneğin tekrarından oluşur; farklı oturum
başarısını göstermez. Kimliği doğru ölçmek için kişilerin yeni kayıtları gerekir.

WAV/FLAC, en çok 50 MiB ve 120 saniye kabul edilir. Bir profile en çok 20 doğrulanmış
örnek eklenir. Başka kişiye ait örnek hedef profile yeterli eşik ve aday farkıyla
uymuyorsa ekleme reddedilir. Benzerlik bir olasılık veya yüzde güven değildir.

**Yaklaşık 50 katılımcı, doğruluk hedefidir; profil kayıt kotası değildir.**
Konuşmacılar ekranı mevcut toplamı gösterir. 51. veya 201. kişi sayı nedeniyle
reddedilmez; aynı kalite ve yetki kuralları uygulanır. Her profile en çok 20
doğrulanmış örnek eklenebilir. Önceki kota sürümünde oluşmuş `profile_limit` işleri
tarihsel durumuyla görünür; yeni kayıt başlatılabilir. Bu düzeltme sonrasında açık
tarayıcı sayfasını yenileyin. 100–200 kişide aynı doğruluk henüz ölçülmemiştir.

## Çalışma yapısı

Tarayıcı → FastAPI → PostgreSQL iş kaydı → ayrı worker → yerel CUDA çıkarım servisi.
Worker ECAPA vektörünü aynı PostgreSQL içindeki `vector(192)` profilleriyle karşılaştırır.
Tenant ve model sürümü filtreleri tüm adaylara uygulanır; sıralamadan sonra ilk iki
sonuç karar eşiği/farkı için alınır. Başlangıç eşikleri 0.75 / 0.45 / 0.10'dur;
gerçek ayrı oturum kayıtlarıyla kalibre edilmeden doğruluk garantisi vermez.

Web backend Python 3.13/Alpine, model servisi ayrı Python 3.13/glibc/CUDA ortamındadır.
Model servisi yalnız CUDA kabul eder; cihaz veya model paketi yoksa açık hata verir.
Çalışırken internetten model indirmez. Model dosyalarının sabit SHA-256 listesi
kodda doğrulanır; paket manifestini değiştirmek başka ağırlıkları kabul ettirmez.

Model: `speechbrain/spkrec-ecapa-voxceleb`, revision
`0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`. Mevcut CPU araştırma ortamı ayrı kalır.
Spark için ARM64/CUDA image ve cihaz doğrulaması ayrıca gerekir; 4060 image'ı
Spark'ta sınanmış sayılmaz.

## Yeni bir yerel ortamı hazırlama

Bu bölüm mevcut kurulumu silmez. İlk komut eksik yerel portları ve rastgele sırları
`app/infra/.env` içine üretir; var olan değerleri korur. 8080 başka uygulamaya
aittir; VoiceUp 8081 kullanır ve diğer uygulamanın veritabanını yönetmez.

Bağımlılıkların edinilmesi hazırlık adımıdır. `dependency-admission.json` kaynak,
sürüm ve digest envanterini kaydeder; kurum dağıtımı için dış tarayıcı/bundle kabulünün
yerine geçmez. Model paketi ve image'lar çalışma başlamadan hazırlanır.

```powershell
# Gerekli sırları image/Compose hazırlığından önce yalnız yerel .env dosyasına üretir.
.venv/Scripts/python.exe scripts/prepare-local-config.py

# Sabit Alpine ses kütüphanelerini indirir ve hashlerini doğrular.
.venv/Scripts/python.exe scripts/prepare-audio-libraries.py --arch amd64

# Önceden edinilmiş, sabit revision model cache'inden yerel paketi oluşturur.
.venv/Scripts/python.exe scripts/package-speaker-model.py --output models/speaker-pilot --verify
# Paket henüz yoksa, doğrulanmış cache kaynaklarıyla oluşturun:
# .venv/Scripts/python.exe scripts/package-speaker-model.py --output models/speaker-pilot `
#   --ecapa-source models/ecapa/0f99f2d0ebe89ac095bcc5903c4dd8f72b367286 `
#   --silero-jit .venv/Lib/site-packages/silero_vad/data/silero_vad.jit

# Harici Compose image'larını sürüm/digestleriyle önceden docker pull yapın.
# Ardından yalnız VoiceUp veri servislerini başlatın.
docker compose --project-directory app/infra -f app/infra/docker-compose.local.yml up -d postgres redis

# Uygulama rolü schema oluşturamaz; bu işlem yalnız VoiceUp container'ını kullanır.
.venv/Scripts/python.exe scripts/provision-local-runtime.py

docker compose --project-directory app/infra -f app/infra/docker-compose.local.yml build backend frontend worker migrate

# CUDA paketlerini kalıcı cache içine resmi kaynaklardan indirip lock hashleriyle doğrular.
app/backend/.venv/Scripts/python.exe app/inference/provision_wheelhouse.py --destination models/inference-wheelhouse

# İndirilmiş wheel dosyalarıyla ağsız image kurulumu; yalnız Linux x86_64 / CPython 3.13.
docker build --network=none --build-context wheelhouse=models/inference-wheelhouse `
  -f app/inference/Dockerfile.offline -t voiceup-inference:latest .
# Compose inference build de aynı Dockerfile.offline ve wheelhouse yolunu kullanır.
```

Git Bash veya Linux kabuğunda `scripts/db.sh apply` migrasyonu ayrı, kısa ömürlü
`migrate` sürecinde çalıştırır. `scripts/db.sh validate` ve `scripts/db.sh status`
ile doğrulayın; sonra uygulamayı başlatıp `scripts/create-super-admin.sh` ile yerel
yönetici oluşturun. Runtime rolü `voiceup_runtime` DML yetkilidir; migration sahibi
web/worker bağlantısında kullanılmaz. Gerçek kurum Secret/registry/StorageClass
değerleri ve Kubernetes GPU eklentisi dağıtım ortamında ayrıca hazırlanır.

## Veri ve iş davranışı

Spark üzerinde model çalıştırma için [Spark geliştirme rehberini](SPARK_RUNTIME.md)
kullanın. Başlatıcı son seçilen modu hatırlar; aşağıdaki veri/iş davranışı her iki
modda aynıdır.

Seslerin uygulama kopyaları `voiceup_speaker_audio` volume'ündedir; kullanıcının
orijinal dosyasına dokunulmaz. Profil örneğine bağlı kayıtlar profil silinene kadar
tutulur. Kullanılmayan/tanıma amaçlı dosyalar 24 saat, terminal iş sonuçları ve
tekrar anahtarları 7 gün tutulur. Saatlik bakım aktif iş ve profil referanslarını
korur. Profil silme, aramadan çıkarır; geçmiş sonuç adı da gizlenir.

İşler veritabanında tutulur. Lease ve artan sahiplenme sürümü eski worker'ın geç
gelen sonucunu reddeder. En çok iki deneme yapılır; tekrar, ikinci profil/örnek yaratmaz.
Worker healthcheck, son başarılı veritabanı ilerlemesinin zamanını kontrol eder.

## Kanıtlar ve kalan deney

[Toplu kanıt dizini](evidence/2026-09-08-local-speaker-pilot/README.md),
[backend koşumu](evidence/2026-09-08-local-speaker-pilot/backend-run-report.md),
[arayüz koşumu](../app/frontend/VERIFICATION.md) ve
[çıkarım koşumu](../app/inference/VERIFICATION.md) gerçek test sonuçlarını ayrı tutar.

4060 teknik ölçümünde 20/20 iş tek denemede CUDA ile tamamlandı: işlem p95 0,87 sn,
kuyruk dahil sunucu toplamı p95 2,72 sn; tarayıcı benzeri polling gözlemi p95 3,15 sn.
En yüksek örneklenen toplam cihaz belleği 1519/8188 MiB idi; başka süreçleri de içerir.
Bu, tek teknik profille yapılmış süre ölçümüdür.

Gerçek Türkçe kimlik doğruluğu için beş kayıtlı kişinin her birinden başka oturumda
üç sorgu ve en az iki kayıtsız kişiden toplam on sorgu gerekir. Bu veri henüz yoktur.
Tekrar edilmiş açık örnek dosyasıyla GPU/API/tarayıcı bağlantısı denenebilir;
bu dosya ayrı oturum doğruluk ölçümü olarak kullanılamaz.

Kurumun kabul ettiği çevrimdışı güvenlik tarayıcısı ve Playwright paketi sağlanmadığı
için bu iki dağıtım kapısı ayrıca açık kalır. Canlı CUA tarayıcı kontrolü, kalıcı
Playwright senaryosunun çalıştığı iddiası değildir.
