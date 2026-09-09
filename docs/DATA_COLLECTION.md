# Gerçek kayıtlarla ilk doğruluk deneyi

9 Eylül 2026. Bu kit, [001 yerel pilotun T09 ölçümünü](../specs/speaker-identity/PRDs/001-local-speaker-pilot/tasks.md) hazırlamak içindir.
İlk hedef RTX 4060 üzerinde aynı kişiyi **farklı oturumda** tanımak ve kayıtlı olmayan kişiyi doğru reddetmektir.
Küçük ilk deney onlarca kişilik doğruluk garantisi vermez; daha sonra 10/20/50 kişilik galeriyle büyütülecek.
Uzun dosya ve canlı akış sırası [karar belgesindedir](LONG_RECORDING_STRATEGY.md).

## Toplanacak kayıtlar

Katılmayı kabul eden **yedi kişi** yeterli: başlangıçta kayıtlı beş kişi `P01`–`P05`,
başlangıçta kayıtlı olmayan iki kişi `U01`–`U02`. Gerçek isim yerine bu kodları kullanın.

| Kayıt | Adet | Önerilen içerik |
| --- | ---: | --- |
| `enrollment` | 5 | P01–P05 için kişi başına 20–30 saniye temiz, doğal konuşma |
| `known_query` | 15 | Her P kişisinden üç ayrı yeni kayıt; her biri 10–20 saniye; enrollment oturumundan farklı |
| `unknown_query` | 10 | U01 ve U02 için beşer yeni kayıt; her biri 10–20 saniye; bu kişiler henüz profile eklenmemiş olmalı |
| `new_enrollment` | 1 | U01 için ilk bilinmeyen sorgulardan sonraki ayrı bir oturumda 20–30 saniye |
| `return_query` | 1 | U01'in daha sonraki bir oturumda 10–20 saniyelik geri dönüşü |
| **Toplam** | **32** | İlk deney 30 kayıt, yeni kişinin kaydı ve geri dönüşü 2 ek kayıt |

Tek dosyada yalnız bir insan konuşsun. Kişiler farklı doğal konulardan bahsedebilir;
herkesin aynı metni okuması gerekmez. Ses tekrarı, yapay ses ve başka bir kaydın kopyası kullanmayın.
İlk kayıtları temiz ortamda alın; sonraki sorgularda mümkünse başka gün ve ikinci mikrofon da bulunsun.
Arka arkaya bölünmüş tek kayıt farklı oturum sayılmaz. Üç sorguyu mümkünse üç ayrı oturumdan alın.
Bilinmeyen sorguların da oturum çeşitliliği olsun; aynı kaynağın kırpımlarını bağımsız kanıt olarak saymayın.

Dosya biçimi WAV veya FLAC; tek dosya en fazla 50 MiB ve 120 saniye olabilir.
Pilotun model aşaması kayıtta en az 10 saniye, sorguda en az 3 saniye kullanılabilir konuşma arar;
yukarıdaki daha uzun öneriler sessizlik payı bırakır. Süreyi dosyayı tekrar ederek uzatmayın.
Bu aşamada karışık uzun toplantı dosyasını tek konuşmacılı analiz ekranına yüklemek uygun değildir.

## Hazır klasör ve kayıt listesi

Yerel çalışma kopyası [data/speaker-pilot/dataset.json](../data/speaker-pilot/dataset.json),
sürümlenen boş şablon [examples/speaker-dataset.example.json](../examples/speaker-dataset.example.json) içindedir.
`data/speaker-pilot/` altında P01–P05, U01 ve U02 klasörleri hazırlanmıştır;
dosyaları listedeki göreli yollara yerleştirin. Ses kaydı oluşturulmadı.

Her satırdaki alanları gerçek kayda göre düzenleyin:

- `id`: Bu ses parçasının tekil kayıt kodu.
- `speaker_id`: Kişinin bütün oturumlardaki aynı kodu; örneğin U01 sonradan kaydedilince de U01 kalır.
- `role`: Yukarıdaki deney görevi. Dosya listesinin sırası uygulama çalıştırma sırası değildir.
- `session_id`: Gerçek çekim oturumu; şablondaki A/B/C etiketleri örnektir. Aynı çekimi farklı adlandırmak bağımsız veri oluşturmaz.
- `source_recording_id`: Kesilmeden önceki orijinal kaydın kodu. Aynı kayıttan kesilmiş parçalar bu alanı paylaşır.
- `path`: Veri klasörüne göre yol, örneğin `P01/enrollment.wav`; mutlak yol veya `..` kullanmayın.
- `natural_single_speaker`: Dosyayı dinleyip doğal insan sesi ve tek konuşmacı olduğunu doğruladıktan sonra `true` yapın. Şablonda kasıtlı olarak `false` bulunur.

`data/` ve `outputs/` Git dışında tutulur. Şablona gerçek kişi adlarını veya sesleri eklemeyin.

## Hazırlık kontrolü

Hazırlanmış geliştirme ortamında proje kökünden PowerShell komutu:

```powershell
./app/backend/.venv/Scripts/python.exe ./scripts/validate-speaker-dataset.py --manifest ./data/speaker-pilot/dataset.json --audio-root ./data/speaker-pilot --output ./outputs/speaker-dataset-readiness.json
```

Araç model çalıştırmadan dosyaları okur. Şunları kontrol eder: kişi/sorgu sayıları,
roller arası aynı kişi için oturum/kaynak çakışmaları, yeni kişinin başlangıçta bilinmeyen olması,
yollar, biçim/boyut/süre, yinelenen dosya ve tamamen aynı çözülmüş ses örnekleri.
Bayt ve ses özeti sınırlı bloklarla hesaplanır; giriş dosyaları değiştirilmez.
Manifest en fazla 1 MiB ve 500 kayıt olabilir. Hata listesi en fazla 1.000 ayrıntı içerir;
`errors_total` toplamı, `errors_truncated` kısaltmayı bildirir. Kısaltma hatayı başarıya çevirmez.
Ses dekoderinin statik sınırları da kontrol edilir: 8–192 kHz, 1–8 kanal,
en fazla 24 milyon çözülmüş örnek, sonlu ve -1 ile 1 arasında ses değerleri;
mutlak değeri 0,999 veya üzerindeki örnekler toplamın yüzde 5'ini aşmamalıdır.
Bunlar konuşma kalitesi ve kişinin kimliği için model değerlendirmesinin yerine geçmez.

| Çıktı | Anlam |
| --- | --- |
| `initial_baseline_ready` | İlk beş kayıtlı kişi ve iki bilinmeyen kişiye ait veri kontrolleri geçti |
| `return_phase_ready` | Sonradan kayıt/geri dönüş dosyalarının kontrolleri geçti; ilk aşamanın yerine geçmez |
| `status: ready`, çıkış kodu 0 | İki veri aşaması da hazır |
| `status: not_ready`, çıkış kodu 1 | `errors` içindeki kayıt kodları ve hata nedenleri giderilmeli |
| `accuracy_evidence: false`, `model_executed: false` | Bu araç tanıma başarısı ölçmedi |

Kayıtlar gelmeden boş kitin `not_ready` sonucu vermesi beklenir.
Dosya süresi kullanılabilir konuşma süresi değildir; sessizliği veya iki kişinin konuştuğunu
bu araç otomatik doğrulamaz. Kayıp içermeyen WAV/FLAC dönüşümünde aynı örnekleri yakalayabilir;
yeniden örnekleme, kayıplı sıkıştırma veya değişik kırpımların tümünü bulamaz.
Metadata ve hash, oturum bağımsızlığının veya kişinin kimliğinin kanıtı değildir; dinleme ve kaynak kaydı gerekir.

## Veri hazır olunca yapılacak ölçüm

1. Ayrı bir değerlendirme hesabı ve boş profil alanı kullanılır. Uygulamadaki teknik deneme profili bu deneye karıştırılmaz.
2. P01–P05 kaydedilir. Model revision'ı, eşikler ve kalite kuralları sabitlenir; 15 bilinen ve 10 bilinmeyen sorgu çalıştırılır. Sorgu sonuçları profilleri güncellemez.
3. Bütün başlangıç sorguları bittikten sonra U01 kaydedilir; ayrı oturumdaki geri dönüş kaydı sınanır.
4. Doğru kimlik, yanlış kimlik, bilinmeyen, belirsiz ve iş/kalite hataları ayrı raporlanır. Hatalı veya reddedilmiş sorgular paydadan sessizce çıkarılmaz.

İlk kabul deneyi en az 14/15 doğru bilinen tanıma ve 10 bilinmeyende sıfır yanlış kabul hedefler;
U01'in kaydedilmeden önce reddedilmesi ve kaydedildikten sonra geri dönüşünün tanınması ayrıca incelenir.
**Bu hedefler henüz ölçülmedi.** On sorguda sıfır hata, gerçek yanlış kabul oranının sıfır veya yüzde birin altında olduğunu kanıtlamaz.
Eşik ayarı gerekiyorsa ayrı geliştirme verisi kullanılır; sonucu görülen kayıt tekrar kör test diye sunulmaz.
Ayrıntılı oranlar ve ölçek protokolü [değerlendirme planındadır](EVALUATION_PLAN.md).

Mevcut hazırlık aracı uygulama API'sini çağırmaz. Gerçek sorguları topluca çalıştıracak ve kalıcı kişi
kimlikleriyle sonuçları eşleştirecek değerlendirme koşucusu, T09'un kalan ölçüm işidir.
