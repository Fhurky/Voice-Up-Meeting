# Plan — Pascal NVIDIA GPU üzerinde yerel çalışma

1. Requirement 1: `config.py`, `models.py` ve `meeting_models.py` içine açık
   `x86_64-cu126` profilini ve profil başına Whisper hesaplama türünü ekle; profil
   ve hesaplama türü testleriyle cu128 regresyonunu koru.
2. Requirement 2: `requirements.cu126.in` ve mevcut kilidin CUDA dışı pinleriyle
   kısıtlanmış `uv pip compile --torch-backend cu126` hash kilidini üret;
   `provision_wheelhouse.py` torch tablosunu sürüm anahtarlı yap; kabul kaydını
   yeni yetki dosyası, artifact bağları ve yayın tarihleriyle güncelle.
3. Requirement 3: Dockerfile'lara `INFERENCE_REQUIREMENTS` derleme argümanı,
   Compose'a profil/kilit değişkenleri ekle; `local_runtime_config.py` profil tablosu,
   `prepare-local-config.py` GPU algılama ve `setup-local-meeting.py` wheelhouse seçimi.
4. Requirement 4: `docs/LOCAL_PILOT.md` içine Windows/Pascal kurulum bölümü ekle.
5. Requirement 1–4: Odaklı testler, gerçek Compose çözümleme, ağsız imaj derleme,
   GTX 1080 Ti CUDA/HTTP hazırlığı, yerel uygulama ve sabit koşum raporu.
