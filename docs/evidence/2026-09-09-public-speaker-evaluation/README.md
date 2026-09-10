# Koşum raporu — 2026-09-09 · Açık ses verisiyle uygulama ve Spark doğrulaması

1. Sonuç: Yazılım kontrolleri geçti; gerçek ses tanıma yüksek doğruluk hedefini karşılamıyor — birim 819 başarılı / tarayıcı 16 başarılı / atlanan 2 ortam kapısı; karar bekleyen: yok. Seçilen politikayla 1.009 gerçek iş terminal duruma ulaştı: 820 başarılı, 189 kalite hatası. Canlı davranış gözlendi; eksik güvenlik ve temsilî veri kanıtı nedeniyle tam kabul verilmedi.
2. Koşulan: Sabit `kt-vibecoding-python-web-v2`; Windows uygulama ve PostgreSQL, Ethernet/SSH üzerinden NVIDIA DGX Spark GB10 CUDA çıkarımı. Kalibrasyon ve test ayrı hesaplarda, ayrık kişilerle yürütüldü.

   | Kapsam | Sonuç ve kanıt |
   | --- | --- |
   | Lisanslı gerçek ses hazırlığı | [OpenSLR LibriSpeech](https://www.openslr.org/12), CC BY 4.0; dört resmî arşiv, toplam 1.327.654.041 bayt. 140 seçilmiş kişi, 604 WAV. [Protokol ve tekrar koşumu](../../PUBLIC_DATASET_PROTOCOL.md). |
   | Referans/çıkarım/Spark sınırları | 641 başarılı; iki Windows atlaması ayrıca gerçek Linux sembolik bağlantı testinde geçti. [Referans](reference-report.md), [Linux](symlink-report.md). |
   | Başlatıcı regresyonları | Önceki pakete ek 9 vaka geçti; eski adres ve UTF-8 aktarımı düzeltildi. [Rapor](nginx-reload-report.md), [PowerShell tarih uyumu](../2026-09-09-powershell-compatibility/README.md). |
   | Veri araçları | Hazırlama 23, API değerlendirme 43, anonim raporlama 11: toplam 77 başarılı. [JUnit](evaluation-tool-tests-final.xml), [bağımsız inceleme](audit-report.md). |
   | Son tam kalite kapısı | Güncellenen başlatıcının canlı kontrolünden sonra `scripts/quality-gate.sh all`, exit 0: 69 backend (54 birim + 15 gerçek PostgreSQL), 21 frontend; config, biçim/lint/tip, migration/drift, OpenAPI/tip, build, yönetişim ve chart kontrolleri geçti. Geçici test veritabanı silindi; uygulama veritabanına migration uygulanmadı. [Ham çıktı](quality-gate-post-startup.txt), [koşum bilgisi](quality-gate-post-startup-result.json). Önceki aynı 90-testlik [koşum](quality-gate-final.txt) tekrar toplama eklenmedi. |
   | Benzersiz otomatik toplam | 641 + 2 + 9 + 77 + 90 = **819**. Tekrarlanan ve kırmızı koşumlar tekrar eklenmedi. [Kaynak hashleri ve test envanteri](test-inventory.json). |
   | Gerçek arayüz ve yetki | 16 tarayıcı akışı, ayrıca 7 HTTP yetki kontrolü geçti. [Tarayıcı raporu](browser-report.md), [yetki sonuçları](live-authorization.json). |
   | Son tek komut kontrolü | Güncellenen başlatıcı hem PowerShell 7 hem Windows PowerShell 5.1 ile `-NoBrowser` kullanılarak hazır duruma ulaştı. Uygulama/Spark hazır, yerel model kapalı, asıl profil ve diğer kapsayıcılar değişmedi. [Canlı sonuç](final-live-environment.json), [iki başlatıcı koşumu](one-click-final.json). |
   | Önceki 0.75 referansı | Ayrı eski kalibrasyon koşumu 142 iş; 10 adaydan 7 kayıt, bilinen sorguda 5/30 doğru. [Tarihsel sonuç](calibration-summary.json). |
   | Politika seçimi | Yalnız 50 adaylık kalibrasyon teşhisi: 0.75 ile 50/150, 0.55 ile 109/150 doğru; 0.50 iki yanlış bilinmeyen kabulü üretti. [Teşhis tablosu](calibration-policy-grid.json), [sabit politika](selected-policy.json). Eski 10-aday uygulama koşumuyla bu 50-aday tablosu doğrudan karşılaştırılmamalıdır. |
   | Seçilen politikayla gerçek kalibrasyon | 302 iş; 40/50 profil, 109/150 doğru tanıma, 0 yanlış kişi; 100 bilinmeyende 87 bilinmeyen, 4 belirsiz, 9 kalite hatası, 0 yanlış kabul. Yeni kişinin kaydı ve ayrı sesinden geri dönüşü başarılı. [Sonuç](calibration-selected-summary.json). |
   | Ayrı kişilerle gerçek test | 707 iş; 5/10/20/50 adaylı iç içe galeriler. Aşağıdaki tablo bütün planlanan bilinen sorguları içerir. [Tam sonuç](test-summary.json). |
   | Güvenlik / kalıcı tarayıcı kapısı | `scripts/security-gate.sh` ve `scripts/e2e.sh speaker-identity`, ikisi de exit 2: onaylı çevrimdışı araç paketleri yok. [Güvenlik çıktısı](security-gate.txt), [tarayıcı çıktısı](permanent-browser.txt). Başarılı sayılmadı. |

   | Planlanan kişi | Oluşturulan profil | Doğru tanınan / tüm bilinen sorgular | Doğru tanıma oranı | Yanlış kişiye atama |
   | ---: | ---: | ---: | ---: | ---: |
   | 5 | 2 | 6 / 15 | %40,0 | 0 |
   | 10 | 4 | 11 / 30 | %36,7 | 0 |
   | 20 | 10 | 28 / 60 | %46,7 | 0 |
   | 50 | 29 | 77 / 150 | **%51,3** | 0 |

   Son satırda 21 kişinin ilk kaydı reddedildi: 14 yetersiz kullanılabilir konuşma, 7 tutarsız ses. Bilinen 150 sorguda 77 doğru, 46 bilinmeyen, 1 belirsiz ve 26 kalite hatası var. Kişiye göre kümelenmiş yüzde 95 bootstrap aralığı doğru tanıma için yaklaşık **%39,3–%63,3**; nüfus garantisi değildir.

   Her galeri aynı 20 bilinmeyen kişinin aynı 100 sorgusunu kullanır: 80 bilinmeyen sonucu, 20 kalite hatası, sıfır yanlış kabul. Bunlar 400 bağımsız kişi deneyi değildir. Kalite hataları doğru ret sayılmadı; gözlenen yanlış kabul alt sınırı %0, değerlendirilemeyenleri hesaba katan en kötü durum üst sınırı %20. Sıfır gözlenen hata, hedeflenen ≤%1 yanlış kabul oranının kanıtı değildir.

   **Ayrı test grubunda yeni kişi kaydı başarısız oldu; geri dönüş sorgusu da yetersiz konuşma nedeniyle başarısız oldu.** Bu temel senaryo yalnız kalibrasyon grubunda geçti. Son 50-aday bölümünde iş yürütme p95 0,178 saniye, kuyruk p95 1,976 saniye; hata işleri dahildir. Tam kalite kapısı testin son bölümüyle çakıştı; bu sayılar yalıtılmış hız karşılaştırması veya saf GPU süresi değildir.

3. Maddeler:

   **KUSUR**

   M1 PowerShell 7 tarih dönüşümü geçerli tünel kaydını reddediyordu; sürüme uygun JSON okuma ve iki motorda regresyonla düzeltildi. [Kanıt](../2026-09-09-powershell-compatibility/README.md).

   M2 Backend adresi değişince nginx eski adrese gidiyor, 502/504 oluşuyordu; etkin Spark konfigürasyonu sınanıp yenileniyor. Konsola bağlı native stdin BOM/karakter bozulması da düzeltildi. [Kırmızı/yeşil kanıt](nginx-reload-report.md).

   M3 Raporlayıcı geri dönüşte yanlış kişi ile bilinmeyen/belirsiz sonucu ayırmıyordu; planlanan, çalışmayan, bekleyen, hatalı ve yanlış kimlik sonuçları ayrı alanlarla korunuyor. [İnceleme ve testler](audit-report.md).

   **TUZAK**

   M4 Profil oluşturulamayan kişiler ve kalite hataları başarı paydasından çıkarılmadı. 50 aday, 50 kayıtlı profil demek değildir. İngilizce sesli kitap, birleştirilmiş ses parçaları ve farklı kaynak bölümleri; Türkçe toplantı, farklı gün/mikrofon veya üst üste konuşma kanıtı değildir.

   M5 Eşik test sonucuna göre değiştirilmedi. Kalite filtresini gevşetme ve daha uzun sessizlik aralığı denemeleri karışık sonuç verdi; kalibrasyon teşhisi bu değişiklikleri ürüne taşımak için yeterli değildi. Ses penceresi ön işleme ile kalite retleri sonraki doğruluk çalışmasının önceliğidir.

   M6 Windows'taki iki sembolik bağlantı atlaması Linux eşdeğerleriyle kapandı; Windows izinleri doğrulanmış sayılmaz. İlk Linux araç toplaması ve geçici rapor okuma kodundaki varsayılan karakter kodlaması hataları düzeltildi; bunlar ürün doğruluğu başarısı olarak sayılmadı.

   **GÖZLEM**

   M7 Başarılı 820 aday-kalibrasyon/test işi aynı sabit model sürümünü ve `cuda:0` cihazını döndürdü. Model ağırlığı değişmedi; seçilen uygulama politikası `0.55 / 0.45 / 0.10`. Gerçek kişi testindeki düşük başarı, donanımın hazır olmadığı anlamına gelmez.

   M8 Asıl kullanıcı profili ve iki başka projenin çalışan kapsayıcıları değişmedi. [Profil karşılaştırması](user-data-preservation.json), [kapsayıcı karşılaştırması](container-preservation.json). Özel veriler için [ilk gizlilik incelemesi](privacy-review.json) ve [son dosya incelemesi](privacy-final-review.json) onaylı güvenlik taramasının yerine geçmez.

   M9 Kör test özeti ayrıca [98 sayısal/provenans kontrolüyle](final-metrics-audit.json) doğrulandı; bunlar 819 otomatik teste tekrar eklenmedi.

   **AÇIK**

   M10 Yüksek doğruluk hedefi ve ayrı test grubundaki yeni kişi/geri dönüş senaryosu karşılanmadı. Türkçe, gerçek toplantı, farklı cihaz/oturum ve kayıtlı 50 kişinin tamamıyla deney eksik; 001/T09 ve sahibin temsilî veri kabulü açık kalır.

   M11 Onaylı güvenlik tarayıcıları ve kalıcı Playwright paketi eksik. Uzun dosya bölümleme, çok konuşmacı ayrıştırma ve canlı ses 002/003 Draft kapsamındadır; mevcut pilot 120 saniye/50 MiB tek konuşmacı sınırındadır.

   **YAN-ETKİ**

   M12 Dört ayrı yerel test hesabı/tenant oluşturuldu; test profilleri ve iş geçmişi saklandı. Sesler/manifestler `data/public-speaker-evaluation/`, kimlik bilgileri/ham sonuçlar `outputs/public-speaker-evaluation/` altında Git dışında tutuldu. Kamuya uygun kanıt yalnız toplu sayılardır.

   M13 Veri hazırlama, API değerlendirme ve anonim raporlama araçları ile testleri eklendi; pilot eşiği ve Windows başlatıcıları düzeltildi. Yeni bağımlılık/paket/imaj indirilmedi; mevcut Linux test araçları salt okunur bağlandı. Veri arşivleri resmî kaynaktan indirildi. Commit veya push yapılmadı.
