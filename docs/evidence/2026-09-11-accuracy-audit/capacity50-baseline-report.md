# Koşum raporu — 2026-09-11 · Gerçek 50 kişilik ilk toplantının metin ve kalıcı hafıza başlangıç ölçümü

1. Sonuç: İşlem tamamlandı, kalite kabulü başarısızdır; 50 kişiden 36'sı uygun kaynak eşlemesiyle kaydedildi, toplam 37 profilin biri iki kişinin sesini saklıyor — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 2; karar bekleyen: yok. Gerçek HTTP işi 1 tamamlandı; 37/37 dosya kökeni denetlendi, 36/37 profil kaynak saflığı koşulunu geçti; B/C bekletiliyor.
2. Koşulan: Yerel RTX 4060 üzerinde çalışan `kt-vibecoding-python-web-v2` uygulaması; sıradan kullanıcıyla gerçek HTTP yükleme, sekiz worker parçası, ardından yalnız ilgili tenant için PostgreSQL `READ ONLY` / `REPEATABLE READ` ve gerçek dosya denetimi. Bu rapor L2 gözlemidir; kalite geçişi veya kullanıcı kabulü değildir.

   | Ölçüm | Girdi / yöntem | Gözlenen sonuç |
   |---|---|---|
   | Değişmez A kaynağı | Tam cümleler sırayla birleştirilmiş 50 İngilizce konuşmacı; kaynak etiketleri yalnız sonradan denetimde, modele kişi sayısı verilmedi | 2.129,659875 sn; 161 cümle kaydı; 5.724 referans kelime; `auto_enroll=true` |
   | Tamamlanan işlem | `outputs/2026-09-11-accuracy-audit/run-capacity.py`; değişmez A sonucu | 8 parça, 51 konuşmacı izi; 37 kayıt, 8 belirsiz, 6 profil bekleyen |
   | İlk kayıt kapsamı | Uygun kaynak-profili eşlemesi / bütün kaynak kişiler | 36/50 = %72; yeniden katılan kişi doğruluğu değildir |
   | Kaynak eşleme hataları | 51 izin tamamı, kaynağa göre bağımsız zaman kesişimi | Eksik kaynak 0, bölünen kaynak 1, birleşik iz 2, zayıf iz 1; genel eşleme başarısız |
   | Konuşmacı permütasyonlu kelime hata oranı | `unicode-words-v1`; 50 referans ve 51 çıktı akışı; en iyi bire bir eşleme | 803/5.724 = %14,0286513; 229 değiştirme, 288 silme, 286 ekleme |
   | Yalnız atanmış metin hata oranı | Atanmamış metin kişiye eşlenemez; aynı 5.724 kelimelik payda | 886/5.724 = %15,4786862; 156 değiştirme, 366 silme, 364 ekleme |
   | Atanmamış çıktı | Bütün 5.722 çıktı kelimesi | 93 kelime = %1,6253058; 48,38 sn atanmamış metin aralığı |
   | Bütün kalıcı örnekler | [37 profilin hash, aralık ve kaynak sonuçları](capacity50-baseline-results.json) | 37/37 yeniden kurulan WAV, DB örnek/kayıt hash'i ve fiziksel dosya hash'i eşit; 36 profil en az %99,7890848 doğru kaynak |
   | Karışık kalıcı örnek | Hiçbir eşleşmeyen profil dışlanmadı | 48,9708125 sn; `ls-2196` 23,1940625 sn ve `ls-3235` 25,7767500 sn; %47,3630338 / %52,6369662, boşluk 0 |
   | Bağımsız native kaynak incelemesi | Sekiz checkpoint; 300–600 sn çekirdeği | Ayrı `SPEAKER_15` ve `SPEAKER_16`, ikisi de kullanılabilir ve 192 boyutlu vektör mevcut; native 256 boyutlu çift kosinüsü 0,5567067471 |
   | Gözlenen süre | Yükleme tamamlandıktan başlayan runner saati; istek, yoklama ve raporlama dahil | 779,156 sn; eşzamanlı işlemci testleri nedeniyle yalıtılmış model performans ölçümü değildir |
   | Başlangıç görüntüsü | 2026-09-11 08:44:53,516402 UTC | 37 profilin model/vektör/ad/örnek satırı ve fiziksel dosya hashleri sabit; B sonrası karşılaştırma yok |
   | Gerileme denetimi | `freeze-capacity-baseline.py`; eski 48 ve yeni 37 gerçek WAV | 85/85 hash ve PCM biçimi doğrulandı; 85 tekil hash, yinelenen 0; 76 saf ve 9 karışık kontrol; model çağrısı yok |

3. Maddeler:

   **KUSUR**

   M1 KRİTİK — 37. kalıcı profil iki kişiyi içeriyor; `meeting_coherence.py` ve mevcut hafıza kabul yolu bu örneği reddetmedi. Sabit [sonuç dosyası](capacity50-baseline-results.json) bütün 37 profili, başarısız profil dahil saklar; yeni model veya birleştirme düzeltmesinin bu raporda geçtiği iddia edilmez.
   M2 Aynı 300–600 sn çekirdeğinde sağlayıcı iki kişiyi ayrı native etiketledi; son kalıcı global örnek ikisini birleştirdi. Kaynak aralıkları bu etiketlerden sırasıyla 9,247375 ve 13,000375 sn destek gösterir; hata yalnız başlangıçta tek kişi üretildiği varsayımıyla açıklanamaz.

   **TUZAK**

   M3 36/50, doğru kaynakla ilk kayıt kapsamıdır; yeniden tanıma precision/recall/F1 skoru değildir. Uygun eşlemesi bulunmayan karışık profili dışlamak veya işin `succeeded` durumunu kalite başarısı saymak kusuru gizler.
   M4 Konuşmacı permütasyonlu kelime hata oranı kalıcı kimliği ölçmez; kaynak aralığı saflığı da cümle içi sessizliği içerir ve insan etiketli konuşma saflığı ya da konuşmacı ayrıştırma hata oranı değildir.
   M5 Native çift kosinüsü tarihî global kazanan skoru değildir; o kararın ikinci aday skoru ve farkı kaydedilmedi. Özel bellek isteğinin sonradan yeniden kurulması da eski HTTP günlüğü veya değişen `clean_ranges` için tarihî fingerprint kanıtı sayılmaz.
   M6 A ve 85 kontrol artık gözlenmiştir; bunlarla yönlendirilen sonraki düzeltme aynı veride kör holdout başarısı diye sunulamaz. Bu kurulan İngilizce kayıt, Türkçe, eşzamanlı konuşma veya canlı Teams kalitesini kanıtlamaz.

   **GÖZLEM**

   M7 Değişmez A sonucu SHA-256 `c04b798aef5d2c2f8983f50cd61ba1e6d8028ec3317f8f9f31e5f5a2362eb75a`; fiziksel karışık WAV SHA-256 `e7742b80c26466bca99d581f4070010d0815546c29f6037abc5e58033c8f0447`.
   M8 Birleşik kontrol manifesti `outputs/2026-09-11-accuracy-audit/capacity50/retained-controls/combined85-manifest.json`, SHA-256 `95961030ed373d55e49489a9e697ee6580c0865be2ce21e3e37e62b8feaff123`; eski 48 ve yeni 37 kontrol seçimsiz ve tekrar hesabıyla korunuyor.
   M9 [Önceki ayrıntılı kaynak denetimi](../2026-09-11-meeting-quality/capacity50-memory-audit-report.md) ve bu raporun [sanitize edilmiş sonuçları](capacity50-baseline-results.json) başlangıç, kaynak protokolü, native inceleme ve yeniden kurulmuş istek manifestlerinin SHA-256 değerlerini içerir.

   **AÇIK**

   M10 B ve C karışık kalıcı profil nedeniyle koşulmadı; yeniden katılan kişiler, yeni kişi yanlış kabulü ve bu corpus üzerindeki toplantılar arası değişmezlik henüz ölçülmedi. Başlangıç görüntüsü hazır olsa da önce/sonra geçişi iddia edilmez.
   M11 Kalıcı karışımı reddeden düzeltmenin gerçek model karşılaştırması ayrı koordineli koşudadır; 85 dosyayı doğrulamak 85 model vakasının geçtiği anlamına gelmez. Bu rapor yeni birim, tarayıcı veya tam kalite kapısı koşusu içermez.

   **YAN-ETKİ**

   M12 İlk HTTP işi 37 gerçek profil ve örnek oluşturdu; bütün baseline kayıtları ve hata kanıtları korunuyor. Sonraki denetim yalnız okudu; uygulama verisi, GPU veya hizmetler değiştirilmedi; ignored WAV/özel istek/manifestler ve bu sanitize edilmiş rapor üretildi, ham vektör/ses/metin veya kimlik bilgisi Git raporuna alınmadı.
