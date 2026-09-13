# Koşum raporu — 2026-09-13 · Qwen3.5 27B ile Türkçe bağlamsal düzeltme deneyi

1. Sonuç: 59 model isteği tamamlandı; kontrollü hatalar kısmen düzeldi, gerçek veri örneklerinde toplam kelime hatası azalmadı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows, RTX 4060 Laptop 8 GB, yaklaşık 32 GB sistem belleği, mevcut Docker arka uç adaptörü ve yerel Ollama 0.33.3; `kt-vibecoding-python-web-v2`.

   Model `qwen3.5:27b`, Q4_K_M, 27.8B; kurulu dosya yaklaşık 17,4 GB.
   Digest `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.
   İstekler JSON şema, `think:false`, sıcaklık 0, seed 42, bağlam 8192,
   çıktı sınırı 512 ile yapıldı. Model indirilmedi; metin dışarı gönderilmedi.

   | Deney ve toplu kanıt | İstek | Ham → öneri kelime hatası | Ham → öneri WER | Öneri isabeti | Temiz satır bozma | Medyan / en uzun süre |
   |---|---:|---:|---:|---:|---:|---:|
   | [İlk kontrollü geliştirme](controlled-v1-aggregate.json) | 16/16 | 4 → 2 / 91 kelime | %4,40 → %2,20 | 3/4 | 1/12 | 5,63 / 47,44 sn |
   | [Örnek yönlendirmesi kaldırıldıktan sonra](controlled-v2-aggregate.json) | 16/16 | 4 → 2 / 91 kelime | %4,40 → %2,20 | 3/4 | 0/12 | 5,87 / 29,84 sn |
   | [MediaSpeech](mediaspeech-v1-aggregate.json) | 12/12 | 26 → 26 / 331 kelime | %7,85 → %7,85 | —; kabul edilen öneri yok | 0/6 | 5,91 / 22,16 sn |
   | [FLEURS](fleurs-v1-aggregate.json) | 12/12 | 10 → 10 / 201 kelime | %4,98 → %4,98 | 0/1; kelime hatasına etkisiz | 0/6 | 5,71 / 35,33 sn |
   | [Son bellek bırakma ayarı, yeniden kullanılan üç örnek](final-residency-aggregate.json) | 3/3 | 2 → 0 / 13 kelime | %15,38 → %0 | 2/2 | 0/1 | 32,80 / 35,20 sn |

   `scripts/evaluate-transcript-review.py prepare` örnekleri ilk model
   çağrısından önce sabitledi; `run` üretimdeki adaptör ve aynı değişiklik
   denetimini kullandı. Kontrollü 16 örnek geliştirme verisidir; ilk örnek
   başlangıç yönergesindeki gösterimle örtüşür. İkinci koşum aynı örneklerin
   yeniden ölçümüdür; üç örneklik son koşum bağımsız doğruluk testi değildir.

   Her gerçek veri setinde kaynak SHA-256 sırasından altı temiz ve altı
   hatalı kayıt seçildi. Farklı klipler komşu konuşma gibi birleştirilmedi;
   bunlar önceki ASR çıktılarıdır, ses modeli yeniden çalıştırılmadı.
   Referanslar veri setinin sağladığı metinlerdir; bu koşumda ses dinlenerek
   insan doğrulaması yapılmadı. 24 örnek 532 referans kelimede 36 hatayı
   korudu: toplam %6,77. Katmanlı küçük örneklem bütün veri setini veya
   doğal toplantı dağılımını temsil etmez.

   İlk dört deneyde `keep_alive:5m` kullanıldı. Son ayar `keep_alive:0`;
   üç örneklik akışın ilk isteği bellekteki modeli kullandı, sonraki iki
   istekte yeniden yükleme dahil 35,20 ve 32,80 saniye ölçüldü. Ara kontrolde
   Ollama `/api/ps` boş model listesi döndürdü. Bunlar aynı makinedeki
   geliştirme yükü altında alınmış gözlemlerdir, hizmet süresi garantisi değildir.

3. Maddeler:

   **KUSUR**
   M1 Başlangıç yönergesindeki yazılım örneği, hayvan bağlamındaki doğru “sürüyü” kelimesini değiştirdi; örnek kaldırıldı ve aynı temiz cümle tekrar korundu.
   M2 İkinci kontrollü koşumda “kalırdık → kaldırdık” yanında gereksiz “rolden → rolde” önerildi; genel otomatik değiştirme kabul edilmedi, geçici öneri görünümü kullanıldı.
   M3 İlk ölçümde çift sayılı örneklerin medyanı üst orta değerdi; denetim düzeltildi, ham satırlar yeniden hesaplandı ve eski günlük bloklarına dokunmadan yeni sürümler eklendi.

   **TUZAK**
   M4 İlk geliştirme koşumunun son üç isteği sırasında denetim/biçim dosyaları değişti; ilk deney tek kaynak sürümüyle tekrarlanabilir kanıt sayılmaz, sonraki 40 isteğin kaynak karması her satırda aynıydı.
   M5 “İsabet”, tek başına uygulanan önerinin referans kelime hatasını azaltmasıdır; cümlenin toplam hatası aynı kalırken yararlı ve zararlı iki öneri birbirini dengeleyebilir.
   M6 MediaSpeech'te 2, FLEURS'ta 10 öneri korumalarca reddedildi; öneri üretmek, önerinin doğru olduğuna veya kullanılabilirliğine kanıt değildir.

   **GÖZLEM**
   M7 Son yönergeyle 24 temiz kontrollü/gerçek örneğin hiçbiri bozulmadı; örneklem küçüktür ve diğer doğru metinlerin korunacağını garanti etmez.
   M8 Orijinal metin, konuşmacılar ve ses zamanları bu çevrimdışı metin deneyinde değiştirilmedi; testler konuşmacı kimliği veya elli kişi kapasitesini yeniden ölçmez.

   **AÇIK**
   M9 İnsan doğrulanmış doğal toplantı referansı, geniş ayrılmış düzeltme testi ve Spark/Apple ölçümü yok; genel doğruluk artışı veya otomatik düzeltme güvenliği iddia edilmiyor.
   M10 Eşzamanlı ağır ses ve metin işlerinin kaynak paylaşımı bu deneyde ölçülmedi; modelin cevap sonunda belleği bırakması bu ayrı kapasite iddiasının yerine geçmez.

   **YAN-ETKİ**
   M11 Yönerge ve bellek bırakma ayarı güncellendi; beş deney ve kanıt bağlı ölçüm sürümleri `results.md` içine eklendi. Ham metinler/model sonuçları yalnız Git dışı `outputs/` altında.
