# Koşum raporu — 2026-09-10 · Konuşmacı kapasitesi için ilk kırmızı sınır testleri.

1. Sonuç: Eksik kapasite sözleşmesi ve kabul kontrolü gözlendi — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; 11 başarısız, 37 seçilmedi; karar bekleyen: yok.
2. Koşulan: Yerel Docker, Python 3.13, geçici PostgreSQL; `kt-vibecoding-python-web-v2`. `test_speaker_identity.py` → 3 başarısız; `test_speaker_pilot.py` → 8 başarısız. [Ham çıktı](backend-red.txt), [JUnit](backend-red.xml), [tam komut ve kaynak kaydı](backend-provenance.json).
3. Maddeler:
   **KUSUR**
   M1 Zorunlu pozitif `max_profiles` alanı yoktu; 50/51 profilde normal kullanıcı ve `super_admin` yeni iş başlatabiliyordu (DÜZELTİLDİ, iki test dosyasındaki `test_profile_capacity_*` korumaları; [yeşil kanıt](backend-report.md)).
   **TUZAK**
   M2 Reddedilmesi beklenen işler eski uygulamada kuyrukta kaldığından sonraki üç işçi testi zincirleme başarısız oldu; eşzamanlılık yeni veritabanında tek başına ayrıca doğrulandı.
   **GÖZLEM** — yok
   **AÇIK**
   M3 Bu ilk kırmızı koşum tek başına üç zincirleme başarısızlığın davranış kanıtı değildir; [ayrı eşzamanlılık koşumu](backend-concurrency-red-report.md) ve yeşil paket bunları ayırır.
   **YAN-ETKİ**
   M4 Yalnız bu koşumun oluşturduğu benzersiz `_test` veritabanına migrasyon ve fikstürler uygulandı; çıkışta veritabanı düşürüldü. Uygulama veritabanına yazılmadı.
