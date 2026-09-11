# Koşum raporu — 2026-09-11 · Uzun C kaydında tek global Community kümelemesi

1. Sonuç: Bütün-kayıt deneyi kaynak karışmasını azalttı fakat kişi bölünmesini ve metin-atama hatasını artırdığı için sabit kabul ölçütlerini karşılamadı; uygulamaya alınmadı — birim 0 başarılı / gerçek GPU denemesi 1 başarılı / CPU karşılaştırması 1 başarılı / aday kabulü 0 başarılı, 1 başarısız / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; mevcut sabit `d14a4e65…` Linux görüntüsünde 2.152,875 saniyelik C kaydı bir kez işlendi. Aynı Community1 ağırlıkları ve `community-vbx-fa015-v1` tarifi kullanıldı; iki minibatch boyutu 1, model girdisi yalnız tam mono/16 kHz waveform ve örnekleme hızıydı. Kişi sayısı, referans etiketleri ve metin modele verilmedi; ağ, ASR yeniden çalıştırması ve veritabanı yazımı sıfırdır.

   | Ölçüm | Mevcut 8 parça + global eşleme | Tek bütün kayıt |
   |---|---:|---:|
   | Gözlenen bütün gruplar | 52 | 55 |
   | Birden fazla grubun baskın kaynağı olan kişiler | 1 | 4 |
   | Hiçbir grupta baskın olmayan kaynak kişiler | 0 | 0 |
   | Baskın kaynak payı %90 altında olan gruplar | 1 | 0 |
   | Bütün gruplardaki toplam azınlık-kaynak süresi | 43,632 s | 19,1838125 s |
   | En düşük baskın kaynak payı | %58,3962 | %93,7748 |
   | Birleşik permütasyonlu sözcük hatası (cpWER) | 713 / 5.741 = %12,4194 | 774 / 5.741 = %13,4820 |
   | Atanmamış metni kişiye eşlemeyen hata sayısı | 716 | 774 |
   | Son normalize sözcük / atanmamış sözcük | 5.738 / 54 | 5.737 / 38 |

   Önce gerçek sekiz sağlayıcı checkpoint'inin 5.944 ham sözcüğü sabitlendi; mevcut `stitch_words` ve çekirdek sahipliği 5.752 gözlem üretti. Eski eşlemeyle yayımlanmış 352 satırın zaman/metin/konuşmacı/örtüşme/belirsizlik alanları birebir yeniden üretildi. Adaya aynı ham ve sahip olunan sözcükler, mevcut `align_words` gruplaması ve `src/voiceup/meeting_metrics.py` uygulandı; referansın tamamı korundu.

   Model çağrısı 86,230 saniye, gerçek Docker denemesi 97,063 saniye, CPU karşılaştırması 5,968 saniye sürdü; iki komutun gerçek çıkışı 0, zaman aşımı yoktu. Ölçülen süreç RSS tepe değeri 2.893.942.784 bayt, PyTorch CUDA tahsis tepe değeri 124.396.032 bayt, rezervi 161.480.704 bayttı. RAM ile RAM+swap sınırı ayrı ayrı 8 GiB, RSS duruşu 7,5 GiB ve süre sınırı 1.800 saniyeydi.

   [Makine özeti](whole-recording-community-results.json), eski/yeni 107 grubun tamamını tutarlı anonim kaynak etiketleriyle, kritik kaynak katkılarını, altı sabit karşılaştırma koşulunu ve kanıt/kod/model karmalarını içerir. Donmuş protokol SHA-256 `65af2794090ac3a783d305db7f5cfc88df872c2a2189d6605fbc364913d5be73`; özel çıktı dizini `outputs/2026-09-11-accuracy-audit/whole-recording-community-v1/` olarak korundu.
3. Maddeler:
   **KUSUR**
   M1 Aday, daha fazla kişiyi ayrı baskın gruplara böldü ve tam referans üzerinden cpWER hatasını 61 artırdı; altı önceden sabitlenmiş koşulun üçü başarısızdır. Deney çalıştı ancak aday reddedildi; üretim kümeleme veya eşikleri değiştirilmedi.
   **TUZAK**
   M2 Tablodaki 1→4, birden çok grubun baskın kaynağı olan kişi sayısıdır; önceki tam-toplantı raporunun farklı eşiklerle ölçülen `source_mapping_split=2` alanı değildir. Bu iki bölünme tanımı birbirinin yerine kullanılamaz.
   M3 43,632→19,1838125 saniye, 52/55 grubun tamamındaki kaynak-aralığı azınlık katkılarıdır; yalnız tanınmış profillere ait yanlış atama süresi veya kimlik hata oranı değildir. Referans dışı zaman paydanın dışında, konuşma içi sessizlik kaynak aralığının içindedir.
   M4 Bütün-kayıt yürütmesi ve batch32→batch1 birlikte değişti; sonuç yalnız global kümeleme işleminin nedensel etkisi olarak ayrılamaz. Aynı ASR gözlemleri, farklı konuşma desteği nedeniyle son metinde bir sözcük farkı oluşturdu; ASR modeli iyileşmesi iddiası yoktur.
   **GÖZLEM**
   M5 Önceki kritik grup 31,336875 saniye bir kaynak ve 22,325625 saniye diğer kaynağı birleştiriyordu. Aday ağır birleşmeyi azalttı; ilk kaynak iki baskın gruba bölündü, 1,38375 ve 1,08 saniyelik karşı-kaynak katkıları dahil kenar karışmaları kaldı; bütün katkılar makine özetindedir.
   M6 Eksik baskın kaynak sayısı artmadı ve %90 altı grup kalmadı; buna rağmen tek genel başarı skoru ile olumsuz bölünme/metin etkisi gizlenmedi. Hiçbir grup sonuçtan çıkarılmadı, kaynak değiştirilmedi veya ikinci deneme yapılmadı.
   M7 Kurulu kod gerçekten 2.144 iç pencerenin vektörlerini tek VBx çağrısında kümeleyebildi; 8 GiB sınırında bu kaynak için uygulanabilirlik gözlendi. Bu süre ASR, profil kalitesi, kayıt, HTTP ve veritabanını içermez; tüm uygulama gecikmesi değildir.
   **AÇIK**
   M8 Bu çevrimdışı araştırma 310 saniyelik özel API veya kalıcı profil tanıma/örnek kabulü akışını çalıştırmaz. Ses örneği saflığı, kimlik F1/recall veya Türkçe toplantı doğruluğu göstermez; yeni yöntem uygulamaya eklenmedi.
   M9 C kapısı başarısız olduğundan koşullu eski-beşli ve büyük A/B GPU regresyonları başlatılmadı. Kaynak bilinen bir İngilizce regresyon kaydıdır; kör değerlendirme veya genel çözüm iddiası yoktur.
   M10 CUDA sayıları yalnız PyTorch tahsisçisine aittir; sürücü ve diğer kütüphaneler dahil toplam ekran kartı belleği ölçümü değildir. Kaynak hesabı ve bu tek ölçüm, dört saatlik veya daha kalabalık kayıt garantisi vermez.
   **YAN-ETKİ**
   M11 Kök ajan, boş çıkarım servisini deney öncesi durdurup aynı imajla geri başlattı; iki koordinasyon komutunun çıkışı 0'dır. Deney yardımcıları ana servislere müdahale etmedi; üretim kaynağı, model/bağımlılık veya iş verisi değiştirilmedi, özel ham kanıtlar ve bu anonim rapor/özet eklendi.
