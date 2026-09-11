# Koşum raporu — 2026-09-11 · Toplantı kümesi ile kalıcı profilin ses temsilini ayırma

1. Sonuç: Ayrı 256 boyutlu toplantı takibi gerçek veritabanında doğrulandı — birim 34 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Linux Python 3.13, geçici PostgreSQL, gerçek HTTP/disk ve tipli sağlayıcı dublörü.

   | Süit | Son koşum |
   |---|---:|
   | `tests/integration/test_meeting_tracking.py` | 5 başarılı |
   | `tests/integration/test_meeting_worker.py` | 9 başarılı |
   | `tests/integration/test_meeting_cleanup.py` | 7 başarılı |
   | `tests/unit/test_meeting_identity.py` | 13 başarılı |

   Son çıktı: `outputs/2026-09-10-meeting-delivery/tracking-worker-green-v2.txt`.
   Şema, boyut ve davranış RED çıktıları aynı klasörde `tracking-*-red.txt` olarak korundu.

3. Maddeler:

   **KUSUR**
   M1 Kalıcı profil için uygun bulunmayan kısa parçalar artık ayrı model/sürüm kimlikli 256 boyutlu temsille aynı toplantı kümesine bağlanabiliyor; bu durum sıfır saniyelik kalıcı kanıtı artırmıyor.
   M2 192 ve 256 boyutlu vektörleri karşılaştırma veya kesme reddediliyor; eşzamanlı konuşma dışlaması ve kesin kişi sayısını zorlamama regresyonları geçti.

   **TUZAK**
   M3 Kişi sayısı uyuşmazlığı tamamlanan sonuçta hesaplanır; ilk GREEN denemesinin testi hâlâ çalışan işte bu alanı bekliyordu ve 33 başarılı/1 başarısız oldu; test işi tamamlayarak doğru sınırı denetliyor.

   **GÖZLEM**
   M4 Alembic `f43fd9e32042` üç nullable sütun ve nüfus kimliği kısıtı ekler; yerel uygulamaya okuyucular yeniden başlatılmadan önce uygulandı. Her ayrı test veritabanı düşürüldü.
   M5 Sonuç saklama süresi sonunda yeni takip vektörü ve sürüm bilgileri de siliniyor; profil örneği yaşam döngüsü bağımsız kalıyor.

   **AÇIK**
   M6 Bu testler gerçek modellerle 5→5→6 kabulünü veya 50 kişi doğruluğunu kanıtlamaz; gerçek ses protokolü ve tam kapı yeniden çalıştırılacak.

   **YAN-ETKİ**
   M7 Şema, ek migrasyon, özel takip alanlarının tüketimi, temizlik ve regresyonlar değişti; genel API'ye vektör alanı eklenmedi.
