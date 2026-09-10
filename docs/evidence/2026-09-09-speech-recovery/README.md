# Koşum raporu — 2026-09-09 · Korumalı kısa konuşma kurtarma ve yeni kişi testi

1. Sonuç: Düzeltme Spark üzerinde devrede; kazanç küçük ve yüksek doğruluk hedefi karşılanmadı — birim 552 başarılı / tarayıcı 11 başarılı / atlanan 2 ortam kapısı; karar bekleyen: yok. Üç veri koşumundaki 906 işin tamamı sonlandı: 780 başarı, 126 kalite reddi. Canlı akışlar gözlendi; eksik güvenlik kanıtı ve temsilî veri nedeniyle tam ürün kabulü verilmedi.
2. Koşulan: Sabit `kt-vibecoding-python-web-v2`; Windows React/FastAPI/PostgreSQL uygulaması, Ethernet/SSH üzerinden DGX Spark GB10 CUDA çıkarımı. Ağırlıklar, 192 boyutlu vektör uzayı ve `0.55 / 0.45 / 0.10` karar eşikleri değiştirilmedi.

   | Veri grubu | Oluşturulan profil / 50 aday | Doğru / 150 bilinen sorgu | Yanlış kimlik | Bilinmeyenlerde yanlış kabul | Yeni kişinin geri dönüşü |
   | --- | ---: | ---: | ---: | ---: | --- |
   | Kalibrasyon, önceki | 40 | 109 (%72,7) | 0 | 0/100 | Başarılı |
   | Kalibrasyon, yeni sürüm | 40 | **111 (%74,0)** | 0 | 0/100 | Başarılı |
   | Aynı tarihsel test, önceki | 29 | 77 (%51,3) | 0 | 0/100 | Kalite reddi |
   | Aynı tarihsel test, yeni sürüm | 29 | **78 (%52,0)** | 0 | 0/100 | Kalite reddi |
   | Önceden kullanılmamış temiz İngilizce grup | 40 | **116 (%77,3)** | 0 | 0/100 | Başarılı |

   Önceki sayılar [tarihsel rapordan](../2026-09-09-public-speaker-evaluation/README.md), yeni sayılar [kalibrasyon](calibration-live-summary.json), [aynı testin yeniden koşumu](historical-live-summary.json) ve [yeni grup](fresh-live-summary.json) sonuçlarından gelir. Yeni grubun daha yüksek oranı kod iyileşmesi miktarı değildir; farklı kişiler ve yalnız temiz kayıtlar kullanıldı. Her satırdaki başarısız kayıtlar ve sorgular paydada tutuldu.

   | Doğrulama | Kanıt |
   | --- | --- |
   | Aday seçimi | Yalnız kalibrasyonla, puanlardan önce dondurulan protokoller. İlk iki aday karışık kişi kabulünü artırdığı için reddedildi; korumalı aday seçildi. [Tanı raporu](calibration-diagnostic-report.md), [bağımsız denetim](calibration-diagnostic-audit.json). |
   | Eski profillerle uyum | 263 eski kabul ve 14 eski tutarsızlık reddi aynen korundu. İki yönlü sorgu/profil karşılaştırmasında yeni yanlış eşleşme oluşmadı. |
   | Yeni veri hazırlığı | Resmî [OpenSLR LibriSpeech](https://www.openslr.org/12), CC BY 4.0; 6.387.309.499 bayt arşiv doğrulandı. Eski 146 kişi dışlandı; yeni 50 bilinen + 20 bilinmeyen kişi ve 302 WAV hazırlandı. [Hazırlama raporu](fresh-dataset-preparation-report.md). |
   | Çalışan Spark sürümü | Ağsız ARM64 derleme, gerçek CUDA ve imaj içi kaynak hashleri doğrulandı. Önceki imaj geri dönüş için korundu. [Dağıtım raporu](spark-deployment-report.md), [kaynak manifesti](spark-source-manifest.json). |
   | Otomatik kontroller | 96 çıkarım + 350 benzersiz referans/veri aracı + 85 backend + 21 frontend =552. [Paket raporu](automated-report.md), [envanter](test-inventory.json). |
   | Gerçek arayüz | Profil oluşturma, kurtarılan doğru/bilinmeyen ses, sayfa yenileme, yanlış örnek ekleme, sessizlik ve profil korunumu dahil 11 akış. [Tarayıcı raporu](browser-report.md), [son API doğrulaması](browser-api-final-report.md). |
   | Bağımsız metrik denetimi | 906 iş, rapor hashleri, planlanan paydalar, aynı tarihsel kayıtlar ve yeni kişi ayrıklığı için 9.000 kontrol geçti; bunlar 552 teste eklenmedi. [Denetim raporu](final-metrics-audit-report.md). |
   | Son veri ve ortam korunumu | Asıl profilin tüm API yanıtı ve diğer iki projenin kapsayıcıları korundu; normal okuyucu hesabıyla 31 kontrol geçti. Spark hazır, yerel 4060 çıkarımı kapalı. [Son rapor](live-preservation-final-report.md). |
   | Son tek komut kontrolü | PowerShell 7 ve Windows PowerShell 5.1 başlangıcı exit0. Ardından `scripts/quality-gate.sh all` yeniden exit0; tekrarlar test toplamına eklenmedi. [Başlatıcı](one-click-final.json), [son tam kapı](quality-gate-final.txt), [koşum bilgisi](quality-gate-final-result.json). |
   | Eksik kapılar | Güvenlik tarayıcıları ve kalıcı tarayıcı paketi mevcut değil; iki komut exit2. [Güvenlik](security-gate.txt), [kalıcı tarayıcı](permanent-browser.txt). |
   | Kanıt gizliliği ve bağlantılar | Özel kimlik bilgileri yerelde karşılaştırıldı; yayımlanan kaynak/sürüm kanıtları ve yerel bağlantılar incelendi. [Son gizlilik raporu](privacy-final-report.md), [dosya özeti](privacy-final-review.json). |

   Yeni grupta 150 bilinen sorgunun 116'sı doğru, 22'si bilinmeyen, ikisi belirsiz, 10'u kalite reddidir. 100 kayıtsız sorguda 94 bilinmeyen, bir belirsiz ve beş kalite reddi vardır. Kalite hataları doğru reddetme sayılmaz. Kişiye göre kümelenmiş yüzde95 betimsel aralık doğru tanıma için yaklaşık %66,0–%87,3'tür; sıfır gözlenen yanlış kabul nüfus garantisi değildir.

   Üç koşumda başarılı işlerin 772'si özgün yolu, sekizi korumalı kurtarma yolunu kullandı; tüm 780 başarı `cuda:0` ve izinli ön işleme sürümünü bildirdi. Yeni grubun kurtarılan tek işi bir kayıtsız kişi sorgusuydu. İş yürütme süresinin yüzde95 dilimi kalibrasyonda 0,184, tarihsel testte 0,183, yeni grupta 0,194 saniye; kuyrukta yaklaşık iki saniyedir. Bu süreler sunucu iş süresidir, yalnız GPU çekirdek zamanı veya tüm yükleme süresi değildir.

3. Maddeler:

   **KUSUR**
   M1 Sessizliksiz iki kişi karışımlarının 2/10'u eski yeterli kanıt yolunda hâlâ kabul ediliyor; bu düzeltme o yolu değiştirmedi. Çok konuşmacı ayrıştırma kanıtı yok.
   M2 Üç saniyeden kısa bölgeler kayboluyordu; yalnız yetersiz kanıtta özgün bölgeleri denetleyen kurtarma eklendi. [Gerçek PCM ve HTTP testleri](automated-report.md).
   M3 Korumasız birleştirme, aralıklı iki kişi karışımlarının 9/10'unu kabul etti; bu adaylar reddedildi. Özgün parça koruması aynı 10/10 karışımı reddetti.

   **TUZAK**
   M4 Kalibrasyondaki iki ek doğru sorgu aynı kişiden gelir; tarihsel testte yalnız bir ek doğru tanıma vardır. Küçük kazanım istatistiksel kesinlik veya %95 hedefinin sağlanması değildir.
   M5 50 aday, 50 kayıtlı kişi demek değildir. Yeni grupta 10, tarihsel grupta 21 kişinin ilk kaydı reddedildi; bu kişiler değerlendirmeden çıkarılmadı.
   M6 Temiz İngilizce okuma, birleştirilmiş sesler ve ayrık kaynak bölümleri Türkçe toplantı, farklı gün/mikrofon veya model eğitimindeki kişilerden kesin ayrıklık kanıtı değildir.
   M7 İlk canlı yetki kontrolü uygulama `super_admin` hesabının tenant geçişini yanlışlıkla yasak bekledi; beş yanlış beklenti kayıtta korundu, normal okuyucu hesabıyla doğru yetki sınırı doğrulandı.

   **GÖZLEM**
   M8 `preprocessing_version` iş sonucuna tipli aktarılır; eski sonuçlarda `null` kalır. Yedi günlük iş saklaması geçerlidir; kalıcı örnek provenansı iddiası yok. [Sözleşme raporu](metadata-report.md).
   M9 Kullanıcının asıl profilinin genel API yanıtı ve diğer projelerin kapsayıcıları son kontrolle korundu; özel vektörlerin veya bütün veritabanı baytlarının eşitliği iddia edilmedi. [Son korunum](live-preservation-final-report.md), [tarayıcı son korunum](browser-api-final-report.md).

   **AÇIK**
   M10 Öncelikli doğruluk sorunu ilk profil kaydındaki başarısızlıklardır. 001'in %95 hedefi, temsilî Türkçe veri ve sahibin kabulü sağlanmadı; yeni gruptaki geri dönüş başarısı tarihsel grubun başarısızlığını kapatmaz.
   M11 Onaylı çevrimdışı güvenlik ve kalıcı Playwright girdileri eksik. Canlı L2 gözlemleri var; kümülatif kapılar eksik olduğundan tam L1/L2 veya L3 kabulü iddia edilmez.
   M12 Uzun toplantı, konuşmacı ayrıştırma ve canlı ses için 002/003 kapsamları hâlâ Draft; mevcut pilot 120 saniye/50 MiB tek konuşmacılı girdiyi destekler.

   **YAN-ETKİ**
   M13 Dört ayrı değerlendirme hesabı/tenant, test kayıtları ve profilleri yerel geliştirme veritabanında saklandı. Ham ses/manifest ve kimlik bilgileri Git dışındadır; bu rapor toplu veridir.
   M14 Çıkarım kodu, tipli iş metadata'sı, üretilen sözleşmeler, veri araçları ve testleri güncellendi. Spark yeni imaja geçirildi; Windows backend/worker yeniden başlatıldı. Uygulama şeması ve model ağırlıkları değiştirilmedi.
