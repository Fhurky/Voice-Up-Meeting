# Koşum raporu — 2026-09-11 · Gerçek 50 kişilik A toplantısının bütün kalıcı ses örnekleri

1. Sonuç: Kalıcı hafıza denetimi başarısızdır; 37 profilin 36'sı kaynak doğrulamasını geçti, biri iki kişinin sesini saklıyor — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 1; karar bekleyen: yok. 37 profilin tamamı incelendi; B toplantısı koordinatör tarafından durduruldu.
2. Koşulan: Yerel çalışan uygulama, sabit profil `kt-vibecoding-python-web-v2`; tamamlanan gerçek A işi sonrasında PostgreSQL üzerinde tenant ile sınırlı `READ ONLY` / `REPEATABLE READ` sorguları ve gerçek saklanan dosyaların SHA-256 denetimi.

   | İşlem | Kanıt | Gözlenen sonuç |
   |---|---|---|
   | B öncesi başlangıç | `outputs/2026-09-11-accuracy-audit/capacity-memory-audit.py --stage before-b` | 2026-09-11 08:44:53,516402 UTC; 37 profil, 37 örnek; B henüz yok |
   | Tam kaynak denetimi | [Sanitize edilmiş 37 profil sonucu](capacity50-memory-before-b-results.json) | 37/37 yeniden kurulan WAV hash'i, DB örnek/kayıt hash'i ve gerçek saklanan dosya hash'i eşit |
   | Doğru kaynak saflığı | Aynı 37 profilin hepsi; uygun kaynak eşlemesi bulunmayan profil de dahil | 36 profil en az %99,7890848 doğru kaynak; 1 profil %52,6369662 / %47,3630338 karışım |
   | Tam özel istek yeniden kurma | `outputs/2026-09-11-accuracy-audit/extract-capacity-mixed.py` | Gerçek `prepare_context_sample`, mevcut kaynak bağlamları ve değişmeyen 256 boyutlu hedef/rakip vektörleriyle özel istek üretildi; çıkarım çalıştırılmadı |
   | Gerileme kontrolleri | `outputs/2026-09-11-accuracy-audit/prepare-capacity-retained-controls.py` | 36 temiz + 1 karışık kalıcı WAV; 37 tekil hash; 51 yerel konuşmacı izinin kaynak bileşimi ayrıca kaydedildi |

3. Maddeler:

   **KUSUR**

   M1 KRİTİK — Hafızaya alınan bir örnek, `ls-2196` kaynağından 23,1940625 sn ve `ls-3235` kaynağından 25,7767500 sn içeriyor; toplam 48,9708125 sn, boşluk 0. Mevcut `meeting_coherence.py` / hafıza kabul akışı bu gerçek karışımı reddetmedi; düzeltme bekleyen değişmez girdi `mixed-regression/manifest.json` içinde korunuyor.

   **TUZAK**

   M2 Yalnız kaynak eşlemesi uygun 36 profilin raporlanması, 37. karışık profili gizler. Bu rapor tüm 37 kalıcı profili ve tüm 51 yerel konuşmacı izini kapsar; 36 uygun eşleme, bütün hafızanın başarılı olduğu anlamına gelmez.
   M3 Bu 50 kişilik kaynak artık gözlenmiştir. Hata veya kontrol sonuçları yeni ayara yön verdikten sonra aynı corpus yeniden kör holdout diye adlandırılamaz; 36 temiz kontrol, 50 kişide yeniden ölçülmüş başarı değildir.
   M4 Kaynak aralıklarından gelen saflık, cümle içi sessizliği de o kaynağa sayar; insan etiketli konuşma saflığı veya DER değildir. Yeniden kurulan özel istek tarihsel HTTP günlüğü sayılmaz; sonradan değişen `clean_ranges` nedeniyle eski fingerprint iddia edilmez.

   **GÖZLEM**

   M5 Karışık örneğin gerçek saklanan WAV SHA-256 değeri `e7742b80c26466bca99d581f4070010d0815546c29f6037abc5e58033c8f0447`; profil kimliği hash'i `05d6b70ea728cb6fa5c858f2ef45c1aa0ed060daef271f15e0fdbf585c0ef139`.
   M6 B öncesi özel başlangıç görüntüsü SHA-256: `0abdce8bb6415600dfe4e226e646906f0d1c095fac4d2bd11e0bac43a540e49a`. Model/örnek/ad hashleri ile fiziksel dosya hashleri kaydedildi; henüz bir sonraki toplantıyla karşılaştırılmadı.
   M7 Tam 37 kontrol manifesti SHA-256: `940ae17b71627f8c44efdcdc784f2609d1900349f0b120dbdad4224c0790f9a2`; karışık örneğin özel istek ve kaynak etiketleri manifesti SHA-256: `71d5d213a3026e0be7b346b672f63b6d36c199698747bbeb5b3fb5aa630bd7a1`.

   **AÇIK**

   M8 B gerçek koşusu ve önce/sonra değişmezlik karşılaştırması yapılmadı; koordinatör karışık kalıcı örnek nedeniyle B'yi bekletiyor. Başlangıç görüntüsü hazırdır; bu durum bir değişmezlik geçişi olarak raporlanamaz.
   M9 Yeni 37 kontrolün model değerlendirmesi ve eski 48 kontrolle birleşik hash/tekrar denetimi ayrı koordineli araştırmada devam ediyor; bu rapor model karşılaştırmasının geçtiğini iddia etmez.

   **YAN-ETKİ**

   M10 Bütün 37 profil, 37 örnek ve hata kanıtları korundu; hiçbir uygulama/veritabanı kaydı silinmedi veya değiştirilmedi. Yalnız ignored denetleyiciler, WAV/özel istek/kontrol manifestleri ve bu sanitize edilmiş rapor üretildi; ham vektörler, sesler, metinler ve yetkilendirme başlıkları Git'e eklenmedi.
