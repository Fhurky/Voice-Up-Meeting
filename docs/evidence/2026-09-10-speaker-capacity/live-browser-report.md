# Koşum raporu — 2026-09-10 · Gerçek tarayıcıda 50 profil kapasitesi.

1. Sonuç: Güncel uygulamada sekiz canlı arayüz kabul noktası ve altı HTTP kontrolü geçti — birim 0 başarılı / tarayıcı 8 başarılı / atlanan 0; karar bekleyen: yok. Bu kapsamda L2 gözlendi; model doğruluğu ölçülmedi.
2. Koşulan: Windows Docker Compose, gerçek `http://127.0.0.1:8081` ters vekili, Brave üzerinden CUA, normal giriş formu ve yönetici olmayan ayrı test hesabı; sabit `kt-vibecoding-python-web-v2`.

   | Kabul noktası | Gözlenen sonuç |
   | --- | --- |
   | Türkçe kapasite | `Aktif profiller / kapasite: 50 / 50`; ad, dosya ve yeni profil gönderimi kapalı. |
   | Türkçe mevcut profile ekleme | `Örnek ekle` seçilince hedef kişi gösterildi ve dosya alanı açıldı; kapasite engeli bu forma uygulanmadı. |
   | İngilizce kapasite | `Active profiles / capacity: 50 / 50`; `Profile capacity is full.` ve kapalı yeni kayıt alanları. |
   | İngilizce mevcut profile ekleme | `Add sample` seçilince dosya alanı açık; `Cancel` sonrası yeni kayıt yeniden kapalı. |
   | Sayfalama | İkinci sayfa farklı 20 profil gösterirken toplam ve sınır 50/50, yeni kayıt kapalı kaldı. |
   | Sesi tanı ekranı | 50 doluyken analiz dosyası seçimi açık kaldı; bu koşumda dosya/model işi gönderilmedi. |
   | İngilizce terminal hata | `This workspace has reached its limit of 50 active speaker profiles. No new profile was created.` görünür. |
   | Türkçe terminal hata | `Bu çalışma alanında 50 aktif konuşmacı profili sınırına ulaşıldı. Yeni profil oluşturulmadı.` görünür. |

   Sekiz koşul yakalanmış erişilebilirlik durumları üzerinde ayrıca doğrulandı. Giriş ve çıkış gerçek form/düğmelerle yapıldı; tarayıcıya token yerleştirilmedi. [HTTP kanıtı](live-api.json) sıradan rol, 50/50, `409/profile_limit`, değişmeyen profil listesi, yeni iş oluşmaması ve terminal fikstür görünümünü doğrular. [Ters vekil ağ özeti](live-network.json) başarılı okumaları ve beklenen 409'u içerir; hesap/iş kimlikleri yayımlanmaz.

3. Maddeler:

   **KUSUR** — yok
   **TUZAK**
   M1 İlk geçişte Vite önbelleği eski Türkçe kataloğu sundu: `Missing locale key: speaker.profiles.capacityLoading`; kaynak dosyada anahtar vardı, HTTP ile eski modül doğrulandı. Frontend yeniden başlatılıp sayfa yenilenince giderildi; yeni kaynak yaması gerekmedi.
   M2 İlk hata bir konsol hatası ve bir React uyarısı üretti; yeniden başlatma sonrasında yeni uyarı/hata 0. Yanlış başlık bekleyen bir otomasyon seçicisi bulunamayınca gerçek ağaçtan gezinildi; bu bir ürün kusuru değildi.
   M3 Ağ özetinde gezinme sırasında iptal edilmiş bir iş okuması 499 döndü; aynı işin sonraki okuması 200 ve iki dilde terminal görünümü başarılıdır.
   **GÖZLEM**
   M4 Canlı fixture 50 sentetik profil, 50 ilişkili örnek/başarılı geçmiş işi ve bir terminal hata işi içerir; hazır hata satırı yalnız görüntüleme kanıtıdır. Eşzamanlı işçinin gerçekten hata üretmesi ayrı [PostgreSQL testleriyle](backend-report.md) kanıtlandı.
   **AÇIK**
   M5 49→50, silmeyle yer açma, eşzamanlı tamamlama ve gerçek örnek ekleme bu tarayıcı koşumunda yapılmadı; otomatik gerçek PostgreSQL ve frontend testlerinde kapsandı.
   M6 Kalıcı `03-profile-capacity.mjs` giriş noktası kabul edilmiş paket eksikliğinden çalışmadı; CUA sonuçları bu dosyanın yürütüldüğü anlamına gelmez.
   **YAN-ETKİ**
   M7 Ayrı yerel tenant, sıradan yazma rolü/hesabı, sentetik profil/örnek/iş kayıtları ve bir sessiz WAV test kaynağı oluşturuldu; önceki kişi profilleri kullanılmadı. Fikstür ve hesap tekrar test için tutuldu, kimlik bilgileri Git dışındaki `outputs/speaker-capacity/live-fixture.json` içindedir.
   M8 Windows backend, worker ve frontend süreçleri mevcut `scripts/stack.sh restart` ile güncellendi; Spark modeli veya imajı değiştirilmedi. Test hesabından çıkış yapıldı.
