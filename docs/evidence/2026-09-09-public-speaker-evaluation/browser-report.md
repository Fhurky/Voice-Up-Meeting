# Koşum raporu — 2026-09-09 · Gerçek arayüz ve yetkilendirme

1. Sonuç: Gerçek uygulamada 16 tarayıcı akışı ve 7 HTTP yetkilendirme kontrolü geçti — birim 0 başarılı / tarayıcı 16 başarılı / atlanan 1; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows, CUA tarayıcısı, `http://127.0.0.1:8081`, PostgreSQL ve Ethernet üzerinden Spark CUDA modeli. Hesaplara gerçek giriş formuyla girildi. Model eşiği son akışta `0.55 / 0.45 / 0.10` olarak görüldü.

   | Akış | Gözlenen sonuç |
   | --- | --- |
   | 1. Korumalı rota ve giriş | Oturumsuz erişim giriş sayfasına yönlendi; ayrı test hesabıyla giriş başarılı. |
   | 2. Türkçe analiz | Tek konuşmacı kapsamı ve yükleme sınırları görünür. |
   | 3. İngilizce analiz | Başlık, açıklamalar ve dil geçişi görünür. |
   | 4. Bozuk WAV | Çözülebilirlik hatası gösterildi; iş oluşturulmadı. |
   | 5. Sessiz WAV | İş kalıcı olarak başarısız; kullanılabilir konuşma hatası gösterildi. |
   | 6. Başarısız işi yenileme | Aynı iş durumu korundu, profil oluşturulmadı. |
   | 7. Salt okuma hesabı, Türkçe | Yükleme, ad değiştirme ve silme eylemleri bulunmuyor. |
   | 8. Salt okuma hesabı, İngilizce | Yetki açıklamaları görünür; yenilemede yetkiler korunuyor. |
   | 9. Gerçek sesle kayıt | Kalibrasyon kaydından bir profil oluşturuldu. |
   | 10. Ayrı kaynak bölümünden tanıma | Aynı kişi doğru profile bağlandı, benzerlik yaklaşık `0.833`. |
   | 11. Bilinmeyen kişi | Bilinmeyen sonucu, otomatik profil oluşturulmadı. |
   | 12. Yanlış kişiyi profile ekleme | `target_mismatch`; örnek sayısı değişmedi. |
   | 13. Profil adı değiştirme | Yeni ad yenilemeden sonra korundu. |
   | 14. Doğru kişiyi profile ekleme | Aynı profil iki örneğe ulaştı. |
   | 15. Yeni eşikle üçüncü kayıt | Doğru profil, benzerlik yaklaşık `0.869`; cihaz `cuda:0`, kabul `0.55`, bilinmeyen `0.45`, aday farkı `0.1`. |
   | 16. Tarayıcı günlükleri | Son akışta hata ve uyarı kaydı sıfır. |
   | HTTP sözleşmeleri | [7/7 kontrol](live-authorization.json): yetkisiz yükleme, başka tenant işi, eksik/geçersiz tenant, oturumsuz erişim, yetkisiz tenant değiştirme, eksik tekrar anahtarı. |
   | Kalıcı Playwright giriş noktası | `scripts/e2e.sh speaker-identity` exit 2; [çıktı](permanent-browser.txt). |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Arayüzün tanıma puanı doğruluk yüzdesi değildir. Kalite hatası ve bilinmeyen sonuç ayrı gösterildi; bu akışlar nüfus doğruluğu ölçümü değildir.

   **GÖZLEM**

   M2 Tarayıcı yalnız kalibrasyon seslerini kullandı; ayrı test kişilerinin verileri eşik seçiminde kullanılmadı. Kullanıcı profili ayrı [karşılaştırmada](user-data-preservation.json) değişmedi.

   **AÇIK**

   M3 Kalıcı Playwright koşumu için onaylı çevrimdışı paket yok; CUA kanıtı bu eksikliği kapatmaz. Bu koşumda silme tekrarlanmadı; önceki pilot akışları ve PostgreSQL entegrasyon testleri ayrı kanıttır.

   **YAN-ETKİ**

   M4 Ayrı tarayıcı test hesabında bir profil, iki ses örneği ve iş kayıtları bırakıldı. Bozuk/sessiz sesler ve kimlik bilgileri Git dışındaki `outputs/public-speaker-evaluation/` içindedir.
