# Koşum raporu — 2026-09-10 · Son profil yeri için eşzamanlı iki işçinin kırmızı kanıtı.

1. Sonuç: 49 aktif profilde iki işçi de profil oluşturdu ve beklenen koruma başarısız oldu — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; 1 başarısız, 47 seçilmedi; karar bekleyen: yok.
2. Koşulan: Yerel Docker, Python 3.13, yeni geçici PostgreSQL; `kt-vibecoding-python-web-v2`. `test_speaker_pilot.py::test_profile_capacity_serializes_two_workers_for_last_slot` → 1 başarısız. [Ham çıktı](backend-concurrency-red.txt), [JUnit](backend-concurrency-red.xml), [tam komut kaydı](backend-provenance.json).
3. Maddeler:
   **KUSUR**
   M1 İki çıkarım çağrısı aynı bariyerde buluşturuldu; eski uygulama iki işi de `succeeded` yaptı (DÜZELTİLDİ, `SpeakerWorker.complete` içinde kilit altında yeniden sayım; aynı test yeşil pakette geçti).
   **TUZAK** — yok
   **GÖZLEM**
   M2 Gerçek PostgreSQL işlemleri, API ve işçiler kullanıldı; ses vektörleri deterministik teknik fikstürdür, model doğruluğu kanıtı değildir.
   **AÇIK** — yok
   **YAN-ETKİ**
   M3 Koşuma özel yeni `_test` veritabanı ve 49 başlangıç profili oluşturuldu; koşum sonunda yalnız bu veritabanı düşürüldü.
