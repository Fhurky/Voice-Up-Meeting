# Koşum raporu — 2026-09-13 · Gerçek uygulamada son deney durumu

1. Sonuç: İki sıradan hesapta 16 gerçek HTTP kontrolü geçti — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `http://127.0.0.1:8081/api/voiceup/v1` üzerinden gerçek kullanıcı/parola girişi, on iki toplantı GET ve iki profil galerisi GET; `kt-vibecoding-python-web-v2` yerel RTX yığını. [Toplu gözlemler](live-final-check.json).
3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 Bu son kontrol salt okunurdur; önceki GPU deneyleri tekrar çalıştırılmadı ve yeni doğruluk örneği sayılmaz.
   **GÖZLEM**
   M2 On iki toplantının tamamı `succeeded`; taban çizgisinde sayı alanları boş, adayın altı toplantısında her iki alan da 2; iki galeride altışar profil var.
   M3 Her iki girişte uygulama super-admin bayrağı kapalıdır; rol atlama veya tarayıcı oturumuna token enjekte etme kullanılmadı.
   **AÇIK** — yok
   **YAN-ETKİ**
   M4 Yalnız toplu son kontrol kanıtı yazıldı; kimlik bilgileri, tokenlar, isimler ve özel kişi/tenant kimlikleri yayımlanmadı.
