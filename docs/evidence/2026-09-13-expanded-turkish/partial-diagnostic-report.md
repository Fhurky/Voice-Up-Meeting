# Koşum raporu — 2026-09-13 · Sürmekte olan MediaSpeech denemesinin ilk 100 tamamlanmış klibinde betimleyici hata incelemesi

> Düzeltme kaydı: PowerShell üzerinden aktarılan geçici analiz kodunda Türkçe
> sabit sözcüklerin bir kısmı `?` karakterine dönüştü. Bu raporun sayı/söylem
> belirteci/harf işareti aday sayıları güncel kanıt değildir; özgün gövde tarihçe
> olarak korunuyor. [Unicode doğrulamalı tam v2 raporu](mediaspeech-error-analysis-v2-report.md)
> esas alınmalıdır. Dosyadan hesaplanan kelime hata toplamları, birleşik/ayrı
> yazım, kesme işareti ve sınır silmesi gözlemleri bu kusurdan etkilenmedi.

1. Sonuç: Bir kez okunan 100 tamamlanmış klipte 500 kaynak/puan eşleşmesi kontrolü başarılı; bu, 2.433 kliplik koşumun nihai sonucu değildir — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel Windows/Python CPU üzerinden `mediaspeech-optimized.private.clips` içindeki sıralı ilk 100 tamamlanmış kontrol noktası ve eşleşen manifest incelendi; GPU veya yeni çıkarım kullanılmadı. Sabit profil `kt-vibecoding-python-web-v2` korunuyor.

   | Ölçüm | Bu sınırlı alt kümede gözlenen |
   | --- | ---: |
   | İncelenen / planlı klip | 100 / 2.433 |
   | Ses süresi | 1.425,80 saniye |
   | Referans / hipotez kelime sayısı | 2.924 / 2.852 |
   | Değiştirme / silme / ekleme | 200 / 154 / 82 |
   | Toplam kelime hatası | 436 |
   | Alt küme kelime hata oranı | %14,91 |
   | Sıfır kelime hatalı / boş hipotezli klip | 1 / 0 |
   | Kelime hata oranı %50'yi aşan klip | 2 |

   Her klip için manifest ses hash'i, referans metin eşleşmesi ve mevcut
   Türkçe protokolün aynı eşit maliyet önceliğiyle yeniden hizalanmış üç hata
   sayısı doğrulandı: 5 × 100 = 500 kontrol. Model metni değiştirilmedi,
   alternatif normalizasyon uygulanmadı; hiçbir puan `results.md` içine
   eklenmedi. İncelenen kontrol noktası içeriklerinin sıralı SHA-256
   özet zinciri: `feff66eab50e89ff18be86c30c3df68f929d6e6eca857c0cf4bdc11213223d91`.
   Kaynak manifest SHA-256:
   `e5439bc09b057af136bac6d85be1a511eea646c6f942fe519f06a7d0db3929ef`.

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Bu inceleme ilk 100 tamamlanmış kliple sınırlıdır; nihai 2.433 klip puanı, güven aralığı veya bağımsız model iyileşmesi kanıtı olarak kullanılamaz. Model/ayar seçimi yapılmadı.

   M2 Sayı sözcüğü ve söylem belirteci taraması sabit sözcük listesiyle betimleyici adaylar üretir; çok anlamlı sözcükler vardır. Kategoriler kesişebilir, toplanarak ayrı hata sınıfları veya neden yüzdeleri oluşturulamaz.

   **GÖZLEM**

   M3 Referansların hiçbirinde rakam yokken 22 hipotezde rakam var. 18 klipte 23 hata bloğu rakam/yazıyla sayı temsili farkı adayı içeriyor; anlamsal eşdeğerlik doğrulanmadığından bu hatalar puandan çıkarılmadı.

   M4 12 klipte 14 hata bloğunda sözcükleri birleştirip kesme işaretini kaldırınca iki tarafta aynı harf dizisi oluşuyor; ayrıca 10 klipte 10 değiştirme yalnız kesme işareti farkı taşıyor. Bunlar ses çözümleme hatasıyla yazım sözleşmesinin katkısını ayrı incelemek için somut adaylar.

   M5 Referans başındaki 39 kelime 8 klipte, sonundaki 37 kelime 15 klipte silinmiş görünüyor. Bu 76 kelime, toplam 154 silmenin bir bölümüdür; kırpma/referans hizası veya model nedeni ses dinlenmeden belirlenemez.

   M6 Söylem belirteci adayları 18 referansta var; bu sözcükleri içeren yalnız 2 hata işlemi 2 klipte görüldü. Bu alt kümede ana açıklama oldukları iddia edilemez.

   M7 12 klipte eklemeler, değiştirme ve silmeler toplamını aşıyor. Bu betimleyici koşul, tek başına halüsinasyon tanısı değildir; kaynak referansı ve gerçek ses birlikte incelenmelidir.

   **AÇIK**

   M8 Özel ad, kurum adı veya yabancı sözcük hatası bu sınırlı otomatik taramayla güvenilir biçimde sınıflandırılmadı; referanslarda tümü büyük harfli aday bulunmaması özel ad yokluğu anlamına gelmez.

   M9 Tam koşum bittiğinde kaynak başına nihai ölçümler ve dağılımlar ayrı raporlanacak. Buradaki yazım/sayı ve klip sınırı bulguları insan ses-referans denetimine adaydır; şu anda gerçek ses dinlemesi veya referans düzeltmesi yapılmadı.

   **YAN-ETKİ**

   M10 Yalnız bu toplu, açıkça kısmi rapor eklendi. Ham metin, ses/kişi/dosya kimliği yayımlanmadı; kaynak, kontrol noktası, model, kod, veritabanı ve günlük değiştirilmedi.
