# Koşum raporu — 2026-09-13 · Gerçek modelle TR/EN önizleme ekranı

1. Sonuç: Son arayüzde iki gerçek model isteğiyle dört dil/genişlik varyantı doğrulandı — birim 0 başarılı / tarayıcı 4 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: CUA üzerinden gerçek Brave tarayıcısı, Windows ve `127.0.0.1:8081`, yerel Ollama `qwen3.5:27b`; profil `kt-vibecoding-python-web-v2`.

   | Varyant / denetim | Gözlenen |
   |---|---|
   | TR geniş / dar | Gerçek CSS genişliği 1781 / 469 piksel; tek panel, tamamlanmış `unchanged` sonucu, yatay taşma yok |
   | EN geniş / dar | Aynı iki genişlik; tek panel, tamamlanmış `unchanged` sonucu, yatay taşma yok |
   | Son model çağrıları | 17:16:48–17:17:17 UTC Türkçe; İngilizce yanıt 17:18:26 UTC; her seçim için bir `/api/chat` ve bir başarılı kamu önizleme isteği |
   | Kaynak ve kapanış | Aynı metin, kişi ve zaman aralığı görünür kaldı; iki dilde kapanınca panel kaldırıldı ve odak tetikleyici düğmeye döndü |
   | Görsel kanıt | Görünüm boyutu sıfırlandıktan sonra geniş İngilizce ekranın gerçek görüntüsü incelendi; panel ve kaynak birlikte görünür |
   | Konsol / temizlik | Son hata/uyarı listesi boş; boyut geçersiz kılması sıfırlandı, Türkçe geri getirildi, test oturumu ve geçici sekme kapatıldı |

   Dört varyant dört bağımsız model çağrısı değildir: her dilin tek yanıtı iki
   genişlikte incelendi. Son doğrulama 17:16 UTC sonrasındaki kaynak satırı
   ve erişim kayıtlarıyla sınırlandı; başka kullanıcının eşzamanlı istekleri
   bu sayıya katılmadı. Mevcut test toplantısı kullanıldı, veri yüklenmedi.

3. Maddeler:

   **KUSUR**
   M1 İlk canlı İngilizce isteği 60 saniyelik kamu proxy sınırında 504 verdi; uygulama daha sonra 200 üretse de tarayıcı sonucu alamıyordu. [65 saniyelik gerçek proxy regresyonu](runtime-timeout-report.md) ve son TR/EN akışı düzeltmeyi doğruladı.
   M2 React StrictMode iptal edilen başlangıçtan fazladan model işi başlatıyordu; [kırmızı/yeşil test](frontend-strictmode-report.md) ve son iki tekil gerçek istek düzeltmeyi doğruladı.

   **TUZAK**
   M3 İlk düzeltme sonrası sayfa yenilemesi eski Vite dönüşümünü sundu; sunulan dosyada yeni ertelemenin bulunmadığı doğrulandı. Yalnız frontend yeniden başlatıldı, sunulan güncel kaynak doğrulandı ve son akış tekrarlandı.
   M4 Önceki başarısız/iptal edilen tarayıcı denemeleri ve eşzamanlı kullanıcı çalışması nedeniyle bütün oturumun toplam model çağrı sayısı tahmin edilmedi; kontrollü 59 çağrılık kalite deneyi ayrı tutuldu.

   **GÖZLEM**
   M5 Son yanıtlardan sonra Ollama `/api/ps` boş model listesi verdi. İstemci iptali başlamış sunucu hesaplamasını anında durdurma garantisi değildir.

   **AÇIK**
   M6 Gerçek model bu satırda öneri üretmedi; `suggested` ve `rejected` ekran dalları otomatik testli, bu canlı koşumda gözlenmedi. Kaynak satırları başarılı öneri üretmek için değiştirilmedi.
   M7 Dar görünümde ekran yakalama gri görüntü veya zaman aşımı verdi; DOM/erişilebilirlik ve taşma denetimleri geçti, dar görsel görüntü kanıtı yok. Geniş görüntü başarıyla incelendi.
   M8 Kalıcı `10-contextual-transcript-review.mjs` kaydedildi; headless dosya koşumu çalıştırılmadı, gerçek CUA akışı yürütüldü. Spark/Apple ve kullanıcı kabulü bu koşumun kanıtı değildir.

   **YAN-ETKİ**
   M9 Proxy yapılandırması zarif yeniden yüklendi; Vite önbelleği için frontend yeniden başlatıldı. Test kayıtları, model ve güvenlik duvarı değiştirilmedi.
