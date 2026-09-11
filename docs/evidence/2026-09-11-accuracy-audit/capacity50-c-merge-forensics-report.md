# Koşum raporu — 2026-09-11 · C kaydındaki yanlış birleşmenin gerçek ara çıktılarla incelenmesi

1. Sonuç: Yanlış birleşme yeniden üretildi; iki genel önlem de regresyonları nedeniyle reddedildi — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Gerçek C eşleştirme denetimi 1/1, aday karşılaştırması 7 + 7 vaka tamamlandı; bunlar ürün kalite geçişi değildir.
2. Koşulan: `kt-vibecoding-python-web-v2`, yerel Python 3.13.14; gerçek `MeetingChunkPersistence`, imza denetimli bellek deposu ve her parçada float32 dönüşü. C'nin tenant ile sınırlı `READ ONLY` / `REPEATABLE READ` veritabanı dışa aktarımı sonrasında bütün işlemler dosyalardan çalıştı; SQL yazısı ve model/GPU çağrısı sıfır.

   | İnceleme | Gözlenen sonuç |
   |---|---|
   | Gerçek C'nin tekrar üretimi | 8 checkpoint, 52 son satır ve her satırın kaynak aralıkları tam eşit; iki vektör ailesinde en yüksek L2 farkı 2,3898054×10⁻⁸, denetim sınırı 2×10⁻⁷ |
   | İlk yerel karışım, core index 2 | `SPEAKER_10`: 1,350000 sn `ls-1898` + 10,597500 sn `ls-1841`; `inconsistent_audio`, bağımsız 192 vektörü yok; yeni global ordinal 47 oluşuyor |
   | Index 4, önceki yerel etiket | `SPEAKER_11`: 0,033750 sn `ls-1898` + 11,508750 sn `ls-1841`; usable192 mevcut; global47 henüz 192 taşımıyor; 256 birinci 0,92258376, ikinci 0,43572864, fark 0,48685512 |
   | Index 4, büyük çapraz birleşme | `SPEAKER_13`: 11,761875 sn `ls-1898` + 0,016875 sn `ls-1841`; `inconsistent_audio`, 192 yok; global47 ile 256 birinci 0,61056727, ikinci 0,38163984, fark 0,22892743; doğrudan akustik eşleşiyor |
   | Bağımsız çift kanıtının eksikliği | Aynı core'da `SPEAKER_11` usable olsa da `SPEAKER_13` 192 taşımıyor; Decision 23 iki kullanılabilir bağımsız vektör gerektirdiğinden bu çift için ayrı kişi kanıtı oluşmuyor |
   | Index 6 | `SPEAKER_06` kullanılabilir 192 ile geliyor; önerilen global ile 192 benzerliği 0,47469592, mevcut 0,45 eşiğinin altında değil; ardından `SPEAKER_07` ile gerçek yerel çift 0,40978663 olduğundan ayrı ordinal51 oluşuyor |
   | Son tanınmış karışık satır | Ordinal47: 31,336875 sn `ls-1898` + 22,325625 sn `ls-1841`; ayrı ve saf kalıcı örnek denetimi bu konuşmacılı çıktı kusurunu ortadan kaldırmıyor |

   | Sabit aday / tanısal iz sayısı | Eski A | Eski B | Eski C | Eski D | 3.600 sn | 50A | Gerçek 50C |
   |---|---:|---:|---:|---:|---:|---:|---:|
   | Mevcut üretim kodunun replay'i | 5 | 5 | 6 | 6 | 5 | 52 | 52 |
   | Aday 1: kullanılabilir native192/global192 <0,45 engeli | 5 | 5 | 6 | 6 | 20 | 53 | 52 |
   | Aday 2: yalnız `inconsistent_audio` primary merge engeli | 11 | 5 | 8 | 6 | 24 | 93 | 91 |

   Aday 1 tam 256 sıralamasını korudu, bağımsız olarak ayrışan mevcut kimlikleri engelledi ve aynı engeli kaynak bağlamına uyguladı; daha zayıf ikinci adayı seçmedi. Aday 2 yalnız `inconsistent_audio` durumunda doğrudan akustik birleştirmeyi kapattı; benzersiz, örtüşmeyen aynı-kaynak bağlamı kuralını aynen korudu. Diğer kısa veya eksik 192 durumları değiştirilmedi. Her tarif sonuçlar görülmeden kendi protokolü ve kaynak hashleriyle donduruldu; eşik aranmadı.

3. Maddeler:

   **KUSUR**

   M1 C'de açıkça başarısız bağımsız ses doğrulamasından sonra 256 üzerinden yapılan global eşleştirme iki kişinin konuşmasını birleştiriyor; ilk büyük çapraz adım ve önceki yerel karışım [sayısal sonuçta](capacity50-c-merge-forensics-results.json) korunuyor. Üretim düzeltmesi henüz yok.
   M2 Aday 1 C'nin bütün yerel/global haritasını değiştirmedi; uzun kaydı 5→20 parçaya böldü. Aday reddedildi, üretime uygulanmadı.
   M3 Aday 2 kritik kişileri ayırsa da C'de baskın kaynağı birden fazla izde bulunan kişi sayısını 1→23, %90 altı kaynak paylı izleri 1→6 artırdı; eski 5 kişilik A5→11 ve uzun kayıt5→24. Aday reddedildi.

   **TUZAK**

   M4 Aday 2'de kritik yeni izler yaklaşık %99,2729 `ls-1898` ve %95,7447 `ls-1841` içeriyor; tek kusurun iyileşmesi genel kabul değildir. Yerel grubun kendi içindeki karışım çözülmüş sayılmadı.
   M5 İlk gözlemci NumPy float32 değerini JSON'a yazamadı; yalnız skaler dönüştürme düzeltildi, ilk protokol korundu. İkinci adayın ilk yükleyicisi iç içe metin bölme işaretinde durdu; son çağrıyı ayıran düzeltme protokol dondurulmadan yapıldı.
   M6 Kaynak payı tam cümle aralıklarını ve iç sessizliği içerir; DER/JER değildir. Bu rapordaki baskın-kaynak bölünmesi ve %90 tanısı, uygulamanın sabit sıkı eşleme ölçütünden farklıdır; uzun kaydın bu helper'da kaynak saflığı referansı yoktur.

   **GÖZLEM**

   M7 Gerçek C'nin hash bağlı checkpoint ve satır eşleşmesi, gözlenen zaman anındaki sıralamaların üretim kararlarını tekrar ürettiğini destekler. Diğer altı vaka mevcut kaynakla karşılaştırmalı replay'dir; burada ayrıca PostgreSQL kabulü veya yeni HTTP koşumu iddia edilmez.
   M8 [C hafıza raporundaki](capacity50-native-c-memory-report.md) tüm 37 profil/örnek/fiziksel dosyanın A→B→C değişmezliği korunuyor; bu araştırma onları değiştirmedi. Tam ara sonuçlar, aday kaynakları ve protokol hashleri sayısal raporda kayıtlıdır.

   **AÇIK**

   M9 Yanlış birleşmeyi ve gereksiz bölünmeyi birlikte azaltan bir yöntem henüz doğrulanmadı. İkinci aday eski A/uzun kayıtta zaten başarısız olduğundan yeni 50B checkpoint aktarımı ve ek model koşumu yapılmadı.

   **YAN-ETKİ**

   M10 Yalnız ignored araştırma dosyaları ile bu sanitize rapor ve sayısal eki üretildi; üretim kodu, veritabanı, kaynak sesler, referanslar ve modeller değişmedi. Git kanıtında ses, metin, UUID veya ham vektör yoktur.
