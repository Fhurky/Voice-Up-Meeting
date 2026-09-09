# VoiceUp ses tanıma araştırma çekirdeği

Bu rehber ilk Windows/CPU araştırma ortamını anlatır. Ürün temeli artık `app/`
altındaki sağlanan boilerplate'tir; hedef cihaz DGX Spark'tır. Bu çekirdek henüz
platform API ve ekranlarına bağlanmadı. Hedef ortam için [DGX_SPARK_PLAN.md](DGX_SPARK_PLAN.md).

Toplantı kayıtları arasında kalıcı konuşmacı tanıma için yerel Python prototipi.

İlk sürüm: tek konuşmacılı örnekten ses profili kaydı, sonraki kayıtta kimlik eşleştirme,
bilinmeyen ve belirsiz ses ayrımı, SQLite profil deposu ve opsiyonel toplantı bölümleme.
Türkçe doğruluk ölçümü henüz yapılmamıştır. Metne çevirme ve canlı toplantı entegrasyonu
sonraki aşamalardır.

## Kurulum

Python 3.11–3.13 desteklenir; geliştirme ortamı Python 3.12'dir. Proje klasöründe:

```powershell
uv sync --extra ml
uv run --no-sync voiceup doctor
uv run --no-sync voiceup demo
uv run --no-sync pytest
```

`uv.lock` bağımlılık sürümlerini sabitler. Başlangıç ortamı **CPU PyTorch** kullanır.
`--device cuda` için ayrıca uyumlu CUDA PyTorch kurulumu gerekir; bu ilk ortamda
CUDA çalışması doğrulanmış değildir. İlk `enroll`/`identify` ECAPA ağırlıklarını indirir;
ses çıkarımı yerelde yapılır. `demo` modelleri indirmez; sentetik vektörlerle beş kişinin
ikinci oturumda tanınmasını ve altıncı kişinin eklenmesini gösterir. Bu bir doğruluk testi değildir.

Sadece hafıza/karar kodunu çalıştırmak için `uv sync` yeterli. Sonraki komutlarda
`--no-sync` kurulu isteğe bağlı ML paketlerinin kaldırılmasını önler.

## Bir kişinin sesini kaydet ve tekrar tanı

Dosyaları `data/` altına koyun. Enrollment ve identify dosyasında **yalnız bir kişi**
konuşmalı; bu komutlarda VAD sessizliği bulur, kişileri birbirinden ayırmaz.
Kayıt için 20–30 saniye doğal ve net konuşma önerilir. En az 10 saniye kullanılabilir
ses ve en az iki tutarlı pencere gerekir.

```powershell
uv run --no-sync voiceup enroll data/ayse_oturum1.wav --name "Ayşe"
uv run --no-sync voiceup identify data/ayse_oturum2.wav --output outputs/ayse.json
uv run --no-sync voiceup profiles list
```

Çıktıda sabit `speaker_id`, ad, benzerlik, en yakın iki aday arasındaki fark ve karar
nedenleri bulunur. Bir kişiye başka mikrofonla kaydedilmiş **doğrulanmış** örnek eklemek için:

```powershell
uv run --no-sync voiceup enroll data/ayse_mikrofon2.wav --speaker-id spk_GERCEK_KIMLIK
uv run --no-sync voiceup profiles rename spk_GERCEK_KIMLIK "Ayşe Yılmaz"
uv run --no-sync voiceup profiles delete spk_GERCEK_KIMLIK
```

`spk_GERCEK_KIMLIK` yerine listeden dönen kimliği kullanın. Silme, o kişinin bütün
saklanan vektörlerini de siler. `--db data/proje_b.sqlite3` ile ayrı kişi hafızası kullanılır;
`profiles` komutunda bu seçenek `list/rename/delete` sözcüğünden önce gelir.

## Çok konuşmacılı toplantı kaydı

Community-1 erişimi için [Hugging Face model sayfasındaki koşulları](https://huggingface.co/pyannote/speaker-diarization-community-1)
kendi hesabınızdan kabul edin ve model okuma erişimi olan token'ı `HF_TOKEN` ortam
değişkenine yerel olarak tanımlayın. Token'ı sohbete veya Git'e koymanız gerekmez.
`.env.example` yalnızca şablondur; uygulama `.env` dosyasını otomatik yüklemez.

```powershell
uv sync --extra diarization
uv run --no-sync voiceup analyze data/toplanti1.wav --learn-new --output outputs/toplanti1.json
uv run --no-sync voiceup analyze data/toplanti2.wav --learn-new --output outputs/toplanti2.json
```

İlk kayıttaki yeterli kanıtlı yeni sesler `Katılımcı 1`, `Katılımcı 2`… olarak saklanır.
Sonraki kayıtta aynı veritabanıyla tekrar tanınır. Yeni biri mevcut kişilere yeterince
benzemiyorsa ve temiz konuşma kanıtı yeterliyse yeni kalıcı kimlik açılır.
`--learn-new` verilmezse profil eklenmez. Tanınan kişinin profili otomatik değiştirilmez.

Kişi sayısı biliniyorsa `--num-speakers 5`; yalnız sınırlar biliniyorsa
`--min-speakers 2 --max-speakers 20` kullanılabilir. Gerçek sayı verilmiş ve modelin
kendisi saymış olduğu deneyleri ayrı değerlendirin. Sonuçta üst üste konuşmalar
korunur; örtüşen bölgeler ses profili çıkarırken kullanılmaz.

Community-1 kurmadan, **doğrulanmış zaman aralıklarıyla** eşleştirme katmanı da denenebilir:

```powershell
uv run --no-sync voiceup analyze data/toplanti.wav --turns data/dogrulanmis_araliklar.json --learn-new
```

JSON biçimi [turns.example.json](../examples/turns.example.json) içindedir. Örnekteki
zamanlar temsili olup kendi kaydınıza göre etiketlenmelidir. Bu seçenek otomatik
diarization değildir; yanlış veya sessizlik içeren aralıklar sonuçları bozar.

## Kararlar ve değerlendirme

| Durum | Anlam |
| --- | --- |
| `recognized` | Eşik ve aday farkı yeterli; kayıtlı kimlik atandı. |
| `unknown` | Kayıtlı kimlikle güvenilir eşleşme yok; yeni kişi adayı. |
| `ambiguous` | Yakın adaylar, orta skor, az ses, tutarsız pencereler veya kimlik çatışması; kimlik atanmadı. |
| `new` | `--learn-new` ile yeterli kanıtlı yeni profil oluşturuldu. |

Kosinüs benzerliği **yüzde güven değildir**. `--match-threshold 0.75`,
`--new-threshold 0.45`, `--min-margin 0.10` başlangıç ayarlarıdır; hedef veriyle
kalibrasyon yapılmamıştır. Reddedilen kısa kayıtlar da değerlendirmede sayılmalıdır.

Etiketlenmiş karar dosyasından sorgu bazlı DIR ve bilinmeyen yanlış kabul oranı FPIR:

```powershell
uv run --no-sync voiceup evaluate examples/decisions.example.json --output outputs/metrics.json
```

Örnek kararlar yapaydır. Gerçek deneyde `ground_truth` kayıtlı kişinin kalıcı kimliği,
kayıtsız kişi için `null` olur; `predicted_id` yalnız `recognized` için kimlik taşır.
Bu araç eşik seçmez, model çalıştırmaz, DER veya süre ağırlıklı kimlik hatası hesaplamaz.

## Dosyalar ve sonraki çalışma

- [Proje planı ve mimari](PROJECT_PLAN.md)
- [Kaynaklı model karşılaştırması ve lisanslar](MODEL_RESEARCH.md)
- [5/10/20/50 kişilik gerçek ses değerlendirme planı](EVALUATION_PLAN.md)
- [Gerçek model denemesi ve mevcut doğrulama durumu](VALIDATION.md)
- `src/voiceup/`: ses hazırlama, model adaptörleri, kimlik motoru, veritabanı, CLI.
- `tests/`: kayıtlar arası kimlik, yeni kişi, belirsizlik, örtüşme ve veri doğrulama testleri.

SQLite veritabanı `data/speakers.sqlite3`, model önbelleği `models/` altındadır.
Kişi başına en çok 20 açıkça eklenen profil örneği saklanır; en eski örnekler çıkarılır.
Veritabanı model revision'ını ve boyutunu doğrular. Başka modele geçerken ayrı veritabanı
ve yeniden enrollment gerekir. Sesler, veritabanları, token'lar ve model ağırlıkları Git'e alınmaz.
Prototip veritabanı şifreli değildir ve sunucu erişim kontrolü içermez.

WAV ve FLAC tercih edin. Desteklenmeyen toplantı/video formatını önce dönüştürün:

```powershell
ffmpeg -i data/toplanti.mp4 -vn -ar 16000 -ac 1 data/toplanti.wav
```

Katılımcı başına ayrı kanallar varsa onları baştan birleştirmek yerine ayrı tutmak,
sonraki entegrasyonda bölümleme hatasını azaltabilir. İlk dosya prototipi kayıt sonrası
çalışır ve sesi RAM'e alır; canlı akış, ASR ve üretim dağıtımı henüz uygulanmamıştır.
