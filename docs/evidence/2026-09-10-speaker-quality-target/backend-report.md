# Koşum raporu — 2026-09-10 · Profil kotasının kaldırılması ve mevcut güvence sınırlarının doğrulanması.

1. Sonuç: 49 test ve altı statik/sözleşme kontrolü geçti — birim 22 başarılı / tarayıcı 0 başarılı / atlanan 0; gerçek PostgreSQL 27 başarılı; karar bekleyen: yok.
2. Koşulan: Yerel Docker/Git Bash, Python 3.13, migrasyon uygulanmış geçici PostgreSQL; `kt-vibecoding-python-web-v2`. [Ham çıktı](backend-green.txt), [JUnit](backend-green.xml), [tam komutlar ve kaynak hashleri](backend-provenance.json).

   | Paket | Dosya veya kontrol | Başarılı |
   | --- | --- | ---: |
   | Birim | `app/backend/tests/unit/test_speaker_identity.py` | 22 |
   | Gerçek HTTP/PostgreSQL/işçi | `app/backend/tests/integration/test_speaker_pilot.py` | 27 |
   | Statik ve üretilmiş sözleşme | Ruff, Black, isort, mypy, OpenAPI farkı, frontend tip farkı | 6 |

   Black 67 Python dosyasını, mypy 54 uygulama kaynak dosyasını denetledi. Paket,
   Decision 11 için 12 hedeflenmiş vaka ile 37 önceki vakayı birlikte çalıştırdı.

3. Maddeler:
   **KUSUR**
   M1 Yanlış yorumlanan ürün kotası kaldırıldı: normal kullanıcı ve `super_admin` ile 50→51 ve 200→201 kayıtları başarılı; eşzamanlı 49+2 iş iki farklı profil ve yalnız iki örnek oluşturdu.
   M2 `max_profiles` API ve üretilmiş tiplerden kaldırıldı. Tarihsel kapasite hatası aynı işte terminal kalır; aynı anahtar eski işi döndürür, yeni anahtarla kayıt başarılıdır.
   **TUZAK**
   M3 Bu testler sayıya bağlı engelin kalktığını kanıtlar; 50/200 gerçek kişinin tanınma doğruluğu veya gecikme garantisi değildir. Çıkarım vektörleri teknik fikstürdür.
   **GÖZLEM**
   M4 Tenant/model ayrımı, sayfalı toplam, mantıksal silme, mevcut profile ekleme, 20 örnek sınırı, aynı işin yinelenmemesi ve eski işçi sahiplenmesinin reddi korunmuştur.
   **AÇIK**
   M5 Tam profil kapısı, canlı tarayıcı ve güvenlik ortamı bu odaklı paketin dışındadır; ana teslim kanıtında ayrıca izlenir.
   **YAN-ETKİ**
   M6 Koşuma özel yeni `_test` veritabanı oluşturulup düşürüldü; uygulama veritabanına yazılmadı. OpenAPI ve frontend tipleri mevcut betiklerle yeniden üretildi; şema, migrasyon, ayar ve model değiştirilmedi.
