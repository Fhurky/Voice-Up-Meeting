# Koşum raporu — 2026-09-10 · Konuşmacı metriği kanıtlarının son mahremiyet ve kaynak koruma denetimi.

1. Sonuç: Korunan 98/98 dosya aynı kaldı; 44 dosya mahremiyet taramasında ve 77 yerel belge bağlantısında bulgu yok — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel · doğrulama; `kt-vibecoding-python-web-v2`, Windows PowerShell ve mevcut backend Python ortamı; [tam komut, yöntem ve dosya özetleri](privacy-final-review.json).

   | Denetim | Gözlenen sayı |
   | --- | ---: |
   | Eski konuşma kurtarma kanıtı / ham sonuç / manifest SHA-256 ve boyut karşılaştırması | 92 / 3 / 3 aynı |
   | Yeni kanıt / ilgili belge / bu iki denetim çıktısı | 36 / 6 / 2 tarandı |
   | Yerel bağlantı hedefi / dış bağlantı biçimi | 77 / 2 geçerli |
   | Özel kimlik, kimlik bilgisi, ses veya vektör bulgusu | 0 |
3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Kök `.venv` ortamında `python-dotenv` bulunmadığı için ilk yardımcı yükleme girişimi çalışmadı; aynı salt okunur denetim mevcut backend ortamında tamamlandı.
   M2 Bu iki çıktı özette öz-karmaya alınmaz; içerikleri ayrıca taranır. Sonraki belge değişiklikleri bu dosya özetlerinin yeniden doğrulanmasını gerektirir.

   **GÖZLEM**

   M3 [İlk kaynak envanterindeki](source-integrity.json) 98 dosya ve eski 92 dosyalık dizin envanteri korundu; özel karşılaştırma değerleri rapora yazılmadı.
   M4 Çalıştırma kanıtlarında yerel çalışma alanı/araç yolları korunabilir; taranan kapsamda kaynak kişisi veya uygulama kimlik bilgisi eşleşmesi bulunmadı.

   **AÇIK**

   M5 Özel sayısal vektör karşılaştırma girdisi yoktu; uzun sayısal diziler ve ses yükü imzaları tarandı. Dış bağlantı erişimi ve yerel bağlantı parçaları denetlenmedi.
   M6 Bu statik denetimin kanıt seviyesi L1'dir; yeni model çıkarımı, ses çözümü, tarayıcı, API veya veritabanı koşumu yapılmadı ve bunlar için yeni canlı kanıt iddia edilmez.

   **YAN-ETKİ**

   M7 Yalnız bu iki anonim denetim dosyası ve Git dışında tutulan yerel denetim yardımcısı eklendi; eski kanıt, ham sonuç, manifest, ürün kodu, model ve çalışma zamanı değişmedi.
