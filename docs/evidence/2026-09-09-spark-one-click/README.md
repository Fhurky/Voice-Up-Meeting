# Koşum raporu — 2026-09-09 · Tek tıklamayla Windows–Spark bağlantısı ve uygulama başlangıcı

1. Sonuç: Tek giriş noktası hazır; durmuş proje servislerinden gerçek başlangıç ve tekrar kullanım L2 olarak gözlendi — birim 146 başarılı / tarayıcı 0 başarılı / atlanan 1; gerçek PostgreSQL 15 başarılı; toplam 161 otomatik test başarılı; karar bekleyen: yok. Güvenlik/üretim ve L3 sahip kabulü iddia edilmez.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows PowerShell 5.1, yerel CPython 3.13, Docker Desktop ve Spark Linux ARM64.

   | Kontrol | Gözlenen sonuç |
   | --- | --- |
   | `pytest tests/test_connect_spark.py tests/test_spark_runtime_start.py` | 40 Windows koordinasyon + 41 uzak başlatma testi başarılı; Windows symlink yetkisi nedeniyle 1 atlandı. 55,07 sn. [Ham çıktı](focused-tests.txt), [JUnit](focused-tests.xml). |
   | `scripts/quality-gate.sh all` | Exit 0; 44 arka uç birim, 15 gerçek PostgreSQL, 21 ön yüz testi. Yapılandırma/bağımlılık kabulü, formatter/lint/tip, migrasyon/drift, OpenAPI/tipler, governance ve chart kontrolü geçti. Test DB oluşturulup düşürüldü; uygulama DB'sine migrasyon yapılmadı. [Ham çıktı](quality-gate.txt). |
   | Son statik kontroller | Yeni Python yardımcı ve iki test dosyasında Ruff lint/format; `git diff --check` başarılı. PowerShell gerçek yorumlayıcıda, CMD gerçek giriş noktasında çalıştırıldı. |
   | Gerçek Linux dosya sınırı | Doğru 0600 özel ayar kabulü, yanlış 0644 reddi ve model symlink reddi: 3/3 başarılı; geçici fixture temizlendi. [Kanıt](remote-posix.json). |
   | SSH-stdin uzak yardımcı | Aynı hazırlanmış imajla iki çağrı `ready`, yaklaşık birer saniye. Spark `docker.service` açılışta enabled/active. [Canlı çağrılar](remote-start-live.json), [Docker boot](docker-boot.json). |
   | Durmuş servislerden CMD başlangıcı | Yalnız VoiceUp'ın Windows nginx/frontend/backend/worker'ı, sahipli tüneli ve Spark inference/relay'i durduruldu. Proje dışı çalışma dizininden `Start-VoiceUp.cmd -NoBrowser` exit 0; 16,43 sn. [Sonuç](stopped-services-start.json), [ekran çıktısı](stopped-services-start.txt). |
   | Başlangıç sonrası gerçek ses işi | Tek denemede CUDA başarısı; job UUID Spark logunda 200. Profil aynı, diğer projeye ait iki konteynerin çalışma durumu ve başlangıç zamanı aynı; yerel inference kapalı. [Uygulama](after-recovery.json), [Spark korelasyonu](recovered-job-remote.json). |
   | Sağlıklı durumda tekrar başlangıç | Exit 0; 8,86 sn, aynı sahipli SSH PID yeniden kullanıldı. [Sonuç](repeated-start.json), [çıktı](repeated-start.txt). |
   | `scripts/security-gate.sh` | Exit 2: çevrimdışı `gitleaks` bulunamadı. Sonraki tarayıcılar çalışmadı; güvenlik kanıtı açık. [Ham çıktı](security-gate.txt). |

3. Maddeler:

   **KUSUR**

   M1 DÜZELTİLDİ: Eski başlatıcı Docker ve uzak model servislerinin zaten hazır olmasını gerektiriyordu. Yeni [koordinatör](../../../scripts/connect-spark.ps1) bu adımları tek giriş noktasında toplar; yalnız hazırlanmış imajlarla çalışır.

   M2 DÜZELTİLDİ: Uzak hazırlık kontrolünde sayısal `ready=1` artık gerçek boolean hazırlığı sayılmıyor; başarısız testten sonra düzeltildi. [Koruyan testler](../../../tests/test_spark_runtime_start.py).

   M3 DÜZELTİLDİ: Yerel Docker hazırlık isteğinin zaman aşımı, Desktop başlatma/bekleme adımını atlamıyor. Yalnız bu probe hatası yeniden deneniyor; uzak endpoint ve yanlış engine reddediliyor. [Koruyan testler](../../../tests/test_connect_spark.py).

   **TUZAK**

   M4 Spark açık ve kablo bağlı olmalı. İlk özel anahtar/adres/model/imaj/uygulama kurulumu hazırlanmış cihazlar içindir; betik yeni makineye kurulum yapmaz, cihazı elektrikten açmaz veya indirme başlatmaz.

   M5 Kablo takma olayını izleyen sürekli görev kurulmadı. Kullanıcı tek betik seçeneğini de kabul ettiği için günlük kullanımda masaüstü kısayolu veya CMD/PowerShell giriş noktası kullanılır.

   M6 Hazırlanmış Spark Compose/nginx hashleri değişirse başlangıç reddedilir. Uzak yardımcı, ayarları sessizce güncellemez; değişiklik ilgili kaynak ve kanıtla birlikte ilerletilir.

   **GÖZLEM**

   M7 Başlangıç sırası Ethernet → yerel Linux Docker → doğrulanmış uzak servisler → sahipli SSH → uygulama/web hazırlığıdır. Çift çağrı kilidi bütün akış boyunca tutulur; hata sonrası bırakılır. Wi-Fi, CPU veya yerel GPU'ya otomatik dönüş yoktur.

   M8 Başlatıcının normal kullanımı hazır URL'yi varsayılan tarayıcıda açar; doğrulama koşumları `-NoBrowser` kullandı. Türkçe UTF-8 çıktı ve proje dışından çağrı gerçek CMD koşumunda doğrulandı.

   **AÇIK**

   M9 Docker Desktop'ın gerçekten kapalı olduğu durum mevcut diğer projeyi durdurmamak için canlı denenmedi. Kapalı/başlamayan/zaman aşımı/yanlış engine dalları otomatik sınır testleriyle doğrulandı; tüm cihaz reboot'u ve fiziksel kablo çıkarma canlı koşumu yapılmadı.

   M10 Çevrimdışı güvenlik paketi eksik ve Windows symlink testi atlandı. Ayrı Linux dosya kanıtı atlamayı Windows başarısına dönüştürmez. Bu dağıtım işi kişi tanıma doğruluğu veya uzun kayıt yeteneği eklemez.

   **YAN-ETKİ**

   M11 [Start-VoiceUp.cmd](../../../Start-VoiceUp.cmd), Windows koordinatörü, uzak stdlib yardımcı ve testler eklendi. Masaüstünde `VoiceUp Spark.lnk` oluşturuldu; hedef mevcut proje CMD'si olarak geri okunup doğrulandı. Önceden aynı isimli kısayol yoktu.

   M12 Yalnız proje servisleri test için durdurulup geri açıldı; tünel yeniden kuruldu. Kilit dosyası Git dışındaki bağlantı klasöründe boş olarak kalır; işlem tamamlandığında kilit tutulmaz. Profil değişmedi; teknik tanıma işi mevcut saklama politikasına tabidir.

Kullanım ve ilk kurulum sınırları: [Spark geliştirme rehberi](../../SPARK_RUNTIME.md).
