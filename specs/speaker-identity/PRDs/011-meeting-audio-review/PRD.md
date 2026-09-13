# PRD — Toplantı metninden kaynak sesi inceleme

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [011](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`.
Kabul kaydı: Kullanıcının 13 Eylül 2026 kullanılabilirlik ve kapsamlı
iyileştirme planını uygulama talimatı, insan denetimini mümkün kılan bu dar
dilimi yetkilendirir. Model kalitesi ve kullanıcı incelemesi ayrı kanıttır.

## Amaç ve aktör

Toplantıyı okuma yetkisi olan kullanıcı, transkriptte gördüğü bir sözü ve
konuşmacı atamasını ilgili kaynak sesi dinleyerek kontrol eder. Uzun kaydın
tamamı tarayıcı belleğine alınmaz. Mevcut ad değiştirme, hafıza ve transkript
sonuçları korunur; dinleme bunları değiştiren bir işlem değildir.

## Kararlar ve değişmezler

Decision 1: Aynı origin altında `GET /meetings/{public_id}/audio-preview`
zorunlu `start_seconds` ve `end_seconds` sorgularıyla en çok 30 saniye döndürür.
Değerler sonlu, başlangıç negatif olmayan, bitiş başlangıçtan büyük ve kayıt
süresi içinde olmalıdır. Geçersiz aralık 422 `invalid_audio_range` olur.
Çıktı `audio/wav`, mono PCM16 ve kaynağın özgün 8–192 kHz örnekleme hızıdır;
üst sınır 11.520.128 bayttır. Çok kanallı kaynak eşit ağırlıkla monoya alınır.
Bu karışım temizlenmiş veya konuşmacısı ayrılmış ses diye sunulmaz.

Decision 2: JWT ve `meeting_analysis:read` zorunlu; kaynak yalnız etkin tenant
altında çözülür. Başka tenant, silinmiş veya bulunamayan toplantı 404;
mühürlenmemiş yükleme 409 `meeting_state_conflict`; saklama süresi dolmuş,
silinmiş veya okunamayan kaynak 410 `recording_unavailable` döndürür.
Süre kontrolü cleanup işinin yetişmesine bağlı değildir. Yanıt
`Cache-Control: no-store`, `X-Content-Type-Options: nosniff` taşır;
token, dosya yolu veya kullanıcı başlığı URL/yanıt/loglara yazılmaz.

Decision 3: Kaynak adaptörü yalnız istenen kare aralığını bloklarla okur.
Yol, biçim, kanal/örnekleme ve sonlu örnek sınırlarını korur; kırpılma kalitesi
dinlemeyi reddetme nedeni olmaz. Mevcut model `window()`/örnek çıkarma
kalite retleri aynen kalır. Ses temizleme, model çağrısı ve yeni kalıcı dosya yoktur.
Mühürlü format/boyut/süre/hız/kanal metadata'sı açılan kaynakla karşılaştırılır;
aynı metadata altında yerinde değiştirilmiş tüm PCM baytlarının yeniden SHA
hesabı bu kısa okuma işleminin garantisi değildir. Depo yazma sınırı mevcut
mühürlü yükleme politikasında kalır; yol ve metadata değişimleri test edilir.

Decision 4: Metin satırındaki erişilebilir dinleme düğmesi, satır başlangıcından
en çok 30 saniyelik bölümü yükler. Uzun satırda önceki/sonraki bölüm denetimleri
satır sonuna kadar ilerler; satır sınırı kayıt süresine sıkıştırılır.
Seçili kişi, kayıt içindeki başlangıç/bitiş ve bunun kaynak ses olduğu görünür.
Yerel oynatıcı seek/pause/volume denetimleri sunar; otomatik oynatma reddedilirse
kullanıcı oynatmayı başlatabilir, bu bir sunucu hatası diye gösterilmez.

Decision 5: Aynı anda tek ses bölümü tutulur. Yeni satır/bölüm, sayfa veya
toplantı değişimi, bileşenin kapanması ve çıkışta istek iptal edilir ve Blob URL
serbest bırakılır. Geç dönen yanıt yeni seçimi değiştiremez. Ortak API istemcisi
kimlik/tenant/timeout/401 davranışını koruyarak boyut ve içerik türü sınırlı
ikili yanıt okur; düz `<audio src>` ile kimlik başlığı atlanmaz.

Decision 6: Yükleniyor, yeniden dene, kaynak artık yok, izin yok, bozuk yanıt ve
dinlenebilir bölüm yok durumları TR/EN açıklanır. Süresi dolmuş kaynak için
transkript ve kişi bilgisi okunabilir kalır. Sayfalama ve yeniden adlandırma
bozulmaz; mevcut tasarım tokenları, semantik düğme/alanlar ve klavye kullanılır.
Mevcut konuşmacı `reason` kodları yalnız bilinen güvenli bir TR/EN açıklama
listesinden gösterilir; tanınmayan kod ham basılmaz. Ad değiştirme açıklaması,
gösterim adını değiştirmenin ses kimliğini/yanlış atamayı düzeltmediğini ve
bağlı profil adının diğer toplantılarda da kullanılacağını açıklar.

## Gereksinimler

Requirement 1: Yetkili, tenant kapsamlı ve boyutu sınırlı PCM16 önizleme;
WAV/FLAC, çok kanal, 8/16/48/192 kHz, kayıt başı/sonu ve kırpılmış kaynak
gerçek dosya sınırında test edilir. Eksik, değiştirilmiş/bağlı yol ve geçersiz
aralık güvenli hata üretir. Okuma işlemi profil/metin veya audit satırı yazmaz.

Requirement 2: API, ortak istemci, üretilmiş OpenAPI/tipler, TR/EN sonuç
bileşeni ve kalıcı tarayıcı senaryosu birlikte teslim edilir. Yeni rota/menü
yoktur; mevcut toplantı detayının okuma izni kullanılır.

Requirement 3: Gerçek PostgreSQL+HTTP testleri kimliksiz/izinsiz/başka tenant,
soft-delete, süre sonu ve mühürlenmemiş kaynak davranışını; frontend testleri
başarılı dinleme, uzun satır bölümü, hata, hızlı seçim/iptal ve URL temizliğini
doğrular. Kayıt tekrar okunduğunda aynı çıktı alınır; veri değişmez.

Requirement 4: Yerel ters proxy üzerinden gerçek oturum açma ve TR/EN
dar/geniş görünümde sesin yüklenmesi/oynatılabilirliği gözlenir. Normal rol
HTTP sınırı ayrıca sınanır. Tam profil ve güvenlik kapılarının gerçek sonuçları
raporlanır; eksik araç/cihaz adımı başarı sayılmaz.

## Katmanlar ve işletim

API: tipli süre girdileri, binary OpenAPI yanıtı, ortak hata zarfı ve DI.
Servis: tenant/lifecycle/süre sınırı; altyapı: mevcut opak yerel kaynak deposu.
Şema/migration N/A — yeni kayıt, tablo veya kalıcı kullanıcı verisi yok.
Model/embedding N/A — dinlemede model veya vektör hesabı yok.
Bağımlılık/ayar N/A — mevcut SoundFile, FastAPI ve tarayıcı API'leri yeterli;
30 saniye ve bayt sınırı bu sözleşmenin sabitidir.
Dağıtım mevcut servis/proxy/chart sınırını kullanır; ayrı ağ/volume gerekmez.
Önbellek N/A — hassas yanıt saklanmaz; tarayıcıdaki tek geçici Blob iptal edilir.
Gözlemlenebilirlik mevcut istek kodları/süreleri; ses, transkript ve sır loglanmaz.
Özel kaynaklar mevcut saklama ve temizleme politikasına tabidir.

## Kabul

- [x] Gerçek dosya/HTTP önizlemesi sınırlı ve tenant/izin/lifecycle korumalı.
- [x] Modelin kalite retleri değişmeden kırpılmış kaynak dinlenebilir.
- [x] TR/EN tek oynatıcı, uzun satır parçaları ve iptal/temizlik davranışı tamam.
- [x] OpenAPI ve frontend tipleri üretilmiş; dar/tam kontroller raporlanmış.
- [x] Gerçek tarayıcı akışı, kalıcı senaryo ve kullanım belgesi mevcut;
  fiziksel ses çıkışı veya kullanıcı kalite kabulü gözlenmediyse ayrı açık.

Kanıt: [görevler](tasks.md) ve [13 Eylül raporları](../../../../docs/evidence/2026-09-13-usability-improvement/README.md).
L2 işlev gözlendi; güvenlik tarayıcısı, fiziksel ses/L3 ve headless koşucu
yürütümü açık kayıtlıdır. Bu kabul modelin elli kişide kalite kabulü değildir.
