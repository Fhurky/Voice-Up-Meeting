# Koşum raporu — 2026-09-10 · Kayıt başarısızlıkları ve mevcut modelin ayrıştırılması.

1. Sonuç: Öncelikli doğruluk kaybı ilk profil kaydı ve sorgu tutarlılık reddi — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; üç mevcut sonuç/manifest çifti doğrulandı; karar bekleyen: yok. Yeni model doğruluk deneyi yapılmadı.
2. Koşulan: Yerel salt okunur `speaker_metrics.summarize_metrics` ve mevcut raporun `outcome/subset_counts` yardımcıları; anonim kişi-kayıt ilişkisi sayımları. Canlı model kimliği mevcut backend→Spark `/ready` yolundan ayrıca okundu.

   | Ölçü | Son temiz İngilizce grup | Kalibrasyon |
   | --- | ---: | ---: |
   | İlk kaydı başarılı kişi | 40/50 | 40/50 |
   | Doğru kimlik / bütün planlı bilinen sorgular | 116/150 | 111/150 |
   | Doğru kimlik / profili oluşturulan kişilerin sorguları | 116/120 (%96,67) | 111/120 (%92,50) |
   | Kaydı olmayan kişilerin kayıp sorguları | 30/34 kayıp (%88,24) | 30/39 kayıp (%76,92) |
   | Kayıtlı kişilerde kalan kayıplar | 4 `inconsistent_audio` | 9 `inconsistent_audio` |
   | İlk kayıt hataları | 10 `inconsistent_audio` | 10 `inconsistent_audio` |

   Temiz grupta kaydı olmayan kişilerin 30 sorgusu 22 `unknown`, iki `ambiguous`,
   altı `inconsistent_audio`; kalibrasyonda 21 `unknown`, dokuz `inconsistent_audio`.
   Kayıtlı kişilerde başarılı olup yanlış/unknown/ambiguous olan sorgu yoktur.
   Temiz grupta 36 kişi 3/3, dört kişi 2/3 doğru tanındı.

   Canlı hazır model: `speechbrain/spkrec-ecapa-voxceleb`, revision
   `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`, `dimensions: 192`, `device: cuda:0`.
   Hazır olma yanıtı çıkarım doğruluğu deneyi değildir. Yeni adayların birincil
   kaynakları ve önerilen deney [araştırma belgesindedir](../../../plans/SPEAKER_QUALITY_50.md).

3. Maddeler:

   **KUSUR**
   M1 Tutarlılık reddi iki grupta da ilk kayıt kapsamını %80'de bırakıyor; kimlik benzerlik eşiği eksik profilleri oluşturamaz.
   **TUZAK**
   M2 %96,67 seçilmiş kayıtlı alt grubun oranıdır; genel doğruluk %77,33 kalır. 50 aday, 50 başarıyla kayıtlı kişi değildir.
   M3 Sorgu retleri değişmezse yalnız ilk kayıtları düzeltmenin temiz gruptaki teorik tavanı 140/150=%93,33'tür; kazanım ölçülmedi. %95 için ek sorgu retlerinin de azaltılması gerekir.
   M4 Artık incelenmiş bu temiz grup yeni model seçimi sonrasında kör kabul verisi olarak adlandırılamaz; yeni ayrık test gerekir.
   **GÖZLEM**
   M5 Eski rapor/manifestler yeniden yazılmadı; kişi/hesap/iş kimlikleri veya sesler bu rapora aktarılmadı. Model kartlarındaki iki-kayıt EER değeri uygulama doğruluğuna çevrilmedi.
   **AÇIK**
   M6 Alternatif kayıtlar, ReDimNet2/WeSpeaker karşılaştırması ve temsilî Türkçe koşum henüz yapılmadı; bunlar araştırma önerisidir.
   **YAN-ETKİ**
   M7 İlk `/ready` isteği durmuş SSH tüneli nedeniyle 502 idi; mevcut `scripts/spark-tunnel.ps1 -Action Start` tüneli başlattı ve yeniden kontrol hazır yanıtı verdi. Model/ağırlık/çıkarım imajı değiştirilmedi.
