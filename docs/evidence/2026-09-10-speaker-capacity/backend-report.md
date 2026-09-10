# Koşum raporu — 2026-09-10 · Konuşmacı kapasitesi, işçi ve önceki sözleşmelerin yeşil doğrulaması.

1. Sonuç: 48 test geçti; son yer yalnız bir işe verildi — birim 22 başarılı / tarayıcı 0 başarılı / atlanan 0; gerçek PostgreSQL 26 başarılı; karar bekleyen: yok.
2. Koşulan: Yerel Docker, Python 3.13, migrasyon uygulanmış geçici PostgreSQL; `kt-vibecoding-python-web-v2`. [Ham çıktı](backend-green.txt), [JUnit](backend-green.xml), [tam komut ve kaynak hashleri](backend-provenance.json).

   | Paket | Dosya | Başarılı |
   | --- | --- | ---: |
   | Birim | `app/backend/tests/unit/test_speaker_identity.py` | 22 |
   | Gerçek HTTP/PostgreSQL/işçi | `app/backend/tests/integration/test_speaker_pilot.py` | 26 |

3. Maddeler:
   **KUSUR**
   M1 Eksik 50 profil sınırı düzeltildi; 49→50 kabulü, 51. isteğin reddi, sınırdaki tekrar, `super_admin`, mevcut profile ekleme, tanıma, silmeyle yer açılması ve tenant/model kapsamı testlerle korundu.
   M2 Eşzamanlı son yer testi artık bir başarı ve tek denemede terminal `profile_limit` üretir; toplam 50 profil, yalnız bir yeni örnek ve iki anahtarın değişmeyen tekrarı doğrulandı.
   **TUZAK**
   M3 Kuyruktaki işler yer ayırmaz; son yer başka işte dolarsa kayıt işi çıkarım sonrasında terminal kapasite hatası verir.
   **GÖZLEM**
   M4 Paket 11 yeni kapasite vakası ve 37 önceki vakayı kapsar. Teknik vektör fikstürleri model doğruluğu veya gerçek 50 kişinin tanınma kanıtı değildir.
   **AÇIK**
   M5 Tam profil kapısı, gerçek tarayıcı ve güvenlik taraması bu odaklı koşumun parçası değildir; ana teslim kanıtında ayrıca izlenir.
   **YAN-ETKİ**
   M6 Yalnız bu koşumun oluşturduğu benzersiz `_test` veritabanına migrasyon ve fikstürler yazıldı; başarıdan sonra düşürüldü. Uygulama veritabanına yazılmadı.
