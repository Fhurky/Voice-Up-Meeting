# Koşum raporu — 2026-09-13 · Model seçimi, yeşil öneri ve kullanıcı kaydı canlı tarayıcı akışı

1. Sonuç: TR/EN ve geniş/dar görünümde dört işlevsel varyant geçti; iki gerçek model çağrısı ve bir açık kayıt gözlendi — birim 0 başarılı / tarayıcı 4 başarılı / atlanan 3; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows Brave üzerinden `127.0.0.1:8081`, çalışan FastAPI/PostgreSQL ve yerel Ollama; yalnız açıkça adlandırılmış sentetik test toplantısı.

   | Varyant / kontrol | Gözlenen sonuç |
   |---|---|
   | TR, geniş görünüm | Üç kurulu model listelendi; 9B seçimi hesaplama başlatmadı. 27B açık kontrolü bir öneri üretti; değişen kelime yeşil ve altı çizili göründü. |
   | Açık kayıt ve yenileme | Kaydetme sürüm 1 oluşturdu; panel kapandı, ana satır yeşil gösterildi. Sayfa yenilendiğinde aynı kayıt geri geldi. Orijinal/Düzeltilmiş geçişi özgün metni korudu. |
   | EN, geniş görünüm | Kaydedilmiş sürüm İngilizce etiketlerle göründü. 12B açık kontrolü hedef satır yerine komşu satır için öneri döndürdü; öneri ve tam model yanıtı görünür, kaydetme kullanılamazdı. |
   | EN, dar görünüm | Seçilen model, eşlenemeyen öneri ve ham cevap okunabilir DOM'da kaldı; belge genişliği ve kaydırma genişliği 469 CSS piksel, yatay taşma yok. |
   | TR, dar görünüm | Aynı öneri Türkçe açıklamayla görünür; panel kapanışı ve Enter ile özgün sürüme dönüş geçti. Kayıtlı değişiklik rengi `rgb(33, 120, 99)`, alt çizgi gözlendi. |
   | Görsel / konsol | Normal 1901 CSS piksel görünümde öneri ve kayıt sonrası iki ekran görüntüsü incelendi; konsolda hata/uyarı yok. Dar görüntü yakalama 5000 ms araç zaman aşımına uğradı. |

   Dört varyant dört ayrı kayıt değildir. Yalnız TR geniş akış bir sürüm kaydetti;
   EN ve dar kontroller aynı kayıt üzerinde çalıştı. Atlanan üç kanıt: kalıcı
   headless senaryolar 10 ve 11'in doğrudan yürütümü, dar ekran görsel yakalaması.
   Bu senaryoların akışları canlı CUA ile çalıştırıldı; script yürütümü olarak sayılmadı.

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**
   M1 Erişilebilirlik ağacı basılı sürüm düğmelerini checkbox olarak gösterdi; ilk Playwright checkbox seçicisi eşleşmedi, DOM'daki gerçek button rolüyle doğrulandı. Uygulama hatası değildi.
   M2 Yeşil işaret model önerisidir; doğruluk onayı değildir. Eşlenemeyen öneri de gösterilir, ancak kaynakta yeri uydurulmaz ve kaydedilemez.

   **GÖZLEM**
   M3 Özgün metin, zamanlar ve konuşmacı sonucu korundu; model seçimi tek başına üretim başlatmadı. Kaydedilen sürüm yeniden açıldı ve özgün görünüm klavyeyle seçildi.
   M4 İki gerçek model yanıtı yalnız arayüz/kalıcılık doğrulamasıdır; yeni doğruluk örnekleri olarak [dört örnekli model kıyasına](model-report.md) eklenmedi.

   **AÇIK**
   M5 Dar ekran DOM/etkileşim kontrolleri geçti fakat ekran görüntüsü aracı zaman aşımına uğradı; dar görsel doğrulama tamamlanmış sayılmaz. Kalıcı headless scriptler doğrudan çalıştırılmadı.
   M6 Gerçek ses kaydı, ASR, mikrofon, Apple/Spark ve kullanıcı kabulü bu yeni koşumun parçası değildir; sentetik metin satırları yalnız bu akışı sınadı.

   **YAN-ETKİ**
   M7 Ayrı admin test toplantısında bir düzeltme sürümü kaydedildi. HTTP deneyiyle birlikte toplam iki test toplantısı ve iki sürüm oluştu; mevcut kullanıcı toplantıları değiştirilmedi.
   M8 Geçici ekran boyutu geri alındı, dil Türkçe bırakıldı, test oturumu kapatıldı ve geçici tarayıcı sekmesi kapatıldı. Test toplantıları açık sentetik başlıklarıyla yerelde tutuldu.
