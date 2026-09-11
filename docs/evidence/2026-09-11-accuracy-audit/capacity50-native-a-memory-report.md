# Koşum raporu — 2026-09-11 · Yeni 50 kişilik A toplantısının tüm kalıcı örnekleri ve B öncesi başlangıç

1. Sonuç: Yeni A toplantısında saklanan 37 profilin tamamı kaynak ve fiziksel dosya denetimini geçti; ilk kayıt kapsamı 37/50, yani %74'tür — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Kaynak denetimi 37/37, eski galerinin değişmezlik karşılaştırması 1/1, özel iz/genel çıktı sınırı 1/1 başarılıdır; bütün 50 kişi için kusursuzluk iddia edilmez.
2. Koşulan: Çalışan yerel RTX 4060 uygulaması, `kt-vibecoding-python-web-v2`; gerçek A HTTP/worker işi sonrasında tenant ile sınırlı PostgreSQL `READ ONLY` / `REPEATABLE READ` ve gerçek saklanan dosyalar. Dar hafıza ve gizlilik sınırları L2 gözlendi; modeller bu denetimde çağrılmadı.

   | İşlem | Yöntem / kanıt | Gözlenen sonuç |
   |---|---|---|
   | Gerçek A | Aynı değişmez 2.129,659875 sn kaynak; kişi sayısı girdisi yok | 8 parça, 52 iz; 37 kayıt, 9 belirsiz, 6 bekleyen; 444,14 sn runner gözlemi |
   | B öncesi başlangıç | `capacity-native-memory-audit.py --stage before-b` | 2026-09-11 09:48:58,545456 UTC; 37 profil ve 37 örnek; o anda B yok |
   | Tüm kalıcı kaynaklar | Her örnek orijinal `clean_ranges` ile yeniden kuruldu | 37/37 WAV hash'i DB örneği/kaydı ve fiziksel dosya hash'iyle aynı; atlanan profil 0 |
   | Kaynak saflığı | [Her profilin aralık, hash ve kaynak sonucu](capacity50-native-a-memory-results.json) | 37/37 en az %99 doğru kaynak; en düşük %99,7890848; en yüksek yabancı pay %0,2109152 ve boşluk payı %0,0924446 |
   | Eski başarısız galeri | `a-native-boundaries.py`, 08:44:53 başlangıcıyla 09:52:51,419374 UTC karşılaştırması | Eski 37 profil/örnek ve gerçek dosyaların hashleri birebir aynı; karışık hata örneği korunuyor |
   | Özel iz / genel çıktı | A'nın 52 satırı tenant ile sınırlı okundu; gerçek HTTP belgesi denetlendi | 47 özel karar izi, her birinde iki model; 45 native ayrım kaydı; genel belgede özel props/iz/vektör/ses alanı yok |
   | Kelime hatası | Aynı 5.724 referans kelime | Konuşmacı permütasyonlu hata 658/5.724 = %11,4954577; yalnız atanmış hata 733/5.724 = %12,8057303 |
   | Dönüş değerlendirmesi hazırlığı | Sonuçlar okunmadan sabitlenen `return-assignment-protocol.json` ve `diagnose-native-return.py` | Tüm tanınmış satırlar dahil; 37 kayıtlı/13 kaydedilmemiş kişi; 8 sınıflandırma dalı yapay girdilerle doğrulandı, gerçek B/C sonucu bu raporda yok |

3. Maddeler:

   **KUSUR**

   M1 A kaynak eşlemesinde hâlâ bir birleşik iz, bir bölünen kaynak ve bir zayıf iz var; 13 kişi uygun kalıcı profile sahip değil. Önceki karışık kalıcı örneğin yeni hafızada tekrarlanmaması, bütün konuşmacı ayırma sorunlarının bittiği anlamına gelmez.

   **TUZAK**

   M2 %74 ilk kayıt kapsamıdır, dönüş tanıma doğruluğu değildir. Kaynak aralıkları iç sessizliği de içerir; bu oran insan etiketli konuşma saflığı veya konuşmacı ayrıştırma hata oranı değildir.
   M3 A artık gözlenmiş gerileme verisidir. 444,14 sn yükleme sonrası yoklama/raporlama dahil gözlemdir; önceki 779,156 sn eşzamanlı işlemci testlerinden etkilenmişti, yalıtılmış hızlanma kıyası yapılmaz.

   **GÖZLEM**

   M4 B öncesi özel görüntü SHA-256 `bf3395f51172344513ba31e083175b7545e5d30c53c8260d316462e9388f377a`; bütün 37 profil ayrı ayrı [sanitize edilmiş sonuçta](capacity50-native-a-memory-results.json) korunur.
   M5 Eski hatalı galerinin sonraki özel görüntü SHA-256 değeri `efc8439a12e70a159a53379c3b91b9cf67eabc8802ab1d00974dc8e5568eb8cd`; profil/model/vektör/ad/örnek/dosya karşılaştırmalarının tamamı eşit.
   M6 Dönüş tanısı protokolü SHA-256 `dd12436235acf6499696355ffc72caf69bce2354d12f2ff711d7c81053ca69f3`; kaynak eşlemesi doğrulanamayan tanınmış satırlar ayrı kalır, gizlenmez veya varsayımla yanlış sayılmaz.

   **AÇIK**

   M7 B/C sonrasındaki bütün profil/örnek/dosya değişmezliği, yanlış kişi atamaları ve kaydedilmemiş kişinin bilinen profile yanlış bağlanması ayrı terminal denetiminde ölçülecek; bu A-only rapor bunları geçmiş saymaz.
   M8 Yapay İngilizce kaynak, Türkçe doğal toplantı veya canlı Teams kalitesi için kanıt değildir; genel kalite kapısı ve donanım kapsamı ayrı raporlardadır.

   **YAN-ETKİ**

   M9 Yeni A gerçek işi ayrı galeride 37 profil oluşturdu; sonraki denetim yalnız okudu ve ignored özel görüntüler ile sanitize edilmiş kanıt yazdı. Eski 37 profil değişmedi; kaynaklar yeniden üretilmedi, kullanıcı ses/metni/vektörü bu rapora alınmadı.
