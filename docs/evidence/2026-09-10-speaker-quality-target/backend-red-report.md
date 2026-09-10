# Koşum raporu — 2026-09-10 · Profil kotasının kaldırılması için kırmızı sözleşme ve işçi testleri.

1. Sonuç: Önceki kota, yeni kabul edilen davranışı 12 vakada engelledi — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; 12 başarısız, 37 seçilmedi; karar bekleyen: yok.
2. Koşulan: Yerel Docker/Git Bash, Python 3.13, migrasyon uygulanmış geçici PostgreSQL; `kt-vibecoding-python-web-v2`. `test_speaker_identity.py` → 3 başarısız, `test_speaker_pilot.py` → 9 başarısız. [Ham çıktı](backend-red.txt), [JUnit](backend-red.xml), [tam komut ve kaynak kaydı](backend-provenance.json).
3. Maddeler:
   **KUSUR**
   M1 Eski kota 50/200 profilden sonra HTTP 409 üretiyor, 49+2 eşzamanlı işin birini reddediyor ve kaldırılmış olması gereken `max_profiles` alanını zorunlu tutuyordu (DÜZELTİLDİ, [yeşil rapor](backend-report.md)).
   M2 Tarihsel `profile_limit` mesajı sınırın hâlen geçerli olduğunu söylüyordu; yeni mesaj geçmiş kuralı ve yeni kayıt seçeneğini açıklar (DÜZELTİLDİ, `test_historical_profile_limit_remains_terminal_and_allows_new_job`).
   **TUZAK**
   M3 Decision 11 önceki kota gereksinimini açıkça geçersiz kıldı; yalnız ona bağlı test beklentileri güncellendi. Önceki kapasite kanıtı değiştirilmedi.
   **GÖZLEM** — yok
   **AÇIK** — yok
   **YAN-ETKİ**
   M4 Yalnız bu koşum için oluşturulan benzersiz `_test` veritabanına migrasyon ve fikstürler yazıldı; başarısız koşum çıkışında veritabanı düşürüldü. Uygulama veritabanına yazılmadı.
