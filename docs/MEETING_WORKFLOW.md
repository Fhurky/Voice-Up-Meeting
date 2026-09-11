# Toplantı kaydından konuşmacılı döküme

Durum: [002 PRD](../specs/speaker-identity/PRDs/002-long-recording-analysis/PRD.md)
içindeki kayıt yükleme, konuşmacılı metin, elle isim verme ve kalıcı hafıza akışı
11 Eylül 2026'da yerel RTX 4060 üzerinde gerçek model ve tarayıcıyla doğrulandı.
Sabit dört kayıtta hafıza 5→5→5→6 ilerledi: aynı kişiler tanındı, kısa konuşan
yeni kişi bekledi, yeterli konuştuğunda yalnız bir yeni profil eklendi.
[API/model kanıtı](evidence/2026-09-10-meeting-delivery/frozen-meeting-flow-report.md)
ve [tarayıcı kanıtı](evidence/2026-09-10-meeting-delivery/meeting-memory-browser-report.md)
kontrollü İngilizce kaynaklarla sınırlıdır; Türkçe/50 kişilik toplantı doğruluğu
ve native Spark/Apple toplantı çalışma zamanı ayrıca doğrulanmalıdır.
Son kullanıcı seçimi "Kaydı yüklemek yeterli; tanıma ve hafızayı tamamla" oldu.
Bu nedenle güncel teslim yüklenen dosyaya odaklanır; önceki mikrofon isteği ayrı
[007 yeteneğinde](../specs/speaker-identity/PRDs/007-microphone-meeting-capture/PRD.md)
Accepted ve henüz uygulanmamış olarak korunur. Teams kaydının otomatik alınması gerekmez.

## Kullanıcının izleyeceği akış

1. `Toplantılar` ekranında toplantıya ad ver ve WAV/FLAC ses dosyasını seç; sınır 4 saat ve 2 GiB'dır.
2. İstersen katılımcı üst sınırını veya gerçekten konuşan kişi sayısını belirt; dosya aktarımı tamamlanınca analizi başlat.
3. Sistem uzun kaydı sınırlı parçalarda işler; kişi etiketlerini parçalar arasında birleştirir.
4. Sonuçta zaman, konuşmacı ve söylenen metin satırlarını gör.
5. Tanınan kişi mevcut adıyla görünür. Yeni kişinin kısa sözleri toplantı etiketiyle
   yazılır; aynı kişiye ait ayrı temiz bölümler biriktirilir. Toplam 20 saniyeyi
   aşınca süre yeterli olur; kalite ve kimlik kontrolleri de geçerse kişi kalıcı
   geçici adla kaydedilir ve sonraki kayıtta aynı kimlikle tanınabilir.
6. Toplantı sonucu veya profil ekranından kişiye elle isim ver. Model gerçek ismi sesten çıkarmaz.
7. Aynı kişilerin farklı kaydını yükle; kayıtlı isim ve kimlikler korunmalı, yeni kişi yalnız yeterli temiz kanıtla eklenmeli.

Doğrulanan kabul örneği: ilk kayıttaki beş kişiye isim verildikten sonra farklı ikinci
kayıtta aynı beş profil görünür; üçüncü kayıtta altıncı yeni kişi varsa yalnız
bir yeni profil eklenir. Yeniden deneme ve servis yeniden başlatma bu sayıları
ve adları değiştirmedi. Altı kaydedilen ses örneğinin kaynak saflığı yüzde 99'u
geçti; ayrı tekrar toplantısında mevcut altı profilin sesleri, vektörleri ve
adları değişmedi. Bu saflık oranı genel kimlik tanıma doğruluğu değildir.

Bir saatlik kontrollü dayanıklılık kaydı gerçek worker'da 12 parçada tamamlandı;
tanınan beş kişi ve mevcut profil hafızası korundu. Bu kayıt aynı sesin tekrarıyla
hazırlandığından yeni bir doğruluk verisi sayılmaz. [Toplu test raporu](evidence/2026-09-11-meeting-quality/delivery-report.md)
cihaz, süre ve kalite açısından doğrulanmamış hedefleri de listeler.

Katılımcı üst sınırı ile kesin konuşan sayısı farklıdır: toplantıya beş kişi
katılmış olsa da yalnız üçü konuşmuş olabilir. Sayı verilmezse sistem tahmin eder.
Her kısa parçada bütün katılımcıların konuştuğu varsayılmaz; sayıyı tutturmak için
iki ses körce birleştirilmez. Sonuç beklentiyle uyuşmazsa fark görünür kalır.
Elle isim vermek kimliği veya ses vektörünü değiştirmez; aynı adı alan iki profil
birleşmez. Henüz kalıcı profili olmayan kişinin toplantı adı da hafızaya
kaydedilmiş kişi adı gibi gösterilmez.

Bir sözcüğün zaman aralığı farklı kişilere yayılıyor ve tek kişinin açık desteği
yoksa metin korunur, konuşmacı belirsiz gösterilir. Modelin zaman hatası başka
bir kişinin sözünü kesin kimlikle yazdırmamalıdır; bu nedenle bazı metinler
inceleme gerektirebilir.

Örnek çıktı yalnız gösterim içindir, modelin ürettiği bir sonuç değildir:

| Zaman | Konuşmacı | Söylediği |
| --- | --- | --- |
| 00:05–00:09 | Ayşe | Bugünkü gündemin ilk maddesi yeni tasarım. |
| 00:10–00:14 | Konuşmacı 2 · profil için yeterli konuşma bekleniyor | Ben önce test sonuçlarını paylaşayım. |
| 00:16–00:20 | Ayşe | Tamam, ardından tasarıma geçelim. |

## Model görevleri ve doğru hafıza davranışı

| İş | Seçilen ilk model |
| --- | --- |
| Kimin ne zaman konuştuğunu ayırma | pyannote Community-1 |
| Konuşmayı özgün dilinde yazıya çevirme | Whisper large-v3 / faster-whisper için CTranslate2 dağıtımı |
| Önceki kayıtlardan kişiyi tanıma | Toplantıya özel WeSpeaker 256 boyutlu temsil ve bağımsız SpeechBrain ECAPA-TDNN 192 boyutlu denetim |

İlk iki modelin Spark hazırlığı tamamlanmadı. Community-1 için kullanıcının
yerel Hugging Face tokeniyle seçilmiş sabit model yapılandırmasına erişim
doğrulandı, sekiz dosyalı çevrimdışı paket hazırlandı ve model ayrı bir RTX 4060
deneyinde çalıştırıldı. Yeni toplantı çalışma zamanı ayrı bir yerel x86_64 CUDA
imajıyla seçilir; mevcut tek kişilik ECAPA/Silero akışı da aynı sınırda korunur.
Güvenli hazırlık, seçilmiş dosyaları
lisans, boyut ve SHA-256 envanteriyle paketler; eksik/bozuk paket hazır sayılmaz.
Token yalnız ilk hazırlıkta kullanılır, ses kayıtları buluta gönderilmez.
Çalışma sırasında model/bağımlılık indirilmez; hazır paket çevrimdışı doğrulanır.

Toplantıda aynı kişiye güvenle bağlanan kısa sözler biriktirilir. Konuşma
boşlukları, üst üste konuşma ve tekrar işlenen kaynak süreyi artırmaz. Yeni
hafıza kaydı için kalite kontrolünden geçen tekil konuşmanın 20 saniyeyi aşması
ve en az üç farklı doğal konuşma örneği bulunması gerekir. Seçilen örnekte
destekli ikinci bir ses saptanırsa kişi hafızaya kaydedilmez; transkript ve
toplantıdaki kişi etiketi korunur. Yetersiz ses, en yakın kayıtlı kişiye zorlanmaz.
Tanınan kişilerin mevcut ses örnekleri ve vektörleri otomatik genişletilmez.
İsim vermek yalnız gösterim adını değiştirir.

İki modelin vektörleri ayrı alanlarda, kendi model/sürüm kimliğiyle aranır;
boyutlar birbirine dönüştürülmez. İki kanıt çelişirse sistem otomatik profil
oluşturmaz. Mevcut yalnız ECAPA profilleri korunur ve kendi uzaylarında aranır.

Projenin Python ortamı etkinleştirildikten sonra model hazırlama ve çevrimdışı
doğrulama komutları aşağıdadır. İlk komut gerektiğinde kök `.env` içindeki
`HF_TOKEN` değerini kullanır; ikinci komut token okumaz ve indirme yapmaz.

```bash
python scripts/prepare-diarization-model.py
python scripts/prepare-diarization-model.py --verify
```

Bu komutlar model dosyalarını hazırlar; yeni modelin Python bağımlılıklarını
kurmaz veya çalışan uygulamanın modelini değiştirmez. [Deney ve sınırları](evidence/2026-09-10-community-diarization/README.md).

## Yerel RTX toplantı çalışma zamanını hazırlama

Ön koşul: mevcut [yerel NVIDIA pilotu](LOCAL_PILOT.md), 63 paketli temel
`models/inference-wheelhouse`, `models/speaker-pilot` ve Linux x86_64 Docker
hazır olmalıdır. Hazırlık sırasında internet yalnız sabit model ve paket dosyaları
için kullanılır; Community-1 erişimi gerekiyorsa mevcut kök `.env` içindeki
`HF_TOKEN` okunur. Token komut satırına veya loglara taşınmaz.

```powershell
python scripts/setup-local-meeting.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1 -Mode Local
```

İlk komut mevcut model/paket hazırlayıcılarını çağırır, model hashlerini ve
iki wheelhouse'un kilitli hashlerini doğrular, bağımlılık kabul kontrolünü çalıştırır
ve `Dockerfile.meeting` ile ağsız derleme yapar. Başarıdan sonra
`outputs/local-meeting-enabled.txt` içine `enabled` kaydeder. Hazırlık başarısızsa
eski seçim korunur; eksik veya bozuk paket etkinleştirilmez. Yeni imaj temel pilot
imajını ezmez. `--verify` yalnız çevrimdışı doğrular; indirme, derleme ve seçim değişikliği yapmaz.

Sonraki `start-local.ps1` ve `scripts/stack.sh` çağrıları kayıtlı yerel seçimde
`docker-compose.meeting.yml` ekini kullanır; normal başlatma model indirmez ve
imaj derlemez. Güncellemeden sonra imajı yenilemek için hazırlığı yeniden çalıştırın.
Yerel toplantı modu etkinse `start-local.ps1`, uygulama bağlantısını yazmadan önce
özel model servisinde CUDA ve üç sabit modelin hazır olduğunu doğrular; başlangıç
beklemesinin üst sınırı 180 saniyedir. Modeller bu sürede hazır olmazsa komut hata
verir ve yerel seçim korunur; model hazır olana kadar yeni analiz başlatmayın.
Bu ek yalnız yerel x86_64 NVIDIA içindir. CPU/Mac ve Spark başlangıç modları yerel
toplantı seçim dosyasını kullanmaz; bu kod ARM64 model uyumu veya Spark kabulü iddiası değildir.

### Depolama ve worker kapasitesi

Kubernetes tanımında `app-backend.audioStorage.size` başlangıçta `10Gi`,
`app-worker.resources.limits.memory` ise `512Mi`, bellek isteği `256Mi` değerindedir. Bu değerler uzun
toplantılar için yük testiyle yeterli bulundu anlamına gelmez. Toplantı başına
2 GiB sınırı ve tenant başına varsayılan 10 GiB kota, bütün tenantların toplam
disk kullanımını sınırlamaz; aynı kalıcı birimde profil sesleri de tutulur.
İşletimde disk kapasitesi, eşzamanlı tenant kotalarının toplamı, saklama süresi,
profil sesleri ve geçici işleme alanı birlikte hesaplanarak ayrılmalıdır.
Birimin boş alanı izlenmeli; çok tenantlı kurulumun varsayılan 10 GiB birime
sığdığı varsayılmamalıdır.

Worker bütün kaydı belleğe almaz; yine de en yüksek kabul edilen örnekleme
hızındaki 310 saniyelik ses parçası, Python süreci, HTTP yanıtı ve çözümleme
tamponları birlikte ölçülmelidir. Gerçek 310 saniyelik 192 kHz/8 kanal kaynakta
dosya okuma ve örnek çıkarma tepe belleği 213,39 MiB ölçüldü; bu ölçüm HTTP/model
çıkarımını içermez ve `256Mi` sınırının bütün worker için yeterli olduğunu
göstermez. Ayrı gerçek HTTP ölçümünde yürütücü 119 MB istek ve 8,2 MB yanıtla
223,54 MiB kullandı; veritabanı checkpoint yazımı bu ölçümde yoktur. Ek çalışma
payı için chart isteği 256 MiB, sınırı 512 MiB olarak ayarlandı;
[ölçüm raporu](evidence/2026-09-10-meeting-delivery/worker-http-rss-report.md).
1/2/4 saatlik kaynaklar 12/24/48 pencereyle, iki ayrı HTTP süreci
arasında yükleme devamıyla doğrulandı; [koşum raporu](evidence/2026-09-11-long-meeting-source/window310-report.md).
Kaynak limitleri ölçülen tepe bellek ve eşzamanlılık
üzerinden dağıtım değerlerinde ayarlanır; bu değişiklik yerel RTX, CPU, Apple
ve Spark ortamları için ortak bir kapasite veya performans garantisi vermez.

Yeni toplantılar 300 saniyelik ana bölge ve iki yanda beş saniyeye kadar bağlamla
işlenir. Güncellemeden önce açılmış toplantılar özgün 60 saniyelik pencere
ayarlarıyla devam eder; yeniden deneme tamamlanan parçaları yeniden saymaz.

Yükleme 4 MiB parçalarla ilerler. Sayfayı yenilerseniz aynı dosyayı yeniden
seçin: sunucudaki parçalar hashleriyle karşılaştırılır, eksik bölüm aktarılır.
Aktarımı duraklatmak toplantıyı silmez; analiz iptali ve toplantı silme ayrı onaylardır.
Toplantı silme kalıcı kişi profillerini silmez. Profil için yeterli ses bulunmayan
kişi metinde kalır; elle verilen toplantı adı tek başına hafıza kaydı oluşturmaz.

Spark'ta yeni diarization paketinin ARM64/TorchCodec uyumu da hazırlanmalıdır;
model erişimi tek başına bütün kurulumu tamamlamaz. Kullanıcının seçtiği yerel
RTX 4060 üzerinde Python 3.13 geliştirme doğrulaması ayrı yapılır; bunun sonucu
Spark/ARM64 kabulü yerine geçmez. Ayrı bir CPU araştırma deneyi de uygulamanın
desteklenen çalışma ortamını değiştirmez. Yerel x86_64 için CTranslate2 paketi
ve bağımlılık kapanışı doğrulandı, gerçek metin ve hafıza akışı geçti. Bağımsız
güvenlik araç paketinin eksikliği yayına hazır güvenlik kanıtı olarak ayrı izlenir.

Yeni kişi hafızası, model ağırlıklarının her seferinde yeniden eğitilmesi değildir.
Temiz ses örneği, model sürümü ve kişi vektörü mevcut tenant hafızasında tutulur.
Kısa, tutarsız veya üst üste konuşma yanlış bir kalıcı profile çevrilmez; böyle bir
kişi toplantı içinde etiketlenebilir fakat hafızaya kaydedildi olarak gösterilmez.
Yeniden denemede veya eşzamanlı iki toplantıda aynı kişi için çift kayıt önlenir.

20 saniye tek seferde konuşma zorunluluğu değildir: örneğin aynı kişiden güvenle
ayrılmış 6 + 7 + 8 saniyelik temiz bölümler toplam 21 saniye eder. Tam 20 saniye
henüz yeterli değildir. Sessizlik, üst üste konuşma, kayıt boşluğu, yeniden
gönderim ve parça bağlamının tekrar işlenmesi bu toplamı artırmaz. Toplamı aşmak
tutarsız veya karışık sesi geçerli profile dönüştürmez. Yeterli kanıt birikmeyen
kişi `profile_pending` durumunda kalır; söyledikleri metinden çıkarılmaz ve sırf
kısa konuştuğu için en yakın kayıtlı kişinin adına zorlanmaz. Bu karar mevcut
tek konuşmacılı profil yükleme/tanıma API'sinin eşiklerini değiştirmez.

## Teams için korunan ayrım

Platform katılımcısı, toplantıdaki akustik konuşmacı ve kalıcı ses profili ayrı
bilgilerdir. Platform katılımcısı güvenilir biçimde biliniyorsa kısa sözü ona
bağlamak için önce 20 saniyelik biyometrik profil oluşturmak gerekmez. Yalnız
görünen addan iki kişinin aynı kişi olduğu sonucu çıkarılmaz; ortak bir oda
mikrofonu da birden fazla kişiyi taşıyabilir.

Teams'in döküm API'si zamanlı konuşmacı adları sağlayabilir, fakat bu adlar kendi
başına kalıcı ses kimliği değildir. Canlı medya SDK'sı ayrı ses tamponları
verebildiğinde aynı anda en fazla dört aktif konuşmacıyı taşır; 50 katılımcı,
50 kesintisiz ayrı kanal anlamına gelmez. Bu SDK .NET/Windows Server gerektirir;
mevcut Python/FastAPI uygulamasına bu aşamada böyle bir servis eklenmez.
Kaynak katılımcı/kanal/zaman/örtüşme/kesinti bilgilerini korumak, daha sonra
seçilecek bağlantının ses motoruyla çalışabilmesini sağlar.

Mikrofon yakalama ayrı 007 yeteneğidir; fiziksel giriş cihazının duyduğu sesi alır.
Çevrimiçi toplantıdaki uzak kişilerin sesini otomatik yakalama, toplantı platformu
bağlantısının ayrı işidir. Güncel 002 akışında yüklenen dosya tamamlanınca döküm
üretilir. 003 mevcut olarak yalnız canlı konuşmacı kimliği analizi taslağıdır;
canlı transkript bu isteğe eklenmedi.

50 kişi kalite hedefidir, kayıt kotası değildir. Konuşmacı ayrımı, kelime doğruluğu
ve kalıcı kimlik başarısı ayrı ölçülecek; mevcut tek konuşmacı test skorları bu
toplantı akışının doğruluk sonucu olarak kullanılamaz.

Kaynaklar: [Community-1 model kartı](https://huggingface.co/pyannote/speaker-diarization-community-1),
[Whisper large-v3 model kartı](https://huggingface.co/openai/whisper-large-v3).
Seçilmiş çalışma zamanı dosyaları: [CTranslate2 model kartı](https://huggingface.co/Systran/faster-whisper-large-v3/blob/edaa852ec7e145841d8ffdb056a99866b5f0a478/README.md).
Teams bilgileri için: [Graph döküm sözleşmesi](https://learn.microsoft.com/en-us/graph/api/calltranscript-get?view=graph-rest-1.0),
[ayrı ses tamponları](https://microsoftgraph.github.io/microsoft-graph-comms-samples/docs/bot_media/Microsoft.Skype.Bots.Media.AudioSocketSettings.html),
[medya SDK gereksinimleri](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/calls-and-meetings/requirements-considerations-application-hosted-media-bots).
