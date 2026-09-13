# Koşum raporu — 2026-09-13 · İki normal hesapla gerçek HTTP önizlemesi

1. Sonuç: İki tenant hesabında gerçek model önizlemesi ve veri değişmezliği doğrulandı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows üzerinden çalışan `127.0.0.1:8081` uygulaması, yerel Ollama `qwen3.5:27b`, profil `kt-vibecoding-python-web-v2`; [toplu kanıt](live-http-aggregate.json).

   | Akış | Gözlenen |
   |---|---|
   | Son HTTP koşumu | 30 gerçek HTTP isteği, iki mevcut normal hesap; ikisinde okuma ve çalıştırma izinleri |
   | Model önizlemesi | İki POST 200; iki sonuç da `unchanged`, yaklaşık 28,92 ve 29,66 saniye |
   | Kaynak bağlama | Satır kimliği, orijinal metin, SHA-256 ve sabit model digest eşleşti; `Cache-Control: no-store` |
   | Değişmezlik | Önce/sonra toplantı, bütün metin sayfaları, konuşmacılar ve profil listeleri eşit |
   | Olumsuz erişim | Tenant başlığı yokken 400; tenant mevcut ve kimlik doğrulaması yokken 401; yabancı tenant kaynağına 404 |

3. Maddeler:

   **KUSUR**
   M1 İlk deneme betiği başlıksız isteği yanlışlıkla 401 bekledi; mevcut tenant middleware sözleşmesi 400'dür. Beklenti düzeltildi, son 30 istek geçti; ürün yetki davranışı değiştirilmedi.

   **TUZAK**
   M2 İlk betik bir gerçek model 200 yanıtı ve kaynak denetiminden sonra yanlış HTTP beklentisinde durdu; bu fazladan çağrı son iki çağrıya veya doğruluk örneklemine eklenmez.

   **GÖZLEM**
   M3 Normal kullanıcı akışı `super_admin` atlamasına dayanmadı; model çalışırken ve sonrasında kaynak/izin korumalarının regresyonları ayrıca 20 PostgreSQL testiyle kapsandı.

   **AÇIK**
   M4 Bu iki canlı yanıt yeni kelime önermedi; doğru düzeltme isabeti veya gerçek arayüzün bütün sonuç dalları bu HTTP koşumundan çıkarılmaz.

   **YAN-ETKİ**
   M5 Mevcut test kayıtları ve hesapları kullanıldı; yeni toplantı/profil oluşturulmadı. Kimlik bilgileri, kaynak metin ve ayrıntılı yanıtlar yalnız Git dışı `outputs/` altında kaldı.
