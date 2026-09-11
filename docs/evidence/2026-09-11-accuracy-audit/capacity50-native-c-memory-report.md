# Koşum raporu — 2026-09-11 · C dönüş toplantısında değişmeyen hafıza ve süren konuşmacı karışımı

1. Sonuç: C sonrasında 37 profil/örnek/dosya değişmedi; ancak tanınan bir iz 22,325625 sn başka kişiye ait konuşma içeriyor ve genel kalite kabulü sağlanmadı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Değişmezlik 1/1, saklanan kaynak denetimi 37/37 başarılı; bütün 52 satır ve tanınan 37 satır denetlendi.
2. Koşulan: Yerel çalışan `kt-vibecoding-python-web-v2` uygulamasının gerçek C HTTP/worker işi; `capacity-native-memory-audit.py --stage after-c`, `diagnose-native-return.py --case c-return` ve `recognized-source-duration.py --case c-return`. PostgreSQL 10:08:22,378165 UTC'de tenant ile sınırlı `READ ONLY` / `REPEATABLE READ` okundu; ardından yalnız dosyalar işlendi, model çağrılmadı.

   | Ölçüm | Payda / yöntem | Gözlenen sonuç |
   |---|---|---|
   | Gerçek C | 50 kaynak kişi; 37 kayıtlı, 13 kaydedilmemiş | 8/8 parça; 52 iz; 37 tanınan, 8 belirsiz, 7 bekleyen; 438,422 sn runner gözlemi |
   | Değişmeyen sıkı dönüş ölçütü | Bütün kişiler ve A'da kayıtlı kişiler | 35/50 = %70; 35/37 = %94,5946 |
   | Bütün tanınmış satırlar | B görülmeden dondurulan sınıflandırma; ek %99 kaynak koşulu | 28 doğrulanmış doğru, 9 kaynak eşlemesi doğrulanamayan; ayrıca 15 çekinme/profilsiz satır; hiçbiri dışlanmadı |
   | Doğrulanamayan 9 satır | Kaynak belirsizliği yanlış kişi varsayımı değildir | 7 doğru A sahibine eşlenen iz %99 altında; 2 sıkı eşlemede uygun değil: bölünen `ls-6209` ve karışık `ls-1898` |
   | Önemli karışım | `ls-1898` profiliyle tanınan 53,6625 sn iz | 31,336875 sn `ls-1898` + 22,325625 sn kaydedilmemiş `ls-1841`; yaklaşık %58,39 baskın kaynak, diğer kişinin konuşması bilinen ad altında |
   | Bütün profil hashleri | Aynı A başlangıcı → C sonrası | 37 profil/model/vektör/ad, 37 örnek ve fiziksel dosyalar birebir aynı; [her profilin önce/sonra karşılaştırması](capacity50-native-c-memory-results.json) |
   | Saklanan örnekler | A kaynağından yeniden kurulan fiziksel WAV | 37/37 saflık ve hash denetimi tekrar başarılı; sorgu sesiyle örnekler değişmedi |
   | Kelime hata oranı | Eksiksiz 5.741 referans kelime | Konuşmacı permütasyonlu 713/5.741 = %12,4194391; yalnız atanmış 716/5.741 = %12,4716948; 54/5.738 çıktı kelimesi atanmamış |
   | Ek kaynak-süre incelemesi | B sonrası tanımlanıp C öncesi dondurulan tarif; tanınan 37 satırın tamamı | 1.368,2184375 sn atanmış süre; aynı sahip 1.332,8426875 sn = %97,4144662; yabancı kişi 34,663375 sn; boşluk 0,712375 sn |
   | Yabancı kaynak ve örtüşme | [Tam kaynak-süre sonuçları](capacity50-native-c-source-duration-results.json) | Yabancı kayıtlı kişi 8,304625 sn; kaydedilmemiş kişi 26,3587500 sn; çıktı satırları arasında 6.750 çerçeve = 0,421875 sn tekrar atanmış |
   | Baskın kaynak | Eşik kullanmadan bütün tanınan satırlar | 37/37 tek baskın kaynak A profil sahibiyle aynı; bu durum azınlık konuşmalarının yanlış atamasını ortadan kaldırmaz ve %100 precision değildir |

3. Maddeler:

   **KUSUR**

   M1 ÖNEMLİ — Kaydedilmemiş `ls-1841` kaynağının 22,325625 sn konuşması `ls-1898` adıyla tanınan global izde bulunuyor. Kalıcı örnek saf kalmasına rağmen konuşmacılı çıktı karışıyor; bu gözlem genel kalite başarısı diye kapatılamaz.
   M2 Tanınan tüm izlerde toplam 34,663375 sn yabancı kaynak var; C kaynak eşlemesinde iki bölünme, bir birleşik iz ve iki zayıf iz kalıyor. Çıktıdaki 0,421875 sn çift atama süre hesabında ayrıca görünür tutuldu.

   **TUZAK**

   M3 35/50 sıkı dönüş ölçütü ile 28/50 ek saflık sertifikası farklıdır; 9 doğrulanamayan satır ne çıkarıldı ne varsayımla yanlış sayıldı. Doğrulanmış yanlış kişi sınıfının sıfır olması belirsiz satırları kapsayan %100 precision iddiası değildir.
   M4 Kaynak-süre hesabı tam cümle aralıklarını ve iç sessizliği içerir; insan etiketli konuşma doğruluğu, DER/JER veya tekil geçen süre değildir. Payda bütün tanınan satırlara atanmış çerçevelerdir; tekrarlar ayrıca raporlandı.

   **GÖZLEM**

   M5 C sonrası görüntü SHA-256 `ef554136a0fdc2ab9993d14d195a8679f4f4d055b69f12b85f046b687b453767`; B ve C ayrı ayrı aynı A başlangıcıyla karşılaştırıldı ve bütün 37 profil değişmedi.
   M6 Sabit tüm-atama sonucu SHA-256 `df411acfaaaa01fbab0024eb4f59c3a21cfd054d6d35db3c647917a5cf9b9fee`; aynı kaynak-süre tarifinin C sonucu SHA-256 `c5d4fa50786788adf7ae110819b0acc9fe53bc2afa79212d8a81ff420dd2b2ec`.

   **AÇIK**

   M7 Büyük karışımın ilk birleşme adımı ve model/uygulama kararları ayrıca incelenecek; bu rapor yeni bir düzeltmenin geçtiğini iddia etmez. Gerçek Türkçe toplantı ve daha geniş kişi düzeyi kalitesi ayrıca ölçülmelidir.

   **YAN-ETKİ**

   M8 Denetim kaynakları, modelleri veya veritabanını değiştirmedi; özel son görüntü ve sanitize edilmiş bütün satır/profil raporları üretildi. Başarısız ve belirsiz sonuçlar korundu; ses, metin, ham vektör veya gerçek profil kimliği Git raporuna alınmadı.
