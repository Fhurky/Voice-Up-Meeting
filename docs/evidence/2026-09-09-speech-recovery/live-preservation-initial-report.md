# Koşum raporu — 2026-09-09 · İlk canlı korunum ve tenant erişim denetimi

1. Sonuç: Normal okuyucu hesabıyla canlı erişim ve korunum kontrollerinin tamamı geçti; ilk denemedeki ayrıcalıklı hesap beklentisi düzeltildi — birim 0 başarılı / tarayıcı 0 başarılı / canlı kontrol 31 başarılı / atlanan 0; ilk ayrıcalıklı hesap koşumu 24 başarılı ve 5 yanlış aktör beklentisi başarısız; karar bekleyen: yok.
2. Koşulan: Windows üzerinde çalışan FastAPI uygulamasına mevcut `benchmark-local-pilot.py#Api` ile döngüsel adres üzerinden HTTP istekleri; iki mevcut yerel konteynere sınırlı `docker inspect`. Normal hesap koşumu 21 GET ve 3 giriş isteği kullandı; sonuç [canlı denetim kaydındadır](live-preservation-initial-reader.json).
3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 İlk kalibrasyon hesabı uygulama düzeyinde `super_admin` olduğu için başka tenant başlığıyla erişim yetkiliydi; 403 bekleyen 5 kontrol yanlış aktörü kullandı. [İlk sonuç](live-preservation-initial.json) silinmedi; [canlı hesap bağlamı](live-preservation-account-context.json) rolü doğrular.

   M2 Normal hesap `/auth/me` yanıtında `is_super_admin=false` olarak doğrulandı; kendi tenant'ındaki yetkileri ve yabancı tenant'a erişememesi ayrı ayrı ölçüldü. Hiçbir hesap veya rol değiştirilmedi.

   **GÖZLEM**

   M3 Özgün kullanıcı profilinin tüm genel API yanıtı başlangıç kaydıyla birebir aynı: profil sayısı, ad, örnek sayısı, model kimliği/sürümü ve zaman damgaları korundu. Beklenen ve gerçek kanonik yanıt hashı `922a57904521848edce356cfe2a03ec31027e755f1dc9bff62fb0a370250de0a`.

   M4 VoiceUp dışındaki iki yerel konteynerin kimlikleri, çalışma durumları ve başlangıç zamanları eski anlık görüntüyle eşleşti; ikisi de çalışıyordu. Genel kayıtta konteyner adları ve kimlikleri yerine anonim kontrol numaraları ve hashlar bulunur.

   M5 Anonim profil listesi, iş listesi ve iş ayrıntısı istekleri 401; tenant başlığı eksik aynı istekler 400 döndü. Bunlar toplam 6 ret kontrolüdür.

   M6 Varlığı kendi hesabıyla doğrulanan 3 eski tenant işi, normal okuyucunun kendi tenant'ında 404; yabancı tenant başlığıyla 403 döndü. Yabancı tenant profil/iş listeleri de 403; okuyucunun kendi listelerinde yabancı kaynak görünmedi.

   **AÇIK**

   M7 Bu ilk anlık gözlem, devam eden canlı değerlendirmeler bittikten sonraki korunum sonucu değildir; tamamlanma sonrası tekrar denetimi henüz çalıştırılmadı.

   M8 Profil eşitliği genel API alanlarını kapsar; özel veritabanı vektörlerinin veya tüm depolama baytlarının eşitliği iddia edilmez. Liste denetimi güncel tek sayfayı ve açık tenant başlığı retlerini kapsar.

   **YAN-ETKİ**

   M9 Yalnız giriş ve GET istekleri gönderildi; ses yükleme, model çağrısı, iş oluşturma, kullanıcı verisine PATCH/DELETE veya konteyner değişikliği yapılmadı. Özgün ses örnekleri alınmadı veya başka yere yüklenmedi.

   M10 Ham profil/konteyner gözlemleri yok sayılan özel çıktı dizininde kaldı; burada anonim sonuçlar ve hashlar yayımlandı. Giriş tokenları, parolalar, profil adları ve kaynak kimlikleri yayımlanmadı.
