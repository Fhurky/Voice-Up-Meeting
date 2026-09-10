# Koşum raporu — 2026-09-10 · Profil kapasitesi ön yüz kırmızı aşaması.

1. Sonuç: Yeni kapasite davranışlarını koruyan 13 test beklenen nedenle başarısız oldu — birim 9 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel Windows Git Bash → `scripts/stack.sh` → çalışan Linux frontend konteyneri; `kt-vibecoding-python-web-v2` profili. `npm test -- src/pages/SpeakerProfilesPage.test.tsx src/pages/SpeakerJobPage.test.tsx src/components/AudioJobForm.test.tsx src/lib/speakerErrors.test.ts --reporter=dot`: 22 test, 9 başarılı, 13 başarısız; çıkış 1. İlk koşum aynı sayıları verdi; `ApiError` test kurucu argümanları düzeltildikten sonra yukarıdaki komutla gerçek sözleşmeye karşı kırmızı durum yeniden doğrulandı.
3. Maddeler:

   **KUSUR**
   M1 Liste kapasitesi ve yüklenme/hata engeli bulunmadığından `SpeakerProfilesPage.test.tsx` içinde 8 yeni test başarısız: `49 / 50` bulunamadı veya dosya alanı engelli değildi.
   M2 `profile_limit` kodu genel hataya düştüğünden iki dilde HTTP/terminal iş gösterimi ve ortak eşleme için 5 test başarısız; koruyucular `AudioJobForm.test.tsx`, `SpeakerJobPage.test.tsx`, `speakerErrors.test.ts`.
   **TUZAK**
   M3 `ApiError` kurucusu `(status, message, code)` sırasını kullanır; ilk koşumdaki üç test argümanı düzeltildi ve aynı kırmızı sonuç tekrar gözlendi.
   **GÖZLEM**
   M4 Önceden var olan 9 davranış testi geçti; canlı kullanıcı kayıtları ve önceki kanıtlar değiştirilmedi.
   **AÇIK**
   M5 Yeşil uygulama, tam kalite kapısı ve gerçek tarayıcı kanıtı bu kırmızı aşamada henüz koşulmadı.
   **YAN-ETKİ**
   M6 Kapasite için 13 otomatik test eklendi; profil sayfası test yanıtlarına sözleşmedeki `max_profiles` alanı eklendi. Veri fikstürü oluşturulmadı.
