# Koşum raporu — 2026-09-11 · Windows'ta atlanan dosya sistemi ve özel taşıma durumlarının tamamlanması

1. Sonuç: İncelenen 15 Windows atlamasının tamamı uygun ortamda doğrulandı — Linux dosya sistemi 2 başarılı / gerçek Docker HTTP 13 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: [Tam nodeid, gerekçe ve hash kaydı](remaining-platform-coverage.json); başlangıç Windows XML'i korunmuştur. İki atlama sembolik bağlantı yetkisinden, on üç atlama açık `RUN_DOCKER_TRANSPORT=1` seçeneğinin verilmemesinden kaynaklanıyordu.

   | Koşum / ortam | Kapsam | Sonuç |
   | --- | --- | --- |
   | Salt okunur depo ve mevcut test araçlarıyla çevrimdışı Python 3.13/Linux | Model yolu sembolik bağlantısı; wheelhouse hedef/dizin/üst-dizin bağlantıları ve dış dosyayı koruma | 2 başarılı, 0 atlanan; 0,71 saniye |
   | Native Windows pytest + ayrı gerçek Linux Nginx kapsayıcıları | IPv4/çoklu-worker, hatalı veya belirsiz adres, özel ve relay HTTP sözleşmeleri | 9 başarılı, 0 atlanan; 34,94 saniye |
   | Aynı son kaynak üzerinde gerçek Linux Nginx | Local/Spark × start-local/stack; eski IP, geçersiz etkin yapılandırma, güvenli yeniden yükleme | 4 başarılı, 0 atlanan; 20,40 saniye |

3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 Windows koşumundaki 15 atlama silinmedi veya başarılıya çevrilmedi; ayrı Linux/taşıma koşumları tamamlayıcı kanıttır. Test opt-in seçeneği model veya ana uygulama testlerini kendiliğinden etkinleştirmez.
   M2 Linux model-bağlantısı kontrolü mevcut testin değişmemiş gövdesini kullanır; gerçek kullanıcı kimliği, 0600 izinleri, şablon hash'leri, dizin zinciri ve sembolik bağlantı sınanır. Yalnız mimari kabul değeri değiştirilmiştir; native ARM64 veya model çalışması iddiası yoktur.
   M3 Linux'taki model-bağlantısı testi Docker çağrısından önce reddi doğruladığı için yalnız gerçek dosya hazırlığı kurulmuştur; Compose ayrıştırma sahte bir başarıyla değiştirilmemiş, bu adım çağrılmamıştır. Süreç sınırı imza kısıtlı taklitle hiç çağrılmadı olarak doğrulanmıştır.
   **GÖZLEM**
   M4 Linux koşumu mevcut `sha256:09dbebcbdaff48b701260d8e837344aca6c5bb13cde762cf14781dc37bd08110` imajında, ağ kapalı, salt okunur kök/depo ve UID 10001 ile çalıştı; yeni paket, imaj veya model indirilmedi.
   M5 On üç taşıma durumunun tamamı son kaynakta yeniden çalıştı; dört eski-IP testi için önceki başarılı sonuç tek başına kullanılmadı. Kapsayıcılar/ağlar uygulamadan ayrıdır ve koşum sonunda kaldırıldı.
   M6 Üç JUnit dosyası, komutlar, kaynak hash'leri ve özgün atlama gerekçeleri `outputs/2026-09-10-meeting-delivery/linux-skip-coverage/` altında korundu; `kt-vibecoding-python-web-v2` yığını değişmedi.
   **AÇIK**
   M7 Bu rapor yalnız belirtilen 15 durumun tamamlayıcı kapsamıdır; tam kök test paketi ve son profil kalite kapısı ana teslim raporunda ayrı kaydedilir. Gerçek Spark cihazında yeniden hazırlama veya native toplantı modeli doğrulanmadı.
   **YAN-ETKİ**
   M8 Yalnız araştırma çıktıları, Linux için geçici gerçek dosya düzeni, inceleme sarmalayıcısı ve bu sadeleştirilmiş kanıt yazıldı; üretim kodu/test gövdesi değiştirilmedi. Ana backend, veritabanı, profil, GPU işi veya servis yeniden başlatması yapılmadı.
