# Koşum raporu — 2026-09-10 · VoiceUp konuşmacı doğruluğu ölçüleri

1. Sonuç: `voiceup-open-set-v1` ölçüm protokolü ve çevrimdışı hesaplama aracı tamamlandı; üç mevcut deney yeniden puanlandı — birim/entegrasyon 270 başarılı / tarayıcı 0 başarılı / atlanan 1 güvenlik ortam kapısı; karar bekleyen: yok. Testler ve yeniden puanlama 9 Eylül'de çalıştı; kesinti sonrası kaynak eşleşmesi ve rapor incelemesi 10 Eylül'de tamamlandı. Bu, yeni model deneyi veya yüksek doğruluk kabulü değildir.
2. Koşulan: Sabit `kt-vibecoding-python-web-v2`; gerçek uygulamadan daha önce alınmış üç özel rapor ve bunlara bağlı manifestler, yeni `scripts/report-public-speakers.py --metrics-protocol voiceup-open-set-v1 --manifest ...` çağrısıyla çevrimdışı işlendi. Her grupta 50 planlı bilinen kişi, 20 bilinmeyen kişi, 150 bilinen sorgu ve 100 bilinmeyen sorgu bulunur. İlk kayıt başarısızlıkları paydalarda kalır.

   | Ölçü | Kalibrasyon | Aynı tarihsel test | Yeni temiz İngilizce grup |
   | --- | ---: | ---: | ---: |
   | İlk profil kaydı | 40/50 (%80) | 29/50 (%58) | 40/50 (%80) |
   | Kimlik precision | %100 | %100 | %100 |
   | Kimlik recall | %74,00 | %52,00 | %77,33 |
   | Kimlik micro F1 | %85,06 | %68,42 | %87,22 |
   | Kişilere eşit ağırlıklı kimlik macro F1 | **%76,20** | **%54,00** | **%78,40** |
   | Bilinmeyen precision | %80,91 | %63,28 | %81,03 |
   | Bilinmeyen recall | %89,00 | %81,00 | %94,00 |
   | Bilinmeyen F1 | **%84,76** | **%71,05** | **%87,04** |
   | **VoiceUp Score / 100** | **80,25** | **61,36** | **82,49** |
   | Karar kapsamı | %88,40 | %82,40 | %92,80 |
   | Yeni kişinin kaydı ve sonraki dönüşü | Başarılı | İki işlem de kalite reddi | Başarılı |

   Kaynaklar: [kalibrasyon özeti](calibration-summary.json), [tarihsel özet](historical-summary.json),
   [yeni temiz grup özeti](fresh-summary.json). Üç grup farklı kişiler ve koşullar
   içerir; sütunlar aynı veri üzerinde model sürümü karşılaştırması değildir.

   Precision, kişinin kimliğini verdiğimiz seslerin ne kadarında doğru olduğumuzu;
   recall, tanımamız gereken bütün seslerin ne kadarını tanıdığımızı gösterir.
   Micro F1 bütün sorguların sayımlarını kullanır; macro F1 her kişiye eşit ağırlık
   verir. Yeni grupta 116 doğru kimlik, sıfır yanlış kimlik ve 34 kaçırma vardır.
   Bu nedenle gözlenen precision %100 iken recall yalnız %77,33'tür.

   ```text
   Precision = TP / (TP + FP)
   Recall    = TP / (TP + FN)
   F1        = 2 × TP / (2 × TP + FP + FN)

   I = kişi başına kimlik F1'lerinin ortalaması
   U = bilinmeyen sınıfının F1'i
   VoiceUp Score = 100 × 2 × I × U / (I + U)
   ```

   TP doğru pozitif, FP yanlış pozitif, FN yanlış negatiftir. Yanlış bir kimlik
   vermek atanan kişi için FP ve gerçek kişi için FN oluşturur. `unknown` ile
   `ambiguous` ayrı kalır; kalite hatası başarılı bilinmeyen tespiti değildir.
   **VoiceUp Score özel bir bileşik skordur; standart F1 veya yüzde doğruluk değildir.**
   Sıfır/tanımsız payda, eksik koşum ve örnek hesap kuralları
   [ölçüm protokolündedir](../../SPEAKER_METRICS.md).

   | Doğrulama | Kanıt |
   | --- | --- |
   | Kabul ve kapsam | [001 / Decision 9](../../../specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md); yalnız çevrimdışı raporlama, yeni bağımlılık yok. |
   | Gerçek rapor kaynakları | [Kaynak bütünlüğü](source-integrity-report.md); 906 eski işlem, 98 dosyalık korunum envanteri. |
   | Üç gerçek komut | [Komutlar ve çıkışlar](rescore-commands.json); üçü de çıkış 0, giriş dosyaları değişmedi. |
   | Bağımsız hesap | [Son denetim](independent-audit-report.md), [makine kaydı](independent-audit.json); üretim hesaplayıcısını kullanmadan 1.304 kontrol başarılı. |
   | Test ve kaynak eşleşmesi | [270 testin raporu](native-tests-report.md), [envanter](test-inventory.json), [kaynak hashları](scoring-source-manifest.json). |
   | Tam uygulama kapısı | [Son kapı](quality-gate-final.txt), [koşum bilgisi](quality-gate-final-result.json); geçici `_test` veritabanı oluşturuldu ve düşürüldü. |
   | Açık güvenlik girdisi | [Güvenlik raporu](security-report.md); çevrimdışı `gitleaks` bulunamadı, kapı çıkış 2. |
   | Gizlilik ve korunum | [Son gizlilik raporu](privacy-final-report.md), [dosya denetimi](privacy-final-review.json). |

3. Maddeler:

   **KUSUR**
   M1 Yinelenen sorguların eksik sorguları gizlemesi, hazır sayaç/oran değişikliği ve geri dönüş listesinin ayrışması yeni protokolde reddedilir. Koruyucu testler: `tests/test_public_speaker_metrics.py`.
   M2 Koşucunun son galeri doğrulaması başarısızsa bütün işler terminal olsa bile skorlar boş kalır; üretici hatası başarılı koşuma dönüştürülmez. Aynı test dosyasındaki üretici tamamlama vakaları bunu korur.

   **TUZAK**
   M3 Skorlar önceden görülmüş sonuçlara sonradan uygulandı; yeni kör deney veya kod doğruluğu artışı değildir. Bu sayılara bakılarak yeni geçme eşiği seçilmedi.
   M4 %100 gözlenen kimlik precision, bütün kişilerin tanındığı veya gerçek hayatta yanlış kabul riskinin sıfır olduğu anlamına gelmez. Bilinmeyen hataları ve mevcut olası kötü durum sınırları JSON'da korunur.
   M5 İç içe galeriler ve aynı testin Windows/Linux tekrarları toplanmaz. Eski protokol çağrısı şema 1 olarak korunur; yeni doğrulama ve ölçüler açık seçeneklerle şema 2 üretir.

   **GÖZLEM**
   M6 İlk kayıt başarısızlıklarının etkisi kimlik recall/macro F1 içinde bulunur; özet skor kayıt oranıyla tekrar çarpılmaz. Yeni kişinin dönüşü ana galeri puanına katılmaz.
   M7 92 yeni metrik testi, 13 eski raporlayıcı testi, 59 koşucu testi, 85 backend ve 21 frontend testi başarılı; Windows'taki 105 tekrar bu toplama yeniden eklenmedi.

   **AÇIK**
   M8 Türkçe doğal toplantı, farklı gün/mikrofon, örtüşen konuşmacılar ve uzun kayıt için doğruluk kabulü hâlâ açık. F1 ve VoiceUp Score için nüfus güven aralığı hesaplanmadı; önceki recall aralıkları bu skorlara aktarılmaz.
   M9 Onaylı güvenlik tarayıcı ortamı eksik; tam ürün L1/L2 kabulü iddia edilmez. Bu çevrimdışı değişiklikte yeni canlı model/tarayıcı koşumu veya sahibin L3 kabulü yoktur.

   **YAN-ETKİ**
   M10 Ölçüm modülü, mevcut raporlama aracının açık seçenekleri, testler ve protokol belgeleri eklendi/güncellendi. Yeni raporlar ayrı dosyalara yazıldı; model, karar eşikleri, uygulama şeması veya kullanıcı akışı değiştirilmedi.
