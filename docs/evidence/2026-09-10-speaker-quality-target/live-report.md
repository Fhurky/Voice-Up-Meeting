# Koşum raporu — 2026-09-10 · 51. profilin gerçek Spark çıkarımıyla kaydı ve iki dilde profil ekranları.

1. Sonuç: İncelenen davranışlarda L2 gözlendi — birim 0 başarılı / tarayıcı 6 başarılı / atlanan 0; ayrıca gerçek HTTP/Spark kayıt akışı 1 başarılı; karar bekleyen: yok.
2. Koşulan: `http://127.0.0.1:8081` ortak SPA/API adresi; gerçek tarayıcıdaki normal giriş formu ve dört konuşmacı izni olan, `super_admin` olmayan mevcut izole test kullanıcısı. Backend/worker/frontend mevcut `scripts/stack.sh restart backend worker frontend` komutuyla yeniden başlatıldı.

   | Akış | Gözlenen kabul noktası |
   | --- | --- |
   | HTTP/Spark | 50 profil → WAV yükleme 201 → kayıt işi 202 → `succeeded/enrolled`, `cuda:0` → toplam 51; aynı anahtar aynı işi döndürdü, eski 50 profil ve tarihsel başarısız iş değişmedi. |
   | Türkçe 1 | Konuşmacılar ekranında `Toplam profil: 51`; ad alanına değer yazılabildi ve ses dosyası alanı açıktı. |
   | Türkçe 2 | `Örnek ekle` hedef kişiyi gösterdi; dosya alanı ve `Vazgeç` açıktı. |
   | Türkçe 3 | Eski terminal iş yeni kayıt başlatılabileceğini Türkçe açıkladı; mevcut kotanın dolu olduğunu söylemedi. |
   | İngilizce 1 | `Total profiles: 51`; ad alanına değer yazılabildi ve dosya alanı açıktı. |
   | İngilizce 2 | `Add sample` hedef kişiyi gösterdi; dosya alanı ve `Cancel` açıktı. |
   | İngilizce 3 | Eski terminal işin açıklaması `You can now start a new enrollment.` içeriyordu. |

   Giriş, menü bağlantıları, alan düzenleme, örnek eklemeyi açıp iptal etme,
   dil değiştirme, geçmiş iş bağlantısı ve çıkış gerçek erişilebilirlik
   referanslarıyla yürütüldü; token enjekte edilmedi. Dosya seçilmediği için
   gönderme düğmesinin kapalı kalması beklenen davranıştır. Tarayıcıdan profil
   veya örnek gönderilmedi; gerçek kayıt ayrı HTTP akışında üretildi.

   [Anonim HTTP sonucu](live-api.json), [konsol ve kabul özeti](browser-summary.json),
   [anonim ağ özeti](network-summary.json). İş sonucu mevcut
   `speechbrain/spkrec-ecapa-voxceleb` modelini ve
   `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286` sürümünü bildirdi.

3. Maddeler:

   **KUSUR**
   M1 İlk ad-hoc HTTP kontrolü `error_code` yerine sözleşmedeki `error.code` okunması gerektiği için `KeyError` ile durdu; yükleme/iş oluşturma başlamamıştı. Düzeltilen kontrol tam akışta geçti; ürün kusuru değildi.
   **TUZAK**
   M2 İlk 50 profil sentetik, 51. profil tekrarlanmış kamuya açık ses parçasından gerçek vektördür; bu akış 51 gerçek kişinin tanınma doğruluğunu veya gecikme hedefini ölçmez.
   M3 Konsol hata/uyarı listesi boştu. Zaman penceresinin Nginx özetinde iki istemci iptali 499 bulunur; bütün ağ istekleri başarılı diye raporlanmaz, uygulama ekranlarının son yüklemesi başarılıdır.
   **GÖZLEM**
   M4 `max_profiles` gerçek API yanıtında yoktu. Profil başına 20 örnek bilgisi ve tarihsel `profile_limit` sonucu korunur. Kalıcı tarayıcı senaryosu aynı beklentilere güncellendi.
   **AÇIK**
   M5 Kabul edilmiş çevrimdışı Playwright paketi yok; kalıcı senaryo komutu çalışmadı. 50 gerçek kayıtlı kişi, Türkçe toplantılar ve yeni model karşılaştırması bu geçişte ölçülmedi.
   **YAN-ETKİ**
   M6 Önceden oluşturulmuş izole test tenantına bir ses kaydı, iş ve profil eklendi; silme yapılmadı. Özel kimlikler yalnız git dışındaki `outputs/speaker-quality-target` altında tutuldu; tarayıcı oturumu kapatıldı.
   M7 Başlangıçta durmuş olan mevcut Spark SSH tüneli `scripts/spark-tunnel.ps1 -Action Start` ile açıldı; hazır GPU servisi kullanıldı, yeni model indirilmedi.
