# Görevler — Toplantı sonunda konuşmacı birleştirme

- [x] T01 Saf kümeleme fonksiyonu ve birim testleri (Requirement 1).
- [x] T02 `reconcile`, `TrackRebuild`, worker adımı ve PostgreSQL entegrasyon testleri (Requirement 2).
- [x] T03 `meeting_reconciliation_threshold` ayar yüzeyleri (Requirement 3).
- [x] T04 Tekrar oynatma aracı, testleri ve eşik seçimi (Requirement 4).
- [x] T05 `rename` kuralı, ön yüz ve TR/EN metinleri (Requirement 6).
- [x] T06 Tam kalite kapısı (30 Ekim 2026, kısa konuşma kuralı ve 022 dahil: arka uç 931/931, ön yüz 264/264, tüm adımlar geçti).
- [ ] T07 015 protokolü `eval-ami3-*` tenant'larında: iki ses koşulu × iki rotasyon (Requirement 5).
- [ ] T08 016 listeli iki koşum `eval-ami3-array1-r{1,2}-roster` (Requirement 5).
- [x] T09 Çalışan yığında uzun toplantı uçtan uca ve sonuç ekranı tarayıcı kanıtı.
- [ ] T10 Kullanıcı kabulü: gerçek Türkçe toplantı (L3).

30 Ekim 2026 eşik kanıtı: `eval-ami2-*-r1` saklı parça sonuçlarıyla 34 toplantıda tekrar oynatma.
Dev DER (array1/headset) ve 34 toplantıda karışık 30 sn+ küme (array1):
0,40 %23,59/%19,91, 38/176; 0,45 %23,82/%19,96, 35/179; 0,50 %23,94/%19,94, 31/179;
0,55 %24,19/%20,10, 27/173; 0,60 %24,49/%20,27, 16/160; 0,65 %25,01/%20,52, 13/152;
0,70 %25,86/%20,93, 13/149. Seçilen eşik 0,60; tekrar oynatmada 16 test toplantısı %27,31/%22,17.
Bu sayılar birleştirme sonrası gerçek ölçüm değildir; kabul T07'nin ölçümüne bağlıdır.

30 Ekim 2026 ölçüm kanıtı (T07 kısmi, T08 koşulmadı): kullanıcı AMI ölçümünü durdurdu. `results.md`'de
`eval-ami3-array1-r1`, `eval-ami3-headset-r1`, `eval-ami3-array1-r2` tamamlandı; `eval-ami3-headset-r2` 11/34
toplantıda kaldı ve kaydedilmedi, listeli iki koşum başlamadı. Bu ölçümde parça analizi, ses baytları birebir
eşleşen `eval-ami2-*` parça sonuçlarından geri verildi; birleştirme ve kimlik adımları gerçek kodla çalıştı. Çalışan
akışla uzun toplantı doğrulaması T09'da açıktır.

Sonuç: DER array1 %44,57'den %26,17'ye, headset %39,49'dan %21,42'ye indi; 16 test toplantısında %27,56 ve %22,42,
ölçüt sağlandı. Tanıma array1 r1 %69,6 (önce %73,3), r2 %65,2 (önce %64,3), headset r1 %83,3 (önce %82,6).
Yanlış kabul 0/207. **Kabul ölçütü sağlanmadı:** `eval-ami3-array1-r2`'de 46 görünümde 2 yanlış kişi var (eski kodda
0/95). İkisi de `IB4002` toplantısında, 3 ve 5 saniyelik temiz konuşmalı konuşmacılarda; aynı kişilerin profilleri
`IB4001`'de %75–76 saflıkta kümelerden kaydedilmiş. Neden bu iki gözlemden ibaret bir varsayımdır, doğrulanmadı.
Bu bulgu çözülene kadar 021 tamamlanmış sayılmaz.

30 Ekim 2026 alt sınır kontrolü: `MIN_RECOGNITION_SECONDS = 10` ile yalnız uzak mikrofon rotasyon 2 koşuldu
(`eval-ami4-array1-r2`, parça analizi saklı sonuçlardan). Yanlış kişi 2/46'dan 1/46'ya indi, tanıma %65,2'den %71,7'ye
çıktı, yanlış kabul 0/63, DER %26,17 değişmedi. **Kabul ölçütü hâlâ sağlanmadı.** Kalan vaka `IB4002`'de 19 saniyelik,
%83 `MIO092` ağırlıklı konuşmacının `MIO091` profiline bağlanmasıdır; o profil `IB4001`'de %76 saflıkta kümeden
kaydedilmiştir. Süre sınırı bu vakayı çözmez; kayıt kümesinin saflığı sıradaki varsayımdır, doğrulanmadı.
Kısa konuşma kuralı önceki davranışı değiştirir: 3–10 saniye konuşan bilinen kişi artık otomatik adlandırılmaz.

30 Ekim 2026 T09 kanıtı: `TS3003b` (37 dakika) normal GPU worker'ıyla, kayıtlı sonuç kullanılmadan işlendi. Puanlanan
süre, kaçırılan konuşma, yanlış alarm ve kişi karışması saklı parça sonuçlarıyla yapılan ölçümle üç ondalığa kadar
aynı; birleştirme 1,09 saniye sürdü. Sonuç ekranı tarayıcıda sıradan rolle açıldı: metin ve 12 konuşmacı kartı
görüldü, adlandırma açık, konsol hatası yok.

30 Ekim 2026 yanlış kişi incelemesi: küme içi benzerlik karışık kümeleri ayıramıyor (345 kümede en iyi eşik 46 karışık
kümenin 12'sini yakalarken 20 temiz kümeyi kaybediyor); bu yüzden o kural eklenmedi. Tanıma puanı da ayıramıyor: kalan yanlış
eşleşmenin puanı 0,945, doğru eşleşmelerin ortancası 0,85. Profilin içindeki ses eşleşen kişinin sesidir; hata profilin
başka kişinin baskın olduğu bir kümeden açılmasıdır. Puan eşiği veya küme benzerliği kuralı bu sınıfı çözmez.

30 Ekim 2026 Türkçe toplantı gözlemi (etiketsiz, kesin ölçüm değil): 36 dakikalık, kullanıcıya göre 11 net ve 1–2 arka
plan konuşmacılı özel kayıt normal GPU akışıyla 396 saniyede işlendi. 15 konuşmacı bulundu; 13'ü en az 10 saniye,
10'u en az 30 saniye konuşuyor; ilk 11 konuşmacı konuşma süresinin %98,2'si. Birleştirme 16 konuşmacıyı 15'e indirdi,
yani bu kayıtta kopyalanma sorunu AMI'deki kadar görülmedi. 4540 kelimenin %81'i belirsiz işareti olmayan uzun satırlarda;
490 satırın 255'i bir veya iki kelimelik, belirsiz satırların çoğu bunlar. Kişi ataması doğruluğu kullanıcı kontrolü
veya etiket olmadan bilinmiyor. Ses ve metin depoya girmez.
