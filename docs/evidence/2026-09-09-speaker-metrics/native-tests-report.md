# Koşum raporu — 2026-09-10 · Kaydedilmiş otomatik test kanıtlarının son doğrulaması

1. Sonuç: 9 Eylül koşumlarının test ettiği ölçüm kaynakları değişmemiş; toplam 270 benzersiz otomatik test başarılı — birim/entegrasyon 270 başarılı / tarayıcı 0 başarılı / atlanan 1 güvenlik ortam kapısı; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`. Model çalıştırılmadan, ağ erişimi kapalı Linux Python 3.13.14 ortamında ölçüm/raporlayıcı/koşucu testleri; ayrıca gerçek PostgreSQL kullanan tam uygulama kapısı. 10 Eylül'de JUnit sayıları, tekrarların alt küme olması ve test edilmiş kaynak hashları doğrulandı; aynı testler yeniden çalıştırılmadı.

   | Paket | Başarılı | Kanıt |
   | --- | ---: | --- |
   | Yeni ölçüm sözleşmeleri | 92 | [Linux JUnit](native-tests.xml), [kırmızı/yeşil geçmişi](metrics-unit-run-report.md) |
   | Mevcut anonim raporlayıcı | 13 | Aynı Linux JUnit; eski çağrı korunuyor. |
   | Mevcut uygulama değerlendirme koşucusu | 59 | Aynı Linux JUnit; toplam 164, atlama/hata yok. |
   | Backend | 85 | [Son kapı JUnit](quality-gate-final-backend.xml); 66 birim, 19 gerçek PostgreSQL testi. |
   | Frontend | 21 | [Son kapı kaydı](quality-gate-final-frontend.json). |
   | Windows tekrarı | 105 | [Windows JUnit](metrics-unit-tests.xml); Linux'taki 92+13'ün alt kümesi, toplama eklenmedi. |

   [Sayısal envanter](test-inventory.json), [Linux komutu](native-tests-result.json),
   [Linux ham çıktısı](native-tests.txt), [son tam kapı](quality-gate-final.txt),
   [son kapı komutu](quality-gate-final-result.json), [kaynak manifesti](scoring-source-manifest.json).

3. Maddeler:

   **KUSUR**
   M1 Yinelenen/uyuşmayan sorgu, değiştirilmiş hazır sayaç ve ayrışan geri dönüş listesi yeni protokolde reddedilir; son koşucu hatası terminal işler bulunsa da skorları boş bırakır. Koruma: `tests/test_public_speaker_metrics.py`.

   **TUZAK**
   M2 İki uygulama kapısı ve Windows/Linux tekrarları bağımsız yeni test sayısı değildir. İlk süreç ortamı/yazdırma hataları [kapı raporunda](quality-gate-report.md) korunur; başarılı son kapı bunları sessizce silmez.

   **GÖZLEM**
   M3 Yeni ölçüm kaynaklarının dört hashı, kayıtlı kaynak manifestiyle eşleşiyor. 164 kök test, 85 backend ve 21 frontend dışında önceki görevlerin test sayıları bu rapora eklenmedi.

   **AÇIK**
   M4 [Güvenlik kapısı](security-report.md) gerekli çevrimdışı tarayıcı bulunamadığı için çalışmadı. Arayüz değişmedi; bu ölçüm değişikliğinde yeni tarayıcı veya canlı model deneyi yapılmadı. Tam ürün L1/L2 kabulü iddia edilmez.

   **YAN-ETKİ**
   M5 Testler yalnız geçici test veritabanını ve test çıktısını kullandı; yeni kalıcı değerlendirme kaydı veya ses üretilmedi. Bu son kontrolde envanter ve rapor eklendi.
