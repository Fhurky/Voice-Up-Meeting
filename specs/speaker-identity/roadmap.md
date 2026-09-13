# speaker-identity yol haritası

Her satır bağımsız bir yetenek gereksinimine bağlanır. Draft durumu uygulama kabulü değildir.

11 Eylül doğruluk incelemesinde 002'nin Decisions 19–24 düzeltmeleri yerel
uygulamaya alındı; ilk elli kişilik kayıtta kişi eşlemeli kelime hata oranı
%14,03→%11,50 oldu. Saklanan 37 örnek kaynak denetiminden geçti ve iki dönüş
kaydında değişmedi; katı kaynak eşlemesinde her dönüşte 35/50 kişi doğru tanındı.
Bu nedenle elli kişi hedefi tamamlanmış sayılmaz.
Ayrı kontrollü klip galerisinde 49/50 kayıt adayı kabul edildi; birleşik kişi
tanımada precision %100, planlı recall %95 ve F1 %97,44 ölçüldü. Bu sonuç
toplantının konuşmacı gruplamasını ve otomatik yeni kişi kaydını kapsamaz.
[Uygulama, canlı ölçümler ve açık kanıtlar](../../docs/evidence/2026-09-11-accuracy-audit/README.md).

| Order | Capability | PRD | Status |
|---:|---|---|---|
| 001 | local-speaker-pilot | [PRD](PRDs/001-local-speaker-pilot/PRD.md) | Accepted — guarded speech recovery and fresh public holdout measured; quality target and Turkish acceptance incomplete |
| 002 | long-recording-analysis | [PRD](PRDs/002-long-recording-analysis/PRD.md) | Accepted — uploaded-recording five-return/sixth-new memory verified through real local RTX API/browser and restart; native Spark/Apple, representative 50-person quality and release evidence remain incomplete |
| 003 | live-speaker-analysis | [PRD](PRDs/003-live-speaker-analysis/PRD.md) | Draft — selected after 002 identity continuity |
| 004 | spark-remote-inference | [PRD](PRDs/004-spark-remote-inference/PRD.md) | Accepted — Spark application path live; security release evidence unavailable |
| 005 | local-cpu-runtime | [PRD](PRDs/005-local-cpu-runtime/PRD.md) | Accepted — fully local MacBook CPU environment requested; implementation and device evidence tracked in tasks |
| 006 | local-admin-login | [PRD](PRDs/006-local-admin-login/PRD.md) | Accepted — local one-click login verified and published; environment evidence limits recorded |
| 007 | microphone-meeting-capture | [PRD](PRDs/007-microphone-meeting-capture/PRD.md) | Accepted — PCM16/OPFS/WAV ve ortak toplantı arayüzü uygulandı; tam profil kapısı 738 testle geçti, 11 sınırlı tarayıcı kontrolü gözlendi. Fiziksel mikrofon izni, uçtan uca cihaz kabulü ve eksik güvenlik/tarayıcı araçları [görevlerde](PRDs/007-microphone-meeting-capture/tasks.md) açık |
| 008 | modern-workspace | [PRD](PRDs/008-modern-workspace/PRD.md) | Accepted — ortak tasarım uygulandı; 691 otomatik test ve 22 TR/EN dar/geniş tarayıcı kontrolü başarılı; güvenlik taraması, paketli senaryo yürütücüsü ve kullanıcı tasarım kabulü açık |
| 009 | turkish-evaluation-ledger | [PRD](PRDs/009-turkish-evaluation-ledger/PRD.md) | Accepted — otomatik günlük, Türkçe kaynak hazırlama ve RTX/HTTP karşılaştırması doğrulandı; sayısı bilinen küçük deneyde dönüş 3/6→5/6, mikro F1 %66,67→%90,91; insan referansı, 50 kişi ve güvenlik taraması sınırları [raporda](../../docs/evidence/2026-09-13-turkish-evaluation/README.md) |
| 010 | expanded-turkish-benchmark | [PRD](PRDs/010-expanded-turkish-benchmark/PRD.md) | Accepted — 3.176 yeni Türkçe klip ve 12 yeni görüşme kesiti RTX/HTTP ile ölçüldü; MediaSpeech WER %14,12, FLEURS WER %6,50; aynı altı kişilik iki zincirde kimlik F1 %100. 1.231 otomatik test başarılı, 2 Windows atlaması ve eksik güvenlik aracı açık; 50 kişi/genelleme sınırları [raporda](../../docs/evidence/2026-09-13-expanded-turkish/README.md) |
| 011 | meeting-audio-review | [PRD](PRDs/011-meeting-audio-review/PRD.md) | Accepted — 30 saniyelik yetkili kaynak dinleme, TR/EN tek oynatıcı ve gerekçe açıklamaları tamam; 845 otomatik test, 182 gerçek HTTP işlemi ve 4 canlı oynatma varyantı başarılı. Güvenlik aracı, headless koşumu ve fiziksel ses/L3 açık; [kanıt](../../docs/evidence/2026-09-13-usability-improvement/README.md), [görevler](PRDs/011-meeting-audio-review/tasks.md) |
| 012 | contextual-transcript-review | [PRD](PRDs/012-contextual-transcript-review/PRD.md) | Accepted — kaynak değişmeden yerel Qwen3.5 27B önizlemesi; 967 otomatik test, 30 gerçek HTTP isteği, dört canlı TR/EN varyantı ve 59 eşlenmiş model isteği raporlu. Gerçek Türkçe örneklerde hata oranı azalmadı; güvenlik aracı ve diğer açık kanıtlar [raporda](../../docs/evidence/2026-09-13-contextual-transcript-review/README.md); [görevler](PRDs/012-contextual-transcript-review/tasks.md) |
| 013 | model-selection-saved-corrections | [PRD](PRDs/013-model-selection-saved-corrections/PRD.md) | Accepted — üç kurulu model seçimi, tüm önerilerin görünürlüğü ve yeşil kullanıcı kayıtları L2; 1.084 tam kapı testi, 16 HTTP isteği ve dört canlı görünüm. Güvenlik aracı/diğer açık kanıtlar [raporda](../../docs/evidence/2026-09-13-saved-transcript-corrections/README.md); [görevler](PRDs/013-model-selection-saved-corrections/tasks.md) |

9 Eylül 2026 sıralama kararı: [uzun kayıt ve canlı çalışma](../../docs/LONG_RECORDING_STRATEGY.md).
001'in gerçek kişi deneyi önce gelir; sonraki model seçimi ölçüme dayanır.

Yeni cihaz isteğiyle 004, gerçek veri deneyinin çalışma ortamını hazırlamak için öne alındı.
002/003 ve 001 gerçek kişi doğruluğu kanıtı açık kalır; donanım geçişi bunların tamamlanması değildir.

9 Eylül açık veri deneyi tamamlandı: 140 kişi/604 parça, ayrı testte 50 adaydan 29
profil ve 77/150 doğru tanıma; yeni kişinin geri dönüşü kalite nedeniyle başarısız.
[Kanıt](../../docs/evidence/2026-09-09-public-speaker-evaluation/README.md).
001'in yüksek doğruluk hedefi karşılanmadı; kısa konuşma bölgelerinin kullanımı ve
kalite retleri kalibrasyon üzerinde incelenmelidir. 002/003'e geçiş kabulü verilmedi.

Sonraki korumalı kurtarma ölçümü tamamlandı: kalibrasyon 109→111/150, aynı tarihsel
test 77→78/150 doğru; ayrı yeni temiz İngilizce grupta 40/50 profil ve 116/150 doğru.
[Yeni kanıt](../../docs/evidence/2026-09-09-speech-recovery/README.md). Eşik/model
değişmedi; ilk profil kaydındaki kalite retleri ve temsilî Türkçe doğruluk 001'de
açık kalır. Yeni grubun oranı eski daha zor grupla eşdeğer karşılaştırma değildir.

10 Eylül kullanıcı açıklaması: 50 bir profil kotası değil, yüksek doğruluk
hedeflenen katılımcı düzeyidir. 001 Decision 11 ile kota kaldırıldı; 51. profil
canlı Spark'ta oluşturuldu, 200 üzeri kayıt davranışı teknik testlerde doğrulandı.
[Kanıt](../../docs/evidence/2026-09-10-speaker-quality-target/README.md).
Model aynı kaldı; [kayıt retleri ve model karşılaştırması araştırması](../../plans/SPEAKER_QUALITY_50.md)
001'in açık doğruluk hedefini besler, yeni model seçimi veya 002/003 kabulü değildir.

10 Eylül sonraki kullanıcı talimatı: dosya yükleme veya mikrofonla kayıt sonrası
konuşmacılı transkript ve yeni kişilerin otomatik hafızaya alınması şimdi istenen
ürün akışıdır. Bu nedenle 002 kapsamı genişletilip Accepted yapıldı ve uygulama
önceliği verildi; 001 kalite kabulü hâlâ açık. Mikrofon kaydını durdurup analiz
etme 002, canlı konuşmacı kimliği 003'tür; canlı transkript kapsamı eklenmedi.
[Akış](../../docs/MEETING_WORKFLOW.md),
[uygulama planı](PRDs/002-long-recording-analysis/plan.md).

10 Eylül sonraki Teams açıklaması: kısa konuşmalar metinde korunur; aynı akustik
konuşmacıya ait ayrı temiz aralıklar biriktirilir. Otomatik toplantı profili için
toplamın 20 saniyeyi aşması gerekir; tam 20 saniye yetmez, süre kalite/tutarlılık
ve bilinmeyen kişi kararının yerine geçmez. Kaynak platform katılımcısı,
toplantı akustik kümesi ve kalıcı profil ayrı kalır; 001 API/eşikleri değişmez.
Community-1 sabit yapılandırmasına yetkili HTTP 200 erişimi doğrulandı; güvenli
çevrimdışı paket, açık yerel RTX 4060/Python 3.13 deneyi ve üretim/Spark ARM64
uyumu [002 görevlerinde](PRDs/002-long-recording-analysis/tasks.md) ayrı izlenir.
Bu karar Teams bağlantısını uygulamaz, 003'ü Accepted yapmaz veya .NET servis
eklemez; 50 kişilik yüksek doğruluk hedefinin eksik kanıtı açık kalır.

Aynı gün sekiz dosyalı model paketi doğrulandı ve mevcut uygulama değiştirilmeden
RTX 4060/Python 3.13 ile 12 çevrimdışı tanı örneği işlendi. Bilinen 11 örneğin
10'unda konuşmacı sayısı doğruydu; tek kişiyi bölme ve geçişte kişi karıştırma
bulguları nedeniyle bu deney kimlik doğruluğu veya otomatik hafıza kabulü değildir.
[Paket, cihaz ve model kanıtı](../../docs/evidence/2026-09-10-community-diarization/README.md).

Son kullanıcı kararı: "Kaydı yüklemek yeterli; tanıma ve hafızayı tamamla".
Güncel 002 teslimi yüklenen dosyadan konuşmacılı metin, elle kişi isimleri ve
kalıcı hafızadır. Beş kişi ilk toplantıda kaydolur, farklı ikinci kayıtta aynı beş
kimlik/ad geri gelir, üçüncü kayıttaki altıncı yeni kişiyle yalnız bir profil eklenir.
Katılımcı üst sınırı ve kesin konuşan sayısı isteğe bağlı ayrı girdilerdir;
global sayı parçaya zorlanmaz ve sayıyı tutturmak için sesler kör birleştirilmez.
Önceki mikrofon isteği yukarıdaki tarihsel kabulden silinmeden Accepted 007'ye
taşındı; otomatik Teams kaydı ve mikrofon UI'si bu dosya teslimini bekletmez.

11 Eylül 2026: Değişmeyen dört kaynakla yerel RTX uygulama ve tarayıcı kabulü
geçti; hafıza toplamı 5→5→5→6, geri dönen kişilerin ad/kimlikleri aynı kaldı.
Altı yeni örnek yüzde 99 kaynak saflığını geçti; ayrı B tekrarında altı mevcut
profil/örnek değişmedi. [Canlı kanıt](../../docs/evidence/2026-09-10-meeting-delivery/frozen-meeting-flow-report.md)
50 kişilik doğruluk veya native Spark/Apple toplantı çalışma zamanı kanıtı değildir.

11 Eylül sonraki kullanıcı talimatı, uygulama içinden doğrudan ses kaydetmeyi
yeniden istedi ve Accepted 007'yi etkin uygulama kapsamına aldı. `AudioWorklet`
mono PCM16 sesi en çok 16 MiB bellekle OPFS geçici diskine yazar; kullanıcı
durdurduğunda kesin WAV başlığı tamamlanıp mevcut 002 hashli dosya aktarımı ve
metin/hafıza analizi kullanılır. Yeni decoder, API veya şema gerektirmeyen bu
karar, çalışma anında metin yayını veya otomatik Teams ses yakalama eklemez.
Gerçek mikrofon ve tarayıcı kanıtı [007 görevlerinde](PRDs/007-microphone-meeting-capture/tasks.md)
tamamlanıncaya kadar geçmiş dosya testiyle karşılanmış sayılmaz.
