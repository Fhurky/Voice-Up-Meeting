# Koşum raporu — 2026-09-09 · Gerçek arayüzde korumalı konuşma kurtarma

1. Sonuç: Yeni sürümün kullanıcı akışları gözlendi — birim 0 başarılı / tarayıcı 11 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows uygulama içi tarayıcı, gerçek React/FastAPI/PostgreSQL ve Ethernet üzerinden Spark CUDA; sabit `kt-vibecoding-python-web-v2`.

   | Akış | Gözlenen sonuç |
   | --- | --- |
   | Ayrı hesapla giriş ve boş galeri | Giriş başarılı, başlangıçta sıfır profil. |
   | Gerçek kalibrasyon sesiyle kayıt | Bir profil ve bir doğrulanmış örnek; 12,116 saniye, üç pencere. |
   | Önceden yetersiz sayılan farklı kayıt | Beklenen kişi tanındı; kosinüs 0,839, 9,552 saniye, iki pencere. |
   | Bekleyen işi sayfa yenilemeyle açma | Aynı iş adresi korundu ve terminal sonuç gösterildi. |
   | Kayıtlı olmayan kişinin sesi | Bilinmeyen olarak döndü; yeni profil oluşmadı. |
   | Tanıma sonrası galeri | Bir profil/bir örnek korundu. |
   | Yanlış kişiye ait örneği mevcut profile ekleme | Eşleşme reddedildi; profil değiştirilmedi mesajı gösterildi. |
   | Sekiz saniye sessizlik | Yetersiz kullanılabilir konuşma gerekçesi gösterildi. |
   | İki negatif işlem sonrası galeri | Bir profil/bir örnek korundu. |
   | Çıkış | Giriş ekranına dönüldü. |

   İlk satır iki ayrı akışı içerir; toplam 11. [Makine kaydı](browser-observations.json), [görsel](browser-recognized.png), [API doğrulaması](browser-api-initial-report.md). Ham iş adresleri ve ekran metinleri yalnız Git dışındaki özel çıktıda tutuldu.

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**
   M1 Sesler kalibrasyon grubundan seçildi; bu kullanıcı arayüzü kanıtı bağımsız doğruluk testi değildir.

   **GÖZLEM**
   M2 API, kayıt için `vad-windows-v1`, kurtarılan tanıma ve bilinmeyen sorgu için `vad-packed-fallback-v1` döndürdü; vektörler arayüze çıkmadı.

   **AÇIK**
   M3 Kalıcı Playwright kapısı onaylı çevrimdışı paket olmadığı için çalışmadı; gerçek tarayıcı gözlemleri bu kapının yerine geçirilmedi.

   **YAN-ETKİ**
   M4 Ayrı test hesabında beş ses yüklemesi, beş iş ve tek örnekli bir profil bırakıldı; test hesabından çıkış yapıldı. Kullanıcının profili bu akışlarda kullanılmadı.
