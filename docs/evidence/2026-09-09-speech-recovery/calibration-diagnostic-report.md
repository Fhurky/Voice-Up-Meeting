# Koşum raporu — 2026-09-09 · Kısa konuşma kurtarma adaylarının kalibrasyon tanısı ve anonim kanıt denetimi

1. Sonuç: Özgün parça tutarlılık korumalı aday 2 ek bilinen sorguyu doğru tanıdı, mevcut kabulleri korudu ve yeni karışık kişi kabulü üretmedi; önceki iki aday güvenlik regresyonuyla reddedildi — birim 0 başarılı / tarayıcı 0 başarılı / denetim 2749 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, mevcut Spark CUDA modeli; her adayda 302 İngilizce kalibrasyon klibi, 10 yanlış kişiye ekleme denemesi ve 20 karışık kayıt değerlendirildi. Seçilen aday, ürün kaynak kopyası bellekte çalıştırılarak 39.68 saniyede hesaplandı; bu tanı uygulama HTTP koşumu değildir.

   | Ölçüm | Mevcut yöntem | Özgün parça korumalı aday |
   | --- | ---: | ---: |
   | Kaliteli ilk kayıt / 50 | 40 | 40 |
   | Doğru bilinen kişi / 150 | 109 | 111 |
   | Bilinen kalite hatası / 150 | 20 | 18 |
   | Yanlış bilinen kişi / 150 | 0 | 0 |
   | Bilinmeyen yanlış kabul / 100 | 0 | 0 |
   | Bilinmeyen kalite hatası / 100 | 9 | 7 |
   | Aday sorgusu → mevcut profiller, kapsanan kişilerde doğru / 120 | 109 | 111 |
   | Eski sorgu → aday profilleri, doğru / 150 | 109 | 109 |
   | Yanlış kişiye ekleme reddi / 10 | 10 | 10 |
   | Sessizliksiz karışık kayıt reddi / 10 | 8 | 8 |
   | 0.4 saniye aralı karışık kayıt reddi / 10 | 10 | 10 |
   | Doğru dönen kişi / 1 | 1 | 1 |

   | Önceki reddedilen aday | İlk kayıt / 50 | Doğru bilinen / 150 | Sessizliksiz karışım kabulü / 10 | Aralı karışım kabulü / 10 |
   | --- | ---: | ---: | ---: | ---: |
   | Tüm konuşmayı paketleme | 50 | 150 | 5 | 9 |
   | Özgün parça koruması olmayan geri dönüş | 45 | 130 | 2 | 9 |

3. Maddeler:

   **KUSUR**

   M1 Mevcut yöntemin sessizliksiz 10 dönüşümlü karışımdaki 2 kabulü seçilen aday tarafından aynen korundu; bu 2 kayıt başarısız negatiftir. Tüm karışık kişi kayıtlarının reddedildiği iddia edilmez.

   M2 Önceki iki aday, 2 saniyelik farklı kişi parçalarının 0.4 saniye sessizlikle ayrıldığı 10 kaydın 9'unu kabul etti. Bu yeni regresyon nedeniyle reddedildiler; [anonim sonuçlar](rejected-candidates-summary.json), [önceden sabitlenen tanımlar](rejected-candidates-protocol.json).

   **TUZAK**

   M3 Paketlenmiş pencerelere benzer oranlarda iki ses dağıtılması kosinüs tutarlılığını yüksek tutabilir. Seçilen aday bu nedenle en az 1.5 saniyelik özgün blokları paketlemeden önce karşılaştırır; bu koruma vektörleri profil penceresi değildir.

   M4 İlk kayıt kapsamı 40/50 kaldı. Kazanım aynı 1 bilinen kişinin 2 sorgusunda ve 2 ayrı bilinmeyen kişinin 2 sorgusunda gözlendi; tüm kişilere genellenebilen büyük doğruluk artışı değildir.

   M5 Bilinmeyen 100 sorgu 20 kişiye aittir; sıfır gözlenen yanlış kabul sıfır gerçek hata oranı değildir. Kalite hataları tüm planlanan paydalarda tutuldu.

   **GÖZLEM**

   M6 Seçilen aday eşleşme 0.55, bilinmeyen 0.45, fark 0.10 ve tüm tutarlılık kontrollerinde 0.55 kullandı. Parça alt sınırı 1.5 saniye puanlamadan önce sabitlendi; [anonim protokol](calibration-diagnostic-protocol.json).

   M7 Mevcut 263 kabul ve 14 tutarsızlık reddi aynı Evidence nesnesiyle korundu; önceki 302 baseline kaydın kalite, pencere ve süre sonuçları eşleşti. 25 geri dönüş denemesinin 21'i reddedildi; [anonim özet](calibration-diagnostic-summary.json).

   M8 Puanlanan ürün kaynağı SHA256 `bf99e46d17e86ef4bff32be6124a76898ce88439b641933cf97424b9baee81ef`, biçimlendirilmiş kaynak SHA256 `50788c193e93d0c85a7b9eb07706eb286304b76a5d9b963cee5d60cda749a813`; konum bilgisi dışarıda bırakılan Python soyut sözdizim ağaçları tamamen eşit.

   M9 Özel kayıtlar ile yayımlanan sayılar, negatif sonuçlar, baseline tekrarı, korunum, kaynak eşitliği ve kimlik sızıntısı denetiminde 2749 kontrol geçti. Dosya hashları ve denetim kırılımı [denetim kaydındadır](calibration-diagnostic-audit.json).

   **AÇIK**

   M10 Bu çalışma uygulama HTTP akışı veya dağıtım kabulü değildir; yeni canlı uygulama kanıtı ayrı koşumla gösterilmelidir. Test manifesti, test sesleri ve test sonuçları bu aday seçiminde açılmadı.

   M11 Türkçe doğal konuşma, gerçek toplantı, üst üste konuşma ve uzun kayıt başarısı bu İngilizce okuma kalibrasyonundan çıkarılamaz.

   **YAN-ETKİ**

   M12 Sürümlü özel tanı yardımcıları ve sonuçları yok sayılan `outputs/quality-improvement` altında kaldı; burada yalnız anonim protokol, sayılar, kaynak hashları ve rapor yayımlandı. Konuşmacı kimlikleri, kayıt yolları, sesler, vektörler ve kimlik bilgileri yayımlanmadı.

   M13 Tanı için mevcut servis, model, veri tabanı ve kullanıcı profilleri değiştirilmedi; geçici karışımlar ve ses vektörleri yalnız bellekte tutuldu. Ürün kaynağının daha sonra dağıtımı bu raporun kanıt kapsamından ayrıdır.
