# Koşum raporu — 2026-09-10 · Üç nihai konuşmacı ölçüm raporunun bağımsız çevrimdışı denetimi

1. Sonuç: Üç rapor bağımsız hesapla uyuştu — doğrulama 1304 başarılı / birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel · doğrulama, Windows/Python; `outputs/speaker-metrics/final-independent-audit.py` → [independent-audit.json](independent-audit.json) → son koşum 1304 başarılı / 0 başarısız, ilk koşum 1283 başarılı / 21 başarısız; 3 veri grubu, 3 galeri, 906 kaynak işlem; profil `kt-vibecoding-python-web-v2`.
3. Maddeler:

   **KUSUR**

   M1 İlk denetimdeki 21 uyumsuzluk yalnız sayısal histogram anahtarlarının JSON metin anahtarlarıyla karşılaştırılmasından kaynaklandı; yerel denetim betiğinde JSON gösterimi eşitlendi (DÜZELTİLDİ, son koşum). Ürün kusuru bulunmadı.

   **TUZAK**

   M2 Karar kapsamı `ambiguous` sonuçlarını dışlar; başarılı iş oranıyla aynı değildir. Terminal işlerden ayrı koşucu tamamlanması ve `metrics_complete` doğrulandı.

   **GÖZLEM**

   M3 Donmuş beklentinin SHA-256 özeti korunarak ham rapor ve manifestlerden sayımlar yeniden hesaplandı; kimlik/mikro/makro F1, bilinmeyen F1, hata kırılımı, dönüş ayrımı ve tüm rapor alanları uyuştu.
   M4 Kalibrasyon/geçmiş/yeni veri skorları sırasıyla 80,2532394533 / 61,3636363636 / 82,4930599087; kaynaklar ve test edilmiş kodlar 2026-09-09 tarihli [kaynak kaydıyla](scoring-source-manifest.json) değişmeden eşleşti.
   M5 34 mevcut kanıt dosyası, 3 ham rapor ve 3 manifest değişmedi; donmuş beklenen sonuç özeti ve dosya bağları [denetim kaydında](independent-audit.json).

   **AÇIK**

   M6 Bu denetim mevcut kararların yeniden puanlamasını doğrular; model, canlı uygulama, tarayıcı ve test paketleri yeniden çalıştırılmadı. Yeni canlı doğruluk veya kullanıcı kabulü kanıtı üretmez.

   **YAN-ETKİ**

   M7 Yalnız iki yeni anonim denetim belgesi ve Git tarafından yok sayılan yerel denetim betiği yazıldı; ürün, kaynak/model/test dosyaları ve eski kanıtlar değiştirilmedi.
