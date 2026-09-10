# Koşum raporu — 2026-09-10 · Temiz CPU kurulumu ve Windows RTX 4060 çalışma ortamı

1. Sonuç: Temiz CPU kurulumu, yeniden başlatmada kalıcılık ve RTX 4060 üzerinde profil kayıt/tanıma doğrulandı; kapsam için L2 canlı kanıt gözlendi — birim 218 başarılı / tarayıcı 1 başarılı / atlanan 2; karar bekleyen: yok. Güvenlik kapısı araç eksikliğiyle durdu; tam güvenlik veya fiziksel Mac kabulü iddiası yoktur.

2. Koşulan: Sabit profil `kt-vibecoding-python-web-v2`; ana ortam Windows/Docker Desktop ve RTX 4060 Laptop GPU (8 GiB), ayrı kurulum Linux x86_64 CPU. Uygulama konteynerleri Python 3.13 kullanır; ayrı motorun kurulum yardımcısı Python 3.14.7 ile çalıştı.

   | Kontrol / komut | Gözlenen sonuç | Kanıt |
   |---|---|---|
   | `python3 scripts/setup-local-cpu.py`, değiştirilmemiş GitHub kopyası | İlk deneme başarısız: bootstrap kural özeti Windows/Linux sıralamasına bağlı | [İlk deneme](setup-first.log) |
   | Aynı komut, yalnız checker düzeltmesiyle, ayrı Docker motorunda | Çıkış 0; yeni ayarlar, veritabanı, migration, uygulama imajları ve CPU modeli hazır | [Kurulum](setup-fixed.log), [kurulum kaydı](installation-receipt.json) |
   | `python -m pytest tests/test_governance_drift.py -o addopts='' -q` | Önce 4 başarılı / 2 başarısız; düzeltme sonrası 6 başarılı | [Son JUnit sonucu](governance-regression.xml), [test](../../../tests/test_governance_drift.py) |
   | `scripts/quality-gate.sh all`, ana Windows çalışma ağacı | Çıkış 0; 153 backend + 59 frontend; biçim/lint/tip, geçici PostgreSQL, migration, OpenAPI/tip, kural ve chart kontrolleri geçti | [Kapı çıktısı](quality-gate.log), [backend](quality-gate-backend.xml), [frontend](quality-gate-frontend.json) |
   | `scripts/security-gate.sh` | Çıkış 2: `required offline security tool is unavailable: gitleaks` | [Gerçek çıktı](security-gate.log) |
   | İlk yönetici, yükleme/kayıt/tanıma/bilinmeyen kişi, aynı isteği tekrar gönderme; gerçek HTTP | 11 kontrol başarılı; `device=cpu`; ayrı kayıt aynı profile bağlandı, farklı kişi profile bağlanmadı | [İlk canlı sonuçlar](cpu-live-before-restart.json) |
   | `sh scripts/stack.sh --mode cpu stop`, ardından `sh scripts/start-local-cpu.sh`, ayrı motorda | İki komut çıkış 0; 9 kontrol başarılı; profil/örnek/iş/tekrar anahtarı/ayar/model korundu; imaj kimlikleri değişmedi | [Durdurma](cpu-stop.log), [başlatma](cpu-restart.log), [kalıcılık](cpu-live-after-restart.json) |
   | `powershell.exe -NoProfile -File scripts/start-local.ps1 -Mode Local`, ana Windows ortamı | Başlatma çıkış 0; `cuda:0` üzerinde 3 iş başarılı: kayıt öncesi bilinmeyen, profil kaydı, ayrı kayıttan tanıma | [Başlatma](windows-4060-start.log), [ilk iş](windows-4060-live.json), [kayıt/tanıma](windows-4060-profile.json) |
   | Brave, `http://127.0.0.1:8082/speaker-profiles`, yeniden başlatma sonrası salt okunur gözlem | 1 dar ekran kontrolü başarılı: “Temiz CPU kurulum denemesi”, 1/20 örnek, toplam 1 profil görünür | Bu koşumun gerçek tarayıcı erişilebilirlik ağacı gözlemi; tam yükleme senaryosu sayılmaz |
   | Fiziksel Mac kurulumu; kontrollü tarayıcı yükleme akışının tamamı | 2 senaryo tamamlanmadı; nedenleri M7–M8 | Aşağıdaki açık maddeler |

   Ana uygulama **http://127.0.0.1:8081**, temiz CPU uygulaması **http://127.0.0.1:8082** adresindedir.
   [Son hazırlık kontrolünde](final-readiness.json) iki web adresi de HTTP 200 döndürdü;
   model servisleri sırasıyla `cuda:0` ve `cpu` cihazlarında hazırdı.
   İlk CPU veritabanında profil yoktu; `sh scripts/create-super-admin.sh` ile ayrı yönetici
   oluşturuldu. Giriş düğmesi mevcut yönetici hesabını kullanır. Deney, kamuya açık iki kişinin
   üç ses kaydını kullandı: 30,125 saniye kayıt, aynı kişiden ayrı 24,350 saniye sorgu ve
   başka kişiden 27,040 saniye sorgu. Dosya özetleri [fikstür kaydındadır](fixture-hashes.json).
   İşlerde gözlenen yaklaşık 2–4 saniye, sorgulama aralığını içeren tek koşum süresidir;
   kapasite veya 50 kişilik doğruluk ölçümü değildir.

   Temiz kaynak `8478335b282d17a9a4737632d5a4ced5b9964ef2` GitHub commit'inden klonlandı.
   İlk başarısız denemeden sonra yalnız `scripts/check-governance-drift.py` yamalandı.
   Modelin 7 dosyası (91.256.819 bayt) mevcut paketten kopyalanıp hash ile doğrulandı;
   hesaplar, profiller ve eski `.env` aktarılmadı. 47 CPU wheel artifact'ı hazırlandı.
   Ağ indirmesini hızlandırmak için önceden mevcut, sabit özetli temel/yardımcı imajlar
   ayrı motora cache olarak yüklendi; uygulama imajları temiz kaynaktan derlendi.
   Kurulumun 11 sabit imaj pull işlemi yine geçti. Bu, bütün indirmelerin sıfır cache ile
   yapıldığı bir ağ performans deneyi değildir; [cache kaydı](image-cache.json).

   Ayrı makineyi taklit etmek için [resmî Docker imajından](https://hub.docker.com/_/docker)
   `voiceup-fresh-install-20260910` adlı test motoru ve `voiceup_fresh_engine_20260910`
   veri alanı kullanıldı. Motor başlangıçta 0 konteyner/0 imaj içeriyordu. Ana Docker socket'i
   bağlanmadı; yalnız temiz kopya bağlandı. Test motorunun daemon'u yalnız Unix socket dinler;
   ana makineye yalnız web için loopback 8082 sunulur. Docker-in-Docker test motoru ayrıcalıklı
   çalışır; bu düzenek ürün kurulum gereksinimi değildir. Arkadaşın kendi MacBook'unda
   [normal kurulum komutları](../../MACOS_SETUP.md) yeterlidir.

   Kalite kapısı Windows Git Bash ile, `MSYS2_ARG_CONV_EXCL=/tmp;/workspace` ve
   `MSYS_NO_PATHCONV` kaldırılarak çalıştırıldı. Kapının `_test` veritabanı oluşturma,
   migration uygulama ve silme adımları geçti; uygulama veritabanına kapı migration'ı uygulanmadı.
   Ham çıktının PowerShell `NativeCommandError` sarmalları normal stderr satırlarını da içerir;
   sonuç gerçek çıkış kodu ve `KT_GATE_*` kayıtlarından okunmalıdır.

3. Maddeler:

   **KUSUR**

   M1 DÜZELTİLDİ — Windows ve POSIX Path sıralaması aynı kural dosyalarında farklı özet üretiyordu; [checker](../../../scripts/check-governance-drift.py) açık, kararlı dosya adı sırası kullanır, 6 [regresyon testi](../../../tests/test_governance_drift.py) gerçek içerik değişikliğinin reddini korur.

   M2 DÜZELTİLDİ — Spark bağlantısı kesikken ana uygulamanın model yolu kullanılamıyordu; kullanıcı tercihiyle yerel RTX 4060 moduna geçildi, gerçek kayıt/tanıma `cuda:0` üzerinde tamamlandı.

   **TUZAK**

   M3 Yerel başlatıcılar `voiceup` Docker proje adını kullanır; ikinci kopyayı aynı motorda başlatmak yalıtım sağlamaz. Bu deney bu nedenle ayrı motor kullandı.

   M4 RTX 4060 için `powershell.exe -NoProfile -File scripts/start-local.ps1 -Mode Local` kullanılır; mevcut `Start-VoiceUp.cmd` Spark başlatıcısıdır. Eski başarısız işler yeniden çalıştırılmaz; yeni iş başlatılır.

   **GÖZLEM**

   M5 Model, eşikler, API, şema, dependency pin'leri ve üretilmiş kural kilitleri değiştirilmedi; [kurulum kaydı](installation-receipt.json) kaynak özetlerini ve cihaz modlarını içerir. Ana ortamın diğer Docker projeleri korundu.

   **AÇIK**

   M6 Güvenlik kapısı Gitleaks bulunamadığından çıkış 2 ile durdu; güvenlik taramaları başarılı sayılmadı. PRD 005 T05'in güvenlik kısmı açık.

   M7 Fiziksel MacBook erişimi olmadığı için cihazda ilk kurulum/kayıt/tanıma senaryosu atlandı; PRD 005 T06 açık. Linux CPU kanıtı Mac veya kullanıcı kabulü (L3) değildir.

   M8 Kontrollü tarayıcı yükleme akışının tamamı bitmedi: ilk sekme bağlantısı koptu, ardından kullanıcı aynı uygulamayı kullanmaya başladı. Kullanıcı akışına müdahale edilmedi; kontrollü ses işlemleri gerçek HTTP üzerinden doğrulandı.

   M9 Genel bekleme/hata metnindeki GPU ifadesi CPU modunda da görünür; bu koşum arayüz metnini değiştirmedi. Cihaz kanıtı metinden değil gerçek işin `device` alanından alındı.

   M10 Bu koşum sırasında yeni başlangıç düzeltmesi ve kanıtlar henüz commit/push edilmemişti; temiz kurulum başarısı GitHub commit'i artı raporlanan yerel yamaya aittir. Yayınlama doğrulaması bu koşumun kapsamı dışındadır.

   **YAN-ETKİ**

   M11 Temiz kopya `outputs/fresh-install-2026-09-10/repository`, ayrı Docker motoru/veri alanı, kopyalanmış model ve imaj cache'i testin incelenebilmesi için korundu; 8082 uygulaması açık bırakıldı.

   M12 Ana Windows ortamı açık kullanıcı tercihiyle `local` moduna geçirildi; kamu sesinden “RTX 4060 kurulum denemesi” profili ve test işleri oluşturuldu. Ayrı CPU ortamında yeni yönetici ve “Temiz CPU kurulum denemesi” profili oluşturuldu.

   M13 Checker/test, PRD 005 gereksinim/plan/görevler, Mac rehberi ve bu kanıtlar güncellendi. Rapora `.env`, kimlik bilgileri, model veya ses dosyaları eklenmedi; tekrar anahtarı yayımlanan JSON'dan çıkarıldı.
