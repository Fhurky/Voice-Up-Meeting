# VoiceUp

Toplantılar arasında aynı konuşmacıyı yeniden tanımak için kalıcı ses profilleri.
**Yerel RTX 4060 üzerinde toplantı kaydı → konuşmacılı metin → kalıcı kişi hafızası**
akışı çalışır. İlk toplantıda öğrenilen kişilere isim verilir; farklı sonraki
kayıtta aynı kişiler tanınır ve yeterli temiz sesi bulunan yeni kişi eklenir.
Tek konuşmacılı profil oluşturma ve karşılaştırma akışı da korunur.

Mevcut düzey insan denetimli yerel pilottur; [kullanılabilirlik ve doğruluk
planı](plans/USABILITY_AND_ACCURACY.md) ölçülen sonuçları ve 50 kişilik hedefin
açıklarını ayırır. Metindeki **Bu bölümü dinle** ile ilgili kaynak sesi
en fazla 30 saniyelik bölümlerle kontrol edebilirsiniz; [kullanım rehberi](docs/tr/meeting-audio-review.md)
ve [son doğrulama](docs/evidence/2026-09-13-usability-improvement/README.md).

## Kurulum

Bilgisayarınıza ve işlemcinize uyan başlığa gidin. Her başlık sıfırdan bir bilgisayar içindir.

| İşletim sistemi | GPU | CPU |
| --- | --- | --- |
| Windows 10/11 (x86_64) | [Windows GPU](#windows-gpu) | [Windows CPU](#windows-cpu) |
| Linux (x86_64) | [Linux GPU](#linux-gpu) | [Linux CPU](#linux-cpu) |
| macOS | [macOS GPU](#macos-gpu): mümkün değil | [macOS CPU](#macos-cpu): Apple Silicon'da toplantı yok |

Hangi kurulumun ne kadar denendiği:

| Kurulum | Durum |
| --- | --- |
| Windows GPU | Çalışır durumda; RTX 4060 ve GTX 1080 Ti üzerinde gerçek toplantılarla doğrulandı |
| Windows CPU | GPU'lu bir Windows bilgisayarda doğrulandı; GPU'suz bilgisayarda ilk kurulum denenmedi |
| Linux GPU | Denenmedi; aynı Docker yapısını kullanır |
| Linux CPU | Tek konuşmacılı pilot doğrulandı; toplantı işleme denenmedi |
| macOS CPU | Fiziksel Mac'te denenmedi; tek konuşmacılı pilot Linux CPU'da doğrulandı |

Aşağıdaki adımlar koddan ve mevcut rehberlerden derlendi. Baştan sona temiz bir bilgisayarda henüz koşulmadı; bir adım takılırsa
[Sorunlar](#sorunlar) bölümüne bakın.

### Donanım

- **Bellek:** 16 GB RAM ve Docker'a en az 7 GB bellek. Bu değerlerle doğrulandı. CPU modunda 37 saniyelik kayıtta model servisi 4,4 GiB'a çıktı; uzun kayıtta ölçülmedi.
- **Disk:** Model ve paket dosyaları 6,5 GB tutar, Docker imajları bunun üstüne gelir. En az 30 GB boş alan önerilir.
- **GPU:** Yalnız NVIDIA desteklenir. GTX 10xx serisi için uygun paket otomatik seçilir. AMD veya Intel GPU'da CPU kurulumunu kullanın.
- **İnternet:** Yalnız kurulumda gerekir. Uygulama çalışırken model indirmez, ses buluta gitmez.

### Windows GPU

1. [NVIDIA sürücüsünü](https://www.nvidia.com/drivers) kurun. PowerShell'de `nvidia-smi` GPU'yu göstermeli.
2. Yönetici PowerShell'de `wsl --install --no-distribution` çalıştırın ve bilgisayarı yeniden başlatın.
3. [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) kurup açın (WSL2 motoru, Compose 2.24.4 veya üstü).
4. GPU'nun Docker'dan göründüğünü denetleyin: `docker run --rm --gpus all ubuntu nvidia-smi`
5. [Git for Windows](https://git-scm.com/download/win) (Git Bash ile gelir) ve [Python 3.13](https://www.python.org/downloads/) kurun.
6. Git Bash'te [Ortak kurulum](#ortak-kurulum) adımlarını uygulayın.
7. PowerShell'de proje klasöründe uygulamayı başlatın:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1 -Mode Local -Processor Gpu
   ```

8. Git Bash'te yönetici hesabını oluşturun: `sh scripts/create-super-admin.sh`
9. **http://127.0.0.1:8081** adresini açın.

### Windows CPU

GPU veya NVIDIA sürücüsü gerekmez.

1. Yönetici PowerShell'de `wsl --install --no-distribution` çalıştırın ve bilgisayarı yeniden başlatın.
2. [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) kurup açın (WSL2 motoru, Compose 2.24.4 veya üstü).
3. [Git for Windows](https://git-scm.com/download/win) (Git Bash ile gelir) ve [Python 3.13](https://www.python.org/downloads/) kurun.
4. Git Bash'te [Ortak kurulum](#ortak-kurulum) adımlarını uygulayın.
5. PowerShell'de proje klasöründe uygulamayı başlatın:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1 -Mode Local -Processor Cpu
   ```

6. Git Bash'te yönetici hesabını oluşturun: `sh scripts/create-super-admin.sh`
7. **http://127.0.0.1:8081** adresini açın.

CPU modu yavaştır ve ilk denemeler içindir; 5–10 dakikalık kayıtlarla başlayın. 16 mantıksal çekirdekte 14 dakikalık toplantı yaklaşık
10 dakikada işlendi, bu GPU'dan yaklaşık 7 kat yavaştır. Ölçümler [PRD 027 görevlerindedir](specs/speaker-identity/PRDs/027-meeting-cpu-mode/tasks.md).

### Linux GPU

Komutlar Debian/Ubuntu içindir; başka dağıtımda paket adlarını uyarlayın. Toplantı işleme x86_64 ister.

1. NVIDIA sürücüsünü kurun. `nvidia-smi` GPU'yu göstermeli.
2. [Docker Engine ve Compose eklentisini](https://docs.docker.com/engine/install/) kurun (Compose 2.24.4 veya üstü), sonra kullanıcınızı
   gruba ekleyip oturumu yeniden açın: `sudo usermod -aG docker $USER`
3. [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) kurup Docker'a bağlayın:

   ```bash
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

4. GPU'nun Docker'dan göründüğünü denetleyin: `docker run --rm --gpus all ubuntu nvidia-smi`
5. Git ve Python kurun (Python 3.11 veya üstü, 3.13 önerilir): `sudo apt install git python3 python3-venv`
6. [Ortak kurulum](#ortak-kurulum) adımlarını uygulayın.
7. GPU'yu seçip uygulamayı başlatın:

   ```bash
   printf 'gpu\n' > outputs/local-meeting-processor.txt
   sh scripts/stack.sh up -d --no-build --pull never
   ```

8. Yönetici hesabını oluşturun: `sh scripts/create-super-admin.sh`
9. **http://127.0.0.1:8081** adresini açın.

### Linux CPU

GPU veya NVIDIA sürücüsü gerekmez. Komutlar Debian/Ubuntu içindir; toplantı işleme x86_64 ister.

1. [Docker Engine ve Compose eklentisini](https://docs.docker.com/engine/install/) kurun (Compose 2.24.4 veya üstü), sonra kullanıcınızı
   gruba ekleyip oturumu yeniden açın: `sudo usermod -aG docker $USER`
2. Git ve Python kurun (Python 3.11 veya üstü, 3.13 önerilir): `sudo apt install git python3 python3-venv`
3. [Ortak kurulum](#ortak-kurulum) adımlarını uygulayın.
4. CPU'yu seçip uygulamayı başlatın:

   ```bash
   printf 'cpu\n' > outputs/local-meeting-processor.txt
   sh scripts/stack.sh up -d --no-build --pull never
   ```

5. Yönetici hesabını oluşturun: `sh scripts/create-super-admin.sh`
6. **http://127.0.0.1:8081** adresini açın.

ARM64 Linux'ta toplantı kurulumu çalışmaz; yalnız [tek konuşmacılı pilot](docs/MACOS_SETUP.md) (`scripts/setup-local-cpu.py`) kullanılabilir.

### macOS GPU

Mümkün değil. Uygulama Docker içinde NVIDIA CUDA ile çalışır; Mac'te Docker konteynerlere GPU veya Metal erişimi vermez. Mac'te [macOS CPU](#macos-cpu)
kurulumunu kullanın.

### macOS CPU

Mac işlemciniz neyi çalıştırabileceğinizi belirler:

| Mac | Tek konuşmacılı pilot | Toplantı işleme |
| --- | --- | --- |
| Apple Silicon (M serisi) | Var | Yok: toplantı kurulumu x86_64 Docker ister ve burada reddedilir |
| Intel | Var | Adımlar Linux CPU ile aynı, denenmedi |

Tek konuşmacılı pilot, kişi profili oluşturur ve ayrı bir kayıttaki sesi tanır; çok kişili toplantıyı işlemez.

1. [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/) kurup açın (Mac modelinize uygun sürüm, Compose 2.24.4 veya üstü).
2. Git için `xcode-select --install` çalıştırın, [Python 3.13](https://www.python.org/downloads/) kurun.
3. Depoyu indirip pilotu kurun:

   ```bash
   git clone https://github.com/Fhurky/Voice-Up-Meeting.git
   cd Voice-Up-Meeting
   python3 scripts/setup-local-cpu.py
   ```

4. Yönetici hesabını oluşturun: `sh scripts/create-super-admin.sh`
5. **http://127.0.0.1:8081** adresini açın. Sonraki açılışlarda `sh scripts/start-local-cpu.sh` yeterlidir.

Intel Mac'te toplantı işlemeyi denemek için 3. adım yerine [Ortak kurulum](#ortak-kurulum) adımlarını, ardından [Linux CPU](#linux-cpu) 4. adımını uygulayın. Docker Desktop
ayarlarında belleği en az 7 GB yapın. Ayrıntılar: [Mac rehberi](docs/MACOS_SETUP.md).

### Ortak kurulum

Windows, Linux ve Intel Mac'te toplantı kurulumu aynıdır. Windows'ta komutları Git Bash'te çalıştırın. Docker açık olmalı.

1. Depoyu indirin ve Python ortamını hazırlayın:

   ```bash
   git clone https://github.com/Fhurky/Voice-Up-Meeting.git
   cd Voice-Up-Meeting

   # Windows (Git Bash)
   python -m venv .venv
   PY=.venv/Scripts/python

   # Linux ve Intel Mac
   python3 -m venv .venv
   PY=.venv/bin/python

   $PY -m pip install packaging
   ```

2. Hugging Face erişimini hazırlayın. Bu erişim yalnız konuşmacı ayrıştırma modelini indirmek için gerekir:
   - [Hugging Face](https://huggingface.co/join) hesabı açın.
   - [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) sayfasında koşulları kabul edin.
   - [Erişim anahtarı](https://huggingface.co/settings/tokens) oluşturun (Read yetkisi yeter).
   - Proje kökünde `cp .env.example .env` çalıştırıp `HF_TOKEN=` satırına anahtarı yazın. Bu dosya Git'e girmez.

3. Yerel ayarları, ses kütüphanelerini ve konuşmacı modelini hazırlayın. İlk komut gizli değerleri `app/infra/.env` içine üretir ve GPU'ya uygun paketi seçer:

   ```bash
   $PY scripts/prepare-local-config.py
   $PY scripts/prepare-audio-libraries.py --arch amd64
   $PY scripts/prepare-speaker-model.py
   ```

4. Model servisinin paketlerini indirin (3 GB'tan fazla). CPU kurulumunda da gerekir, çünkü CPU modu aynı imajı kullanır:

   ```bash
   # Çoğu bilgisayar, GPU'suz bilgisayarlar dahil
   $PY app/inference/provision_wheelhouse.py --destination models/inference-wheelhouse

   # Yalnız app/infra/.env içinde INFERENCE_RUNTIME_PROFILE=x86_64-cu126 varsa (GTX 10xx)
   $PY app/inference/provision_wheelhouse.py --lock app/inference/requirements.cu126.txt --destination models/inference-wheelhouse-cu126
   ```

5. Hazır Docker imajlarını indirin ve uygulama imajlarını derleyin:

   ```bash
   sh scripts/stack.sh config --images | grep '@sha256:' | xargs -n1 docker pull
   sh scripts/stack.sh build backend frontend worker migrate
   ```

6. Veritabanını hazırlayın:

   ```bash
   sh scripts/stack.sh up -d --no-build --pull never --wait postgres redis
   $PY scripts/provision-local-runtime.py
   sh scripts/db.sh apply
   sh scripts/db.sh validate
   ```

7. Toplantı modellerini indirip model servisinin imajını derleyin (yaklaşık 3 GB). Komut sessiz çalışır, bitince sonucu yazar:

   ```bash
   $PY scripts/setup-local-meeting.py
   ```

8. Geldiğiniz başlığa dönüp sonraki adımla devam edin.

### Kurulumdan sonra

- **Giriş:** Giriş ekranındaki **Admin olarak giriş yap** düğmesi, kurulumda oluşturduğunuz hesapla oturum açar.
- **Sonraki açılışlar:** Windows'ta başlatma komutunu `-Processor` olmadan çalıştırın; son seçim saklanır. Linux'ta `sh scripts/stack.sh up -d --no-build --pull never` yeterlidir.
- **Durdurma:** `sh scripts/stack.sh stop`. Veriler silinmez.
- **İşlemci değiştirme:** Başlatma komutundaki seçimi değiştirin. GPU ile başlatılmış kurulumda yönetici, sol menüdeki **Ayarlar** sayfasından da geçebilir.
  Geçiş yaklaşık bir dakika sürer, işlenen toplantı varken yapılmaz ve uygulama yeniden başlayınca başlatma seçimine döner. CPU ile başlatılmış kurulumda
  GPU seçilemez. Kayıt: [PRD 028](specs/speaker-identity/PRDs/028-settings-processor-switch/PRD.md).
- **Güncelleme:** `git pull --ff-only`, ardından [Ortak kurulum](#ortak-kurulum) 5., 6. ve 7. adımları ve başlatma komutu. Veriler korunur.

### Sorunlar

- **`running scripts is disabled` hatası:** Windows betik çalıştırmayı engelliyor. Başlatma komutunu yukarıdaki `-ExecutionPolicy Bypass` biçimiyle çalıştırın.
- **`Yerel toplantı modelleri hazır değil` hatası:** Modeller başlatma süresi içinde yüklenemedi; CPU'da olabilir. Komutu yeniden çalıştırın.
- **`Meeting preparation failed` hatası:** `HF_TOKEN` değerini, model koşullarının kabul edildiğini, Docker'ın açık olduğunu ve boş diski denetleyin. x86_64 olmayan bilgisayarda bu kurulum çalışmaz.
- **Toplantı CPU'da yarıda kesilip GPU'da bitiyor:** Model servisi bellek yetersizliğinden yeniden başlamış olabilir. Docker'a daha fazla bellek verin.
- **8081 portu dolu:** `app/infra/.env` içindeki `APP_HTTP_PORT` değerini değiştirip uygulamayı yeniden başlatın.

## Yerel uygulama

Hazırlanmış ortamda Docker Desktop açıkken:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1 -Mode Local
```

Uygulama: **http://127.0.0.1:8081**. Yönetici hesabı kurulumda oluşturulur.

Çok konuşmacılı kayıt için önce [toplantı modelini hazırlayın](docs/MEETING_WORKFLOW.md),
ardından `Toplantılar` ekranında WAV/FLAC yükleyin veya **Mikrofonla kaydet**
seçeneğini kullanın. Toplantıya ad verip **Kaydı başlat**, bitince **Durdur ve
analiz et** düğmesine basın; ayrıca dosya seçmeniz gerekmez.
[Mikrofon rehberi](docs/tr/microphone-recording.md) izin, geçici disk ve cihaz
sınırlarını açıklar. Kişi sayısı isteğe bağlıdır.
Kayıt parçalar halinde işlenir; metin, konuşmacılar ve hafıza durumu sonuçta görünür.
İlk hazırlık seçili model dosyalarını indirir; normal çalışmada ses buluta gönderilmez.

Tek konuşmacılı pilotta Konuşmacılar ekranında temiz sesle profil oluşturun; Ses analizi ekranında
başka bir kaydı karşılaştırın. Sonuç tanınan kişi, bilinmeyen veya belirsiz olur.
Sayfa yenilendiğinde iş korunur. Pilotun karşılaştırma işlemi profil oluşturmaz;
toplantıdaki otomatik hafıza seçeneği ayrı bir akıştır.

[Kurulum, kullanım ve veri davranışı](docs/LOCAL_PILOT.md),
[uygulama kapsamı](specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md) ve
[doğrulama kanıtları](docs/evidence/2026-09-08-local-speaker-pilot/README.md).
Gerçek RTX 4060/CUDA çıkarımı ve tarayıcı akışı doğrulandı. Tekrarlı 30 saniyelik
teknik örnekle 20 işte işlem p95 0,87 sn, kuyruk dahil p95 2,72 sn ölçüldü.
Bu ölçüm gerçek kişi doğruluğu veya onlarca konuşmacı kapasitesi kanıtı değildir.

## Doğrulanan toplantı akışı ve açık hedefler

Sabit dört gerçek ses kaydında **5 yeni kişi → aynı 5 kişi → kısa altıncı kişi beklemede
→ yalnız altıncı kişi eklenir** senaryosu API ve tarayıcıdan geçti. Yeniden başlatma
adları/kimlikleri korudu. [Canlı ölçümler](docs/evidence/2026-09-10-meeting-delivery/frozen-meeting-flow-report.md)
ve [kullanım rehberi](docs/MEETING_WORKFLOW.md) kapsamı ve sınırları açıklar.

[Toplantı doğruluğu rehberi](docs/MEETING_ACCURACY.md), kişi tanımayı metin
hatasından ayırır ve tam referanslı kayıtlar için çevrimdışı kelime hata
ölçümünü açıklar. Eksik, fazla ve kişisi belirsiz sözler ölçümde korunur.
[11 Eylül doğruluk incelemesi](docs/evidence/2026-09-11-accuracy-audit/README.md)
uygulanan düzeltmeleri, gerçek elli kişilik sonuçları ve henüz karşılanmayan
doğruluk hedefini birlikte kaydeder.

Türkçe deneyler [results.md](results.md) günlüğüne otomatik kaydedilir.
[Veri seti araştırması](plans/TURKISH_DATASET_RESEARCH.md),
[deneyleri çalıştırma rehberi](docs/TURKISH_EVALUATION.md) ve
[13 Eylül gerçek ölçümleri](docs/evidence/2026-09-13-turkish-evaluation/README.md)
kaynakları, skorları ve sınırlamaları açıklar. Küçük Türkçe görüşme deneyinde
kesin konuşmacı sayısı bilgisi fayda sağladı; bu sonuç 50 kişi başarısı değildir.

[Genişletilmiş Türkçe test raporu](docs/evidence/2026-09-13-expanded-turkish/README.md),
3.176 yeni kısa kayıt ve 12 yeni beş dakikalık görüşme kesitiyle kapsamı genişletir.
MediaSpeech haberleri, FLEURS okunmuş cümleleri ve doğal görüşmeler ayrı ölçülür;
klip sayısı, ses süresi ve gerçek kişi sayısı birbirinin yerine kullanılmaz.

50 kişi kalite hedefidir, kayıt kotası değildir. Temsil edici Türkçe/50 kişilik
toplantı doğruluğu, native Spark/Apple toplantı ortamı ve bağımsız güvenlik taraması
henüz tamamlanmadı. Teams kaydı dosya olarak yüklenir; otomatik Teams bağlantısı
ve canlı analiz uygulanmadı. [Veri hazırlama rehberi](docs/DATA_COLLECTION.md).

## İki bilgisayardan geliştirme

[GitHub ve ikinci bilgisayar rehberi](docs/GIT_WORKFLOW.md). Kaynak kodu Git ile
eşitlenir; yerel sırlar, model paketleri, sesler ve PostgreSQL verisi ayrı hazırlanır.

## Yapı

| Yol | Sorumluluk |
| --- | --- |
| `app/backend/` | Python 3.13/FastAPI; tenant/RBAC; kalıcı profil, parçalı toplantı yükleme, metin ve checkpoint worker |
| `app/frontend/` | React 19/Vite 8; Türkçe/İngilizce profil, toplantı, metin ve isim düzenleme ekranları |
| `app/inference/` | CUDA toplantı veya CPU/CUDA pilot servisi; sabit Community/Whisper/ECAPA/Silero paketleri; çalışma anında indirme yok |
| `schema/` | PostgreSQL 17/pgvector; SQLAlchemy authority ve Alembic migrasyonları |
| `app/infra/`, `app/devops/` | Yerel Compose ve ağ erişimi kısıtlı Helm tanımları |
| `src/voiceup/`, kök `pyproject.toml` | Ayrı tutulan önceki CPU/SQLite araştırma çekirdeği |
| `tools/boilerplate/` | Kullanıcının BoilerPlate / kt-scaffold 0.3.0 kaynak kopyası |

Ses vektörleri aynı PostgreSQL'de model revision ve tenant ile saklanır; her kişiyi
kaydetmek model ağırlıklarını yeniden eğitmek değildir. Web/worker veritabanı rolü
DML yetkilidir; schema değişiklikleri ayrı migration sürecinden uygulanır.

## İlerleme ve hedef

Yerel pilot kapsamı kabul edildi; plan/görevler [burada](specs/speaker-identity/PRDs/001-local-speaker-pilot/tasks.md).
Gerçek Türkçe başarı ölçümü için beş kişiden ayrı oturum kayıtları ve kayıtsız kişilerin
sorguları gerekir. Tekrar edilmiş açık örnek, yalnız teknik bağlantı testi olabilir.

Nihai hedef **DGX Spark / GB10, Linux ARM64, 128 GB CPU/GPU ortak bellek**.
Spark kurulumu, daha güçlü modeller ve onlarca kişi doğruluğu ayrıca doğrulanacak:
[proje planı](docs/PROJECT_PLAN.md), [Spark planı](docs/DGX_SPARK_PLAN.md),
[değerlendirme protokolü](docs/EVALUATION_PLAN.md), [model araştırması](docs/MODEL_RESEARCH.md).

Önceki araştırma komutları: `uv run --no-sync voiceup demo` ve `uv run --no-sync pytest`.
[Boilerplate aktarımı](docs/boilerplate-import/README.md) ve [Türkçe rehberi](docs/tr/README.md).
Kişisel ses, model ağırlığı, yerel sır, cache ve veritabanları Git'e alınmaz.
