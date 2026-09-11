# Koşum raporu — 2026-09-11 · Uygulanan doğruluk düzeltmeleri ve gerçek toplantı ölçümleri

1. Sonuç: Decision 19–24 düzeltmeleri çalışan yerel uygulamada doğrulandı; elli kişide kusursuza yakın doğruluk hedefi karşılanmadı — birim/entegrasyon 2.035 başarılı / bu değişikliklerde tarayıcı 0 başarılı / atlanan 1; karar bekleyen: yok. Gerçek GPU/HTTP davranışı için ulaşılan kanıt L2'dir; temsilî kullanıcı verisiyle L3 kabulü yoktur.
2. Koşulan: Sabit `kt-vibecoding-python-web-v2`; Windows istemci, Linux/Python 3.13 FastAPI ve PostgreSQL 17, yerel RTX 4060. Model ailesi ve eşikler korunarak aynı kaynakların önce/sonra karşılaştırması, yeni boş galeriler, gerçek servis yeniden başlatması, kaynak/dosya denetimi ve otomatik kapılar çalıştırıldı.

   | Uygulanan değişiklik | Amaç ve kanıt |
   |---|---|
   | Kaynak ağırlıklı ses merkezi | Parçalardan biriken vektörlerin normalize edilmeden önceki büyüklüğünü ve gerçek katkı süresini ayrı korur; eksik vektör ve yinelenen bağlam ağırlık eklemez. [Merkez hesabı](resultant-report.md) |
   | Bağımsız farklı kişi kanıtı | Aynı kaynak parçasında iki modelin desteklediği farklı seslerin tek toplantı grubuna veya kalıcı profile bağlanmasını engeller; tam aday sıralaması ve belirsizlik korunur. [Uygulama ve testler](native-exclusions-report.md) |
   | İkinci karışık ses kontrolü | Saklanacak aynı PCM örneğini ayrı WeSpeaker256 ve ECAPA192 uzaylarında denetler; herhangi bir veto saklanabilir çıktıyı kaldırır. 76 temiz örnek izin aldı, 9 bilinen karışık örnek reddedildi. [85 gerçek GPU kontrolü](dual-coherence-report.md) |
   | İstek boyunca GPU'da model tutma | Aynı modelin her küçük pencere için tekrar taşınmasını kaldırır; 56 eşlenmiş GPU kontrolünde 2.979 vektör birebir aynı kaldı. Kontrol aşaması 155,64→24,98 saniye; bütün toplantı hızlanması olarak sunulmaz. [Süre ve bellek](residency-report.md) |
   | Özel karar izi | İki modelin sınırlı skor/karar gerekçelerini aynı tenant ve transaction sınırında kaydeder; genel API'ye kimlik, ses, vektör veya özel iz belgesi eklemez. [Hafıza izi](memory-trace-report.md) |
   | Referanslı metin ve veri araçları | Eksik, fazla ve kişisi belirsiz sözleri paydada tutan kişi eşlemeli kelime hata ölçümü; değişmez, bölüm ayrımlı değerlendirme kaynakları. [Ölçüm rehberi](../../MEETING_ACCURACY.md), [testler](metrics-report.md), [bağımsız inceleme](independent-review-report.md) |

   Uygulanan ayrım kontrolü yalnız kullanılabilir bağımsız kanıt varsa kısıt koyar;
   bütün native etiketleri farklı kişi varsaymaz. Yeni kişi kaydı modeli yeniden
   eğitmez: kaynakla doğrulanmış kısa ses örneğini ve ayrı model temsillerini saklar.
   Modeller Community-1 konuşmacı ayrımı, WeSpeaker256 toplantı temsili,
   SpeechBrain ECAPA192 kimlik denetimi ve Whisper large-v3 metin çıkarımıdır.

   | Elli kişilik kayıt | Önceki A | Düzeltilmiş A | B dönüş | C dönüş |
   |---|---:|---:|---:|---:|
   | Katılımcı / bulunan toplantı grubu | 50 / 51 | 50 / 52 | 50 / 52 | 50 / 52 |
   | Kalıcı galeri | 37; bir karışık örnek | 37; hepsi denetimden geçti | Aynı 37 | Aynı 37 |
   | Katı kaynak eşlemesiyle doğru kişi | 36/50 | 37/50 | 35/50; kayıtlılarda 35/37 | 35/50; kayıtlılarda 35/37 |
   | Kişi eşlemeli kelime hatası (cpWER) | 803/5.724 = %14,03 | 658/5.724 = %11,50 | 462/5.716 = %8,08 | 713/5.741 = %12,42 |
   | Herhangi bir kişiye atanmamış normalize kelime | 93 | 93 | 69 | 54 |

   A karşılaştırmasında sekiz tam model çıktısı, bütün vektörler ve 343 zamanlı
   metin satırı birebir aynıydı; 145 daha az kelime hatası sonraki konuşmacı
   gruplamasından kaynaklanır. B/C, aynı 37 profilin korunduğu farklı kaynaklardır;
   bunlar çalıştırılmamış eski B/C ile önce/sonra iyileşmesi olarak sunulmaz.
   Kaynaklar yaklaşık 35–36 dakikalık, İngilizce sesli kitap cümlelerinden
   oluşturulmuş kayıtlardır. Kişi sayısı modele ipucu olarak verilmedi.
   [Eski A](capacity50-baseline-report.md), [yeni A](capacity50-native-a-memory-report.md),
   [B](capacity50-native-b-memory-report.md), [C](capacity50-native-c-memory-report.md),
   [değişmeyen model çıktısı karşılaştırması](provider-comparison-report.md).

   Kişi benzerliğini toplantı gruplamasından ayırmak için 190 sabit klip gerçek
   model yolunda birer kez işlendi. Elli kayıt adayı ve aynı 140 sorguyla kurulan
   dört kontrollü galerinin birleşik kararları şöyledir:

   | Planlanan / gerçek galeri | Doğru bilinen sorgu | Precision | Planlı recall | F1 |
   |---|---:|---:|---:|---:|
   | 5 / 5 | 10/10 | %100 | %100 | %100 |
   | 10 / 10 | 20/20 | %100 | %100 | %100 |
   | 20 / 20 | 40/40 | %100 | %100 | %100 |
   | 50 / 49 | 95/100 | %100 | %95 | %97,44 |

   Elli hedefinde bir kayıt çoklu grup nedeniyle kontrollü galeriye alınmadı;
   onun iki sorgusu beş kaçırmanın içinde kaldı. Hiç kaydedilmemiş 20 kişinin
   40 sorgusundan 30'u bilinmeyen, 10'u belirsiz kaldı; yanlış kabul 0'dı.
   Bunlar gözlenen bu kümenin skorlarıdır. Galeri kabulü gözetimli ve tek global
   grup şartlıdır; gerçek toplantının otomatik yeni kişi kaydıyla aynı deney
   değildir. Aynı 140 sorgunun dört tekrarı 560 bağımsız örnek sayılmaz;
   galeriyle bilinen/yabancı oranı da değişir. Kaynakların türetilmiş A/B/C
   sonuçları önceden görüldüğünden yeni kör test iddiası yoktur.
   [Tam sayımlar ve model ayrımı](nested-gallery-report.md),
   [bağımsız ölçüm incelemesi](nested-protocol-review-report.md).

   | Ayrı doğrulama | Gözlenen sonuç |
   |---|---|
   | Tam profil kapısı | `scripts/quality-gate.sh all`: 595 backend + 89 ön yüz, çıkış 0; gerçek ayrı PostgreSQL, migrasyon/drift, biçim/lint/tip, OpenAPI/tip sözleşmeleri ve chart/yönetişim geçti. [Rapor](full-gate-report.md) |
   | Kök araştırma/kurulum paketi | 1.116 başarılı, ilk koşumda 15 atlama; sonradan 13 gerçek Docker ve 1 Linux dosya sınırı geçti. Toplam 1.130 farklı başarı, 1 kapanmamış Windows atlaması. [Kök paket](root-suite-report.md), [ek koşumlar](additional-runtime-tests-report.md) |
   | Çıkarım paketi | Son üretim kaynağında 221 başarılı. Dar regresyonlar ve tekrarlar 2.035 toplamına yeniden eklenmedi. [Model sınırları](dual-coherence-report.md) |
   | Gerçek küçük toplantı/hafıza | A/B/D/C: galeri 5→5→5→6; aynı isim ve kimlikler, kısa altıncı kişi beklemede, yeterli konuşunca tek yeni profil, dört idempotent tamamlama ve gerçek backend/worker yeniden başlatması. Altı saklanan örneğin tamamı kaynak/dosya denetiminden geçti. [Canlı akış](five-person-live-report.md) |
   | Dağıtılmış model | Kaynakları doğrulanmış `d14a4e65159a…` imajına gerçek özel HTTP isteğinde eski karışık örnek `inconsistent_audio`; saklanabilir vektör/hash/aralık yok. [İmaj ve HTTP kanıtı](deployed-critical-memory-results.json) |
   | Son çalışma ortamı | Son deneyden sonra aynı imaj mevcut Local wrapper ile geri açıldı; özel model ve genel veritabanı hazır olma uçları HTTP 200. [Geri açılma kanıtı](runtime-restoration-report.md) |
   | Güvenlik kapısı | `scripts/security-gate.sh`, çıkış 2: `required offline security tool is unavailable: gitleaks`; tarama geçişi yok. [Eksik kanıt](security-report.md) |
   | Son belge denetimi | Yerel bağlantılar, sabit rapor yapısı, kayıtlı sayımlar, çalışma ağacı ve 22 kaynak hashinin bağımsız son kontrolü. [Rapor](final-verification-report.md) |

3. Maddeler:

   **KUSUR**

   M1 Yanlış normalize merkez birikimi, bağımsız farklı seslerin yeniden birleşmesi ve bilinen karışık örneğin hafızaya kabulü koruyucu testlerle düzeltildi; ilgili kaynak/test bağları yukarıdaki uygulama raporlarındadır.
   M2 Elli kişinin tamamı güvenilir biçimde kaydedilip geri tanınmadı: A'da 37/50 profil, B ve C'de katı kaynak eşlemesiyle 35/50 doğru kişi. Bu başarısızlıklar paydadan çıkarılmadı.
   M3 C'de temiz bir profile bağlı toplantı grubu, başka bir kaynağın 22,33 saniyesini de içeriyor; bütün 37 profil ve örnek değişmese de metnin bir kısmı yanlış kişinin adı altında görünebilir. [Kök neden ve reddedilen adaylar](capacity50-c-merge-forensics-report.md).

   **TUZAK**

   M4 Saklanan örnek saflığı, toplantıdaki bütün konuşmaların doğru kişiye bağlandığı anlamına gelmez. B/C'nin doğrulanamayan atamaları korunur; yalnız doğrulanabilen alt kümeye bakarak %100 precision iddiası yapılmaz.
   M5 Kaynak cümlesi aralıkları iç sessizlikleri de kapsar; bunlardan hesaplanan saflık ve süreler elle etiketlenmiş konuşmacı hata oranı değildir. cpWER ise isimler arasında en iyi eşlemeyi kullanır, kalıcı kişi kimliğinin doğruluğunu tek başına ölçmez.
   M6 ASR pencereleme ve iki daha sıkı birleşme adayı uygulanmadı; bütün kaydı tek seferde kümelemek de C'nin kelime hatasını 713→774 artırdı ve reddedildi. [ASR](asr-report.md), [birleşme kuralları](capacity50-c-merge-forensics-report.md), [bütün-kayıt deneyi](whole-recording-community-report.md).

   **GÖZLEM**

   M7 Bütün 37 yeni örneğin kaynak sahipliği en az %99,789'dur; özgün kaynaklardan yeniden oluşturulan WAV, kayıtlı hash ve gerçek dosya eşleşir. B/C boyunca isim, vektör, örnek kayıtları ve dosyalar birebir aynı kaldı; eski başarısız galeri de değişmedi.
   M8 Aynı modeller, mevcut 0,55 eşleşme / 0,45 yeni kişi / 0,10 fark sınırları ve tam referanslar korundu; model, veri veya kişi sayısı seçilerek başarısız sonuç gizlenmedi. Kosinüs eşikleri olasılık veya doğruluk yüzdesi değildir.

   **AÇIK**

   M9 Doğal Türkçe toplantı, farklı mikrofonlar, gerçek örtüşen ses ve temsilî kullanıcı kabulü ölçülmedi; İngilizce kontrollü kaynaklar bunların yerine geçmez. Yerel RTX kanıtı native Spark/Apple toplantı desteğini veya 100–200 kişide doğruluğu kanıtlamaz.
   M10 Güvenlik taraması araç/malzeme eksiği nedeniyle tamamlanmadı; bir Windows symlink testi yerel yetki nedeniyle kapatılamadı. İki/dört saatlik tam model koşusu ve bu değişikliklerin yeni tarayıcı koşusu yok; önceki tarayıcı kanıtı ayrı teslimdedir.

   **YAN-ETKİ**

   M11 Mevcut uygulamaya Decision 19–24 kaynakları ve testleri eklendi, yerel çıkarım imajı mevcut çevrimdışı wrapper ile yenilendi; değerlendirme için ayrı sıradan kullanıcı/tenant, yüklemeler ve profiller oluşturuldu. Gerçek kullanıcı kayıtları veya eski başarısız galeri silinmedi.
   M12 Sesler, referans metinleri, vektörler ve özel durum belgeleri ignore edilen yerel dizinlerde kaldı; bu raporlar sayılar, dosya bağları ve hashler içerir. Bu inceleme için commit veya push yapılmadı.
