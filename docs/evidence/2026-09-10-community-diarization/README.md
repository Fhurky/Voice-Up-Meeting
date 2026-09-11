# Koşum raporu — 2026-09-10 · Community-1 çevrimdışı model hazırlığı ve parçalı konuşma deneyi

1. Sonuç: Sabit Community-1 paketi ve kaynak-sınırı regresyonu doğrulandı, ayrı RTX 4060 ortamında 12 kayıt işlendi; konuşmacı ayrımında kalan hatalar nedeniyle ürünün otomatik profil akışı doğrulanmış değildir — birim 475 başarılı / tarayıcı 0 başarılı / atlanan 6; karar bekleyen: yok.

2. Koşulan: `kt-vibecoding-python-web-v2`; paket hazırlığı Windows ve Linux Python 3.13, gerçek model deneyi ayrı Linux Python 3.13.14 / RTX 4060 Laptop GPU ortamında yürütüldü. 475 sayısı her test paketi/ortamının son başarılı yürütmesini toplar: 78 Windows + 78 Linux paketleyici, 107 kaynak-sınırı, 153 backend ve 59 frontend; önceki kapı veya red/green tekrarları yeniden sayılmaz. Kaynak ve protokol özetleri, tam sayımlar ve anonim vaka ölçümleri [results.json](results.json) içindedir. Bu rapor model ön hazırlık kesitini dondurur; sonraki uçtan uca toplantı teslimi ayrı kanıt gerektirir.

   | Kontrol | Gözlenen sonuç |
   |---|---|
   | Paketleyici ve mevcut model hazırlama regresyonu | Windows 78/78, ağsız Linux 78/78; son koşumlarda başarısız/atlanan test yok |
   | Kaynak-sınırı adaptörü ve ilişkili araştırma regresyonu | Linux 107/107: `test_backends.py` 63, `test_audio.py` 29, `test_pipeline.py` 15 |
   | Kaynak-sınırı lint/biçim | Kök Ruff 0.13.3 çıkış 0/0; ek Ruff 0.16.1 lint çıkış 1 ile değiştirilmemiş HEAD'de de bulunan 3 bulgu verdi |
   | Gerçek model paketi | 8 dosya, 32.832.557 byte; bütün boyut/SHA-256 değerleri eşleşti |
   | Hazır paketi çevrimdışı doğrulama ve tekrar kullanma | İki akışta da ağ girişimi 0, token okuma 0 |
   | Linux wheel dosyalarının gerçek metadata incelemesi | 62 ek wheel / 68.354.431 byte doğrulandı; 238 bağımlılık ve 125 Python sürüm koşulunda çatışma yok |
   | Ayrı CUDA model koşumu | 12/12 vaka çıktısı; doğrudan kaydedilmiş çıkış kodu 0; runtime tokeni yok, ağ kapalı |
   | CUDA bellek | En yüksek ayrılmış tensor belleği 1.591 GiB; ayrılmış önbellek dahil rezerve bellek 1.963 GiB |
   | Ayrı Windows CPU araştırması | Python 3.12.10 ile toplam 12 vaka gözlemi; PowerShell sarmalayıcı çıkışı 1, doğrudan son Python çıkış kodu kaydedilmedi |
   | Adaptör değişiminden sonraki son tam kalite kapısı: `scripts/quality-gate.sh all` | Çıkış 0; backend 153/153, frontend 59/59; config, admission, geçici PostgreSQL/migrasyon, sözleşme, governance ve chart adımları geçti |
   | Güvenlik: `scripts/security-gate.sh` | Çıkış 2: `required offline security tool is unavailable: gitleaks`; tarama başarılı sayılmadı |
   | Mevcut uygulamayı koruma kontrolü | Uygulama imajı aynı, readiness HTTP 200; deney konteyneri çalışır bırakılmadı |
   | Bu koşumda yapılmayan altı kabul kontrolü | Fiziksel macOS yayını, Spark ARM64 modeli, yerleşik TorchCodec dosya çözümü, tam toplantı/metin/profil/tarayıcı akışı, 1/2/4 saat dayanıklılık, yaklaşık 50 kişilik temsilî Türkçe doğruluk |

   Model: `pyannote/speaker-diarization-community-1`, revision `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee`; ağırlıklar [sabit manifestle](../../../scripts/diarization-model-manifest.json) seçildi. CUDA deneyinde `pyannote.audio 4.0.7`, `torch/torchaudio 2.8.0+cu128`, `torchcodec 0.7.0` kullanıldı. Temel imajın 63 dağıtımı korunarak 62 araştırma paketi ayrı ortama eklendi; ürün bağımlılık kabulü sağlanmış sayılmadı. Model varsayılanları sabit tutuldu, kişi sayısı ipucu veya sonuçlara göre eşik ayarı yapılmadı. Girdi önceden çözülmüş waveform idi; yerleşik medya dosyası decoder'ı bu kanıtla doğrulanamaz.

   | CUDA vakası | Kaynak süresi (sn) | Beklenen / bulunan kişi | İşleme (sn) | VAD referansına göre yanlış kişiye atanan süre (sn) |
   |---|---:|---:|---:|---:|
   | Kullanıcının sağladığı kayıt | 52,629 | Belirlenmedi / 1 | 4,703 | Referans yok |
   | `single_1` | 32,280 | 1 / 2 — hatalı | 1,029 | 0,00 |
   | `single_2` | 33,355 | 1 / 1 | 1,114 | 0,00 |
   | `single_3` | 42,960 | 1 / 1 | 1,304 | 0,00 |
   | `single_4` | 31,780 | 1 / 1 | 1,117 | 0,00 |
   | `mixed_1_continuous` | 32,000 | 2 / 2 | 0,924 | 3,79 |
   | `mixed_1_gapped` | 18,800 | 2 / 2 | 0,436 | 0,00 |
   | `mixed_2_continuous` | 32,000 | 2 / 2 | 0,911 | 2,09 |
   | `mixed_2_gapped` | 18,800 | 2 / 2 | 0,415 | 0,00 |
   | `silence` | 40,000 | 0 / 0 | 0,247 | 0,00 |
   | `single_fragmented` | 34,000 | 1 / 1 | 0,944 | 0,00 |
   | `overlap_pair` | 12,000 | 2 / 2 | 0,194 | 0,86 |

   Sağlanan kayıtta tek akustik konuşmacı altında 18 aralık bulundu: örtüşmesiz tekil toplam 38,6775 saniye, konuşma etkinliği tespiti (VAD) ile kesişen temiz aday toplamı **37,4445625 saniye**. Bu süre >20 saniye kapısını geçiyor; ECAPA tutarlılığı, kalıcı kimlik veya profil kaydı bu deneyde çalıştırılmadı. Kaynağın PCM özeti `20abf085623d4fa6bf267661a4e79d05876c594c195feeefebdd754cf73387f5`; adı, özel dosya yolu ve ses içeriği rapora alınmadı.

   Beklenen kişi sayısı bilinen 11 vakanın 10'unda sayılar eşleşti; bu **kimlik precision/recall/F1 veya yaklaşık %91 kimlik başarısı değildir**. Ölçüm, dört kamu konuşmacısından hazırlanmış sınırlı vakalarda akustik küme sayısıdır. Zaman hatası, kaynakların bilinen yerleştirme çizelgesine taşınan Silero konuşma maskelerini referans alır: `(kaçırılan kişi-saniyesi + fazladan kişi-saniyesi + yanlış kişiye atanan kişi-saniyesi) / referans kişi-saniyesi`. 10 ms ölçüm adımı ve 0 saniye sınır toleransı kullanıldı. Bu otomatik referans insan tarafından etiketlenmiş konuşmacı ayrım hata oranı (DER) değildir; bir vaka sessizlik olduğu için hata oranının paydası sıfırdır ve oran boş bırakıldı.

   Normal çıktı aynı anda konuşan kişileri korur; exclusive çıktı her anda tek etiket seçerek hizalamayı kolaylaştırır. `overlap_pair` vakasında normal çıktı iki kişi için 7 aralık, exclusive çıktı tek kişi için 2 aralık verdi. Exclusive çıktıyı tek başına kanıt kabul etmek ikinci kişiyi kaybettirir. Normal çıktıdan seçilen aday kanıtta bile referans örtüşmesinin 1,10 saniyesi kaldı; bu yüzden süre kapısı tek başına otomatik profil yetkisi değildir. `single_fragmented` vakasının VAD ile kesişen tekil toplamı 19,81653125 saniyedir; normal aralık toplamının 20,0475 saniye olması yeterli sayılmadı.

   CPU'nun ilk protokolü sekizinci sonuçtan sonra dokuzuncu vakada kaynak dışına taşan `18,96471875` saniyelik bitişi, kaynak `18,8` saniye olduğu için reddetti. İlk sekiz gözlem korunarak v2 protokolü kalan dört vakada ham aralıkları saklayıp kaynak zaman aralığıyla kesiştirdi. Girdi, model, eşik veya kişi ipucu değiştirilmedi. Son CPU ve CUDA kayıtlarında vaka bazında kişi sayıları ve otomatik referans hata ölçümleri aynı; bu gözlem CPU sürecinin çıkış kodu 0 olduğu iddiasına dönüştürülmedi.

   Paket hazırlama ve dar kaynak-sınırı adaptörü altgörevleri için otomatik **L1** kanıtı vardır; 002 toplantı yeteneği tamamlanmadı ve yeni akış için L2/L3 iddiası yoktur. Bağımsız GPU/CPU komut satırı deneyi gerçek HTTP/tarayıcı kabul akışının yerine geçmez; mevcut uygulamanın readiness yanıtı da yeni özelliği doğrulamaz. Güvenlik taraması ayrıca açıktır. Adaptörün son kaynaklarıyla 107 test ve ardından tam profil kapısı geçti; ilk kapı kaydı tarihsel olarak ayrıca korundu. Ham yerel protokoller, JUnit dosyaları ve kapı kayıtları Git dışında `outputs/2026-09-10-community-diarization/` altında korunur; [results.json](results.json) bunların SHA-256 değerlerini taşır.

3. Maddeler:

   **KUSUR**

   M1 `single_1` tek konuşmacıda ikinci etiket üretti; iki kesintisiz karışımda 3,79 ve 2,09 saniye yanlış kişi ataması kaldı. Model veya eşikler bu sonuçları gizlemek için değiştirilmedi.

   M2 Kaynak sonunu aşan geçerli model aralığı ilk CPU ayrıştırmasını durdurdu; [araştırma adaptöründe](../../../src/voiceup/backends.py) kaynakla kesişim ve [regresyonla](../../../tests/test_backends.py) DÜZELTİLDİ, 107 test geçti.

   M3 Paket yayınının POSIX boş-hedef yarışı ve proxy başlığı normalizasyonu DÜZELTİLDİ; [hazırlayıcı](../../../scripts/prepare-diarization-model.py) ve [testleri](../../../tests/test_prepare_diarization_model.py) Windows/Linux'ta doğrulandı.

   M4 Ek Ruff 0.16.1 kontrolünde iki I001 ve bir BLE001 bulundu; aynı bulgular değiştirilmemiş HEAD'de de var. Kök Ruff 0.13.3 lint/biçim geçti; dar adaptör düzeltmesi bu eski bulguları değiştirmedi.

   **TUZAK**

   M5 10/11 kişi-sayısı eşleşmesi kalıcı kimlik doğruluğu değildir; VAD referanslı zaman hatası, insan etiketli DER veya 50 kişilik kabul sonucu olarak sunulamaz.

   M6 CPU'da tamamlanmış 12 ölçüm bulunması PowerShell çıkışı 1'i ortadan kaldırmaz; doğrudan Python çıkış kodu yok. CUDA çıkışı 0 ayrıca kaydedildi.

   M7 Exclusive çıktı örtüşmeyi tek etikete indirir; süreyi normal, tekil, kaynakla sınırlı ve VAD ile kesişen aralıklardan hesaplamak gerekir. >20 saniye kalite/tutarlılık/unknown kontrollerini atlatmaz.

   **GÖZLEM**

   M8 Sağlanan kayıtta tek konuşmacı ve 37,4445625 saniye temiz aday kanıt bulundu; herhangi bir profil oluşturulmadı, kimlik eşleştirilmedi veya metin üretilmedi.

   M9 CUDA'da 12 vaka çevrimdışı işlendi; 1,591 GiB en yüksek tensor belleği gözlendi. Model yükleme süresi 2,750 saniye, sağlanan kaydın işleme süresi 4,703 saniyedir.

   M10 Son tam kalite kapısı exit 0 ve mevcut uygulama readiness HTTP 200 verdi; deney sonunda uygulama imajı değişmedi. [Makine kaydı](results.json) ilk/son kapıyı ve kaynak özetlerini ayırır.

   **AÇIK**

   M11 Gitleaks bulunmadığı için güvenlik kapısı exit 2 ile durdu; güvenlik taraması ve üretim bağımlılık kabulü tamamlanmadı.

   M12 Fiziksel macOS, Spark ARM64, yerleşik TorchCodec decoder ve 1/2/4 saat dayanıklılık kontrolleri bu koşumda yapılmadı; yerel waveform deneyi bunların yerine geçmez.

   M13 Toplantı API/metin/otomatik hafıza/tarayıcı entegrasyonu, yaklaşık 50 kişilik temsilî Türkçe ölçüm ve L3 kullanıcı kabulü bu ön hazırlık koşumunda açık; dar kaynak-sınırı düzeltmesi bu yetenekleri tamamlamaz.

   **YAN-ETKİ**

   M14 Sabit model paketi ve araştırma bağımlılıkları Git dışında hazırlandı; ayrı CUDA deney ortamı kullanıldı. Uygulama/veritabanına yazım ve model/eşik değişikliği yapılmadı.

   M15 Accepted 002 belgeleri parçalı kanıt ve ayrı kimliklerle güncellendi; model hazırlayıcı/manifest/testleri, kaynak-sınırı adaptör düzeltmesi ve bu iki özet dosyası eklendi. Token, özel ses, ham konuşma aralıkları veya kişi vektörleri bu kanıta kopyalanmadı.
