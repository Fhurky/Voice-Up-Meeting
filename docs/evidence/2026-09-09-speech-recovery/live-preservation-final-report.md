# Koşum raporu — 2026-09-09 · Son açılış sonrası kullanıcı korunum, yetki ve çalışma ortamı denetimi

1. Sonuç: Özgün profil ve diğer konteynerler korundu; normal hesabın erişim sınırları ve son hazır durumlar doğrulandı — birim 0 başarılı / tarayıcı 0 başarılı / yetki-korunum kontrolü 31 başarılı / ilk ortam kontrolü 26 başarılı, 3 başarısız / son ortam doğrulaması 4 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows üzerindeki yerel FastAPI, sınırlı yerel Docker durum sorguları ve mevcut SSH bağlantısıyla Spark durum sorguları; yalnız giriş, GET, durum okuma ve hazır uçları kullanıldı. [Son korunum ve yetki kaydı](live-preservation-final.json), [ortam anlık görüntüsü](runtime-final-readiness.json), [ek son doğrulama](runtime-final-readiness-confirmation.json).
3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Frontend'in doğrudan `Host: frontend` isteğine 403 vermesi beklenen host kısıtlamasıdır; nginx'in ilettiği `Host: 127.0.0.1` ile 200 döndü. İlk yanlış host beklentisi düzeltilirken kaynak veya yapılandırma değiştirilmedi.

   M2 İlk ek ortam probunda Loki ve Tempo için hata ayrıntısı tutulmadı; son bağımsız GET kontrolleri ikisinde de 200 `ready` döndü. İlk başarısız gözlemler korundu; nedenleri kanıtlanmadığı için tahmin edilmedi.

   M3 Yerel 4060 çıkarım konteyneri durmuş durumdadır; Docker'da kalan eski sağlık değeri çalışan bir yerel modelin durumu olarak yorumlanmaz.

   **GÖZLEM**

   M4 Özgün profilin tüm genel API yanıtı başlangıçla aynı; 1 profilin adı, örnek sayısı, model bilgileri ve zamanları korundu. Beklenen ve gerçek kanonik yanıt hashı `922a57904521848edce356cfe2a03ec31027e755f1dc9bff62fb0a370250de0a`.

   M5 VoiceUp dışındaki iki yerel konteynerin kimlikleri, çalışma durumları ve başlangıç zamanları eski görüntüyle eşleşti. Son normal okuyucu hesabı matrisi 31/31 geçti: anonim 401, eksik tenant 400, kendi tenant'ında yabancı iş 404, yabancı tenant başlığı 403.

   M6 Yerel 11 VoiceUp servisi çalışıyordu; PostgreSQL ve Redis sağlıklıydı. Genel backend/veritabanı hazır ucu, genel frontend, Grafana, Prometheus, Loki ve Tempo son kontrollerde 200 döndü; OpenTelemetry alıcı portları bağlantı kabul etti.

   M7 Spark çıkarımı sağlıklı ve relay çalışıyor; hem yerel tünel hem özel nginx yolu `ready=true`, `cuda:0`, 192 boyut ve sabit model sürümünü döndürdü. Çalışan çıkarım imajı `sha256:a743b6e101beee3d85788f082d1b32a957149fda409eec3860c681f249b7a8c5`.

   M8 Çalışma modu `spark` olarak kaldı; yerel 4060 çıkarımı `Exited (0)` idi. Tarayıcı test profilinin negatifler sonrası ayrı son denetimi [20/20 başarılıdır](browser-api-final-report.md).

   **AÇIK**

   M9 Worker için ayrı hazır ucu yoktur; çalışan süreç gözlemlendi, tamamlanan iş kanıtı ayrı koşumlarda kayıtlıdır. OpenTelemetry için sağlık uzantısı yapılandırılmadığından yalnız süreç ve iki dinleyen port doğrulandı.

   M10 Profil korunum ölçümü genel API alanlarını kapsar; özel vektörlerin veya tüm veritabanı baytlarının eşitliği iddia edilmez. Tüm durumlar son açılış sonrası anlık gözlemlerdir.

   **YAN-ETKİ**

   M11 Kaynak, veri tabanı, hesap, rol, profil, servis veya konteyner değiştirilmedi; ses yüklenmedi, model çıkarımı çağrılmadı. Ham gözlemler özel çıktı dizininde kaldı; genel kayıtlara kimlikler, parolalar, sesler veya vektörler eklenmedi.
