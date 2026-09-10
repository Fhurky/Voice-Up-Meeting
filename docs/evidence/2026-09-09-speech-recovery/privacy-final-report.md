# Koşum raporu — 2026-09-09 · Yayımlanacak kanıtların gizlilik ve bağlantı incelemesi

1. Sonuç: 90 mevcut kanıt dosyasında doğrulanmış gizli değer, gerçek ses veya biyometrik vektör sızıntısı bulunmadı; yerel bağlantı hedefleri geçerli — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows üzerinde yerel dosya/JSON/JUnit karşılaştırması ve mevcut bir PNG'nin görsel incelemesi; model, veri tabanı veya uygulama testi çalıştırılmadı. Sabit `kt-vibecoding-python-web-v2` değişmedi.

   | Kontrol | Kapsam / gözlenen sonuç |
   | --- | --- |
   | Gerçek hesap ve sır karşılaştırması | Dört yeni değerlendirme hesabı, dört önceki değerlendirme hesabı, asıl kullanıcı ve normal okuyucu hesabı dahil 10 hesabın kullanıcı adı/parolası; iki mevcut `.env` dosyası. Değerler yalnız yerelde karşılaştırıldı. |
   | Özel uygulama ve kaynak kimlikleri | 3.938 uygulama kimliği; üç manifestten gerçek konuşmacı, kayıt, kaynak ses parçası ve ses yolu değerleri. Doğrulanmış eşleşme sıfır. |
   | İçerik imzaları | Token, JSON Web Token, özel anahtar, ses yükü ve sayısal vektör adayları incelendi. Tek ses imzası adayı geçersiz birim test başlığı olarak sınıflandı. |
   | Kaynak/derleme belgeleri | Spark kaynak manifesti, derleme ve aktarım çıktıları aynı dosya taramasına dahil edildi. Kaynak/imaj özetleri ile yerel çalışma yolları kimlik sırrı olarak yanlış sınıflanmadı. |
   | Bağlantılar ve dosya bütünlüğü | Yerel Markdown hedefleri doğrulandı; dış bağlantılarda yalnız biçim kontrol edildi. Dosya sayıları, bağlantı sayıları ve her dosyanın SHA-256 değeri [JSON kaydında](privacy-final-review.json). |

3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 `inference-green.xml` içindeki `test_invalid_audio` vaka adında kasıtlı geçersiz WAV başlığı bulunur; kaynak testteki kısa `bytes` fikstürüyle eşleştirildi. Gerçek ses kaydı değildir; yanlış pozitif kayıtta korundu.
   M2 Sentetik birim test vektörleri biyometrik veri sayılmadı. Çıplak sayısal okuyucu numaraları hash veya kosinüs değerleri içinde aranmadı; gerçek kimlik biçimleri ve değer sınırları kullanıldı.
   **GÖZLEM**
   M3 Mevcut `browser-recognized.png` yalnız genel uygulama ve doğrulama-konuşmacısı etiketleri gösterir; gerçek okuyucu kimliği, hesap, iş adresi veya ses görünmez. Yeni ekran görüntüsü veya pano erişimi yapılmadı.
   M4 Son 90 dosyanın özeti saklandı; bu iki denetim çıktısı kendilerini özetleme döngüsünden dışlandı. Ana rapora bağlantılar taramadan önce eklendi; son metrik ve korunum belgeleri taramaya dahildir.
   **AÇIK**
   M5 Dış URL içeriği yeniden açılmadı ve veri tabanındaki ham vektörler okunmadı; bu yerel yayımlama denetimi uygulamanın eksik onaylı güvenlik tarayıcı kapısını tamamlamaz.
   **YAN-ETKİ**
   M6 İki anonim gizlilik belgesi ve ana rapordaki bağlantıları eklendi. Kaynak kodu, üretilen sözleşmeler, model, uygulama verisi ve önceki kanıtlar değiştirilmedi.
