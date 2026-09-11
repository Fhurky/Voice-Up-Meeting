# Koşum raporu — 2026-09-11 · B dönüş toplantısının bütün atamaları ve 37 profilin değişmezliği

1. Sonuç: B sonrasında 37 profil/örnek/dosya değişmedi; tanınan 36 satırın tamamı denetlendi, kaynak kirliliği ve doğrulanamayan eşlemeler açık bırakıldı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Değişmezlik 1/1, yeniden kaynak denetimi 37/37 başarılı; tüm 52 satır ve tanınan 36 satır hesaba katıldı.
2. Koşulan: Yerel çalışan `kt-vibecoding-python-web-v2` uygulamasında gerçek B HTTP/worker işi; ardından `capacity-native-memory-audit.py --stage after-b`, sabit `diagnose-native-return.py --case b-return` ve ek `recognized-source-duration.py --case b-return`. Veritabanı yalnız ilgili tenant için `READ ONLY` / `REPEATABLE READ` okundu; bu denetim model çağırmadı.

   | Ölçüm | Payda / yöntem | Gözlenen sonuç |
   |---|---|---|
   | Gerçek B | 50 farklı kaynak kişi; A'da 37 kayıtlı, 13 kaydedilmemiş | 8/8 parça; 52 iz; 36 tanınan, 11 belirsiz, 5 bekleyen; 444,671 sn runner gözlemi |
   | İlk kayda bağlı dönüş | Değişmeyen runner'ın sıkı kaynak eşleme ölçütü | 35/50 = %70; A'da kayıtlı kişiler içinde 35/37 = %94,5946 |
   | Bütün tanınmış satırlar | Sabit sınıflandırma, %99 sahip olunan kaynak saflığı ek koşulu | 27 doğrulanmış doğru, 9 kaynak eşlemesi doğrulanamayan; doğrulanmış yanlış kişi/yeni kişiyi bilinene atama 0; 16 çekinme/profilsiz satır ayrıca dahil |
   | Doğrulanamayan 9 satır | Hiçbiri dışlanmadı veya varsayımla yanlış sayılmadı | 8 satır doğru A sahibine eşleniyor fakat kaynak saflığı %92,5769–98,9189; 1 satır bölünen kaynak nedeniyle sıkı eşlemede uygun değil |
   | Profil değişmezliği | 09:48:58 A başlangıcı → 09:58:59,649657 UTC | Bütün 37 profil/model/vektör/ad, 37 örnek ve fiziksel dosya hashleri birebir aynı; [her profilin önce/sonra hashleri](capacity50-native-b-memory-results.json) |
   | Saklanan örnek saflığı | A kaynaklarıyla yeniden fiziksel doğrulama | 37/37 yine başarılı; B sorguları galeriye örnek eklemedi |
   | Kelime hatası | 5.716 eksiksiz referans kelime | Her iki metin ölçütü 462/5.716 = %8,0825752; 91 değiştirme, 187 silme, 184 ekleme; atanmamış 69/5.713 kelime |
   | Ek kaynak-süre incelemesi | Tanınan 36 satırın tamamı; saflık eşiği veya satır dışlama yok | 1.330,0144375 sn atanmış süre: 1.316,432 sn aynı profil sahibine ait, 13,0940625 sn başka kaynağa ait, 0,488375 sn eklenmiş etiketsiz boşluk |
   | Süre dağılımı | Aynı 1.330,0144375 sn payda; [tam sonuç](capacity50-native-b-source-duration-results.json) | Doğru sahip %98,9787752; yabancı kayıtlı kişi 6,193125 sn, yabancı kaydedilmemiş kişi 6,9009375 sn; yinelenen atanmış çerçeve 0 |
   | Baskın kaynak | Eşik kullanmadan, her tanınan satırın tek baskın kaynak sahibi | 36/36 profilin A'da doğrulanmış sahibiyle aynı; bu gözlem %100 kimlik precision skoru değildir |

3. Maddeler:

   **KUSUR**

   M1 Doğru kişinin adıyla dönen bazı izler başka kişilerin kısa konuşma parçalarını içeriyor; toplam 13,0940625 sn yabancı kaynak var. Kalıcı örnekler değişmese de konuşmacılı metin/sahne doğruluğu kusursuz değildir.

   **TUZAK**

   M2 36 tanınan satır ile 35 sıkı doğru kaynak eşlemesi arasındaki fark yanlış kişi kanıtı değildir. Ek %99 kaynak koşulundaki 27 doğru/9 doğrulanamayan sınıfları da değişmeyen 35/50 ölçütünün yerine geçirilmez.
   M3 Kaynak-süre tarifi B görüldükten sonra keşif için eklendi, C görülmeden donduruldu; tam cümle kaynakları iç sessizliği de içerdiği için DER/JER veya insan etiketli konuşma hatası değildir. Tanınan bütün satırlar dahil, ilk sınıflandırmalar değişmedi.

   **GÖZLEM**

   M4 B sonrası özel görüntü SHA-256 `104cc23b56d06f3e05716f47274e3951b28cc32ea6f5ebdf674fefeb6bbaef24`; aynı A başlangıcına göre profil/örnek/fiziksel dosya karşılaştırmalarının tamamı eşit.
   M5 Sabit bütün-atama tanısı SHA-256 `96b6d7f47bb53a8d2bd9ea22a0c8b117bc8f8ac0ff4d2d0c2bbd6ea6d995010c`; kaynak-süre sonucu SHA-256 `01fa4779688559a56ee6c1d7b6b39cd925c276785b1aa66760aa7e29c6828e05`.
   M6 Ek kaynak-süre protokolü SHA-256 `2ffcc83cfd39d5b33cf864b6ab42f818bd2a541041c1f3bb3101b0f7803ec951`; yöntem kaynak aralıklarının çakışmadığını, her satırın bölüm toplamını ve bütün tanınmış satırları doğruladı.

   **AÇIK**

   M7 C ve daha geniş bağımsız kişi/gerçek toplantı sonuçları bu B raporuna dahil değildir. Kaynak belirsizliği bulunan dokuz satır yüzünden doğrulanmış yanlış sayısının sıfır olması genel %100 precision iddiası vermez.

   **YAN-ETKİ**

   M8 Denetim yalnız okudu; kaynak sesler, profil/örnekler ve sabit sınıflandırmalar değişmedi. Ignored özel başlangıç/sonuç dosyaları ile sanitize edilmiş rapor üretildi; B sonrası keşif tarifinin eklenmesi açıkça kaydedildi.
