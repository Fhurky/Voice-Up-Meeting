# Koşum raporu — 2026-09-11 · Kullanıcının Türkçe WAV dosyası yerel toplantı akışında işlendi

1. Sonuç: Gerçek kayıt yükleme, yazıya çevirme ve otomatik profil oluşturma geçti — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; canlı API 1 başarılı; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, ana uygulama HTTP 8081, RTX 4060 Laptop GPU, ayrı normal kullanıcı/test tenantı. Daha önce kullanıcının denememizi istediği `erdogan2.wav`, mevcut parçalı yükleme yardımcısıyla yüklendi; dil `tr`, kişi sayısı ipucu yok, otomatik hafıza açık. [Sayısal sonuçlar](turkish-source-results.json).
3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 Dosya 52,6293 saniyedir; API 35,7990 saniye konuşma ve bir kişi bildirdi. Dosya süresi ile kullanılabilir konuşma süresi aynı ölçü değildir.
   **GÖZLEM**
   M2 Analiz `succeeded`, kişi `enrolled`, hafıza toplamı 1 oldu. İki transkript satırında toplam 546 karakter üretildi; kaynak SHA-256 ve yinelenen tamamlama kimliği doğrulandı.
   M3 Dosya adı gerçek kişinin kimliği için kanıt sayılmadı; sistem yalnız otomatik geçici profil adı verdi. Ham metin, ses ve vektörler yayımlanmadı.
   **AÇIK**
   M4 Elle doğrulanmış referans transkript ve kimlik etiketi yok; bu koşum kelime/kimlik doğruluğu veya çok konuşmacılı Türkçe toplantı kabulü değildir.
   **YAN-ETKİ**
   M5 Ana kullanıcı verisini değiştirmeyen ayrı test tenantında bir toplantı ve bir profil oluşturuldu; özgün masaüstü dosyası değiştirilmedi.
