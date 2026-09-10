# Koşum raporu — 2026-09-09 · Sabit uygulama profilinin tam kalite kapısı

1. Sonuç: Tam uygulama kalite kapısı geçti — birim/entegrasyon 106 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows / Git Bash ve yerel Docker, `kt-vibecoding-python-web-v2`, `scripts/quality-gate.sh all`; başarılı komut çıkışı 0 ve süre 63,593 saniye. [Ham çıktı](quality-gate-retry.txt), [komut kaydı](quality-gate-retry-result.json), [85 backend testi](quality-gate-backend.xml), [21 frontend testi](quality-gate-frontend.json).

   Ölçüm kodu dondurulduktan sonraki son kapı da 9 Eylül'de çıkış 0 ile geçti:
   [60,719 saniyelik komut kaydı](quality-gate-final-result.json), [ham çıktı](quality-gate-final.txt),
   [85 backend testi](quality-gate-final-backend.xml), [21 frontend testi](quality-gate-final-frontend.json).
   Bu tekrar toplam test sayısını artırmaz; 10 Eylül son incelemesinde mevcut kanıt olarak doğrulandı.
3. Maddeler:

   **KUSUR** — yok

   **TUZAK**
   M1 İlk deneme, bu koşumun süreç ortamında bütün MSYS yol dönüşümleri kapatıldığı için `C:\c\Users\...` hatasıyla bağımlılık kontrolünde durdu; [ilk çıktı](quality-gate.txt) korundu. Dönüşüm istisnası yalnız kapsayıcı yollarına daraltılınca kapı geçti; depo betiği değiştirilmedi.
   M2 Başarılı ikinci komutun kayıtları UTF-8 dosyalara tam yazıldı; yalnız en sondaki konsol özetini yazdıran sarmalayıcı CP1254 onay işareti kodlamasında hata verdi. Kapının gerçek çıkışı 0'dır; sarmalayıcı hatası ayrı tutuldu.

   **GÖZLEM**
   M3 Benzersiz `_test` veritabanı oluşturuldu, migrasyon ve gerçek PostgreSQL testleri çalıştı, sonunda düşürüldü. Yapılandırma, lint/biçim/tip, migrasyon, OpenAPI, frontend derleme/tip ve yönetişim/chart kapıları geçti.

   **AÇIK**
   M4 Bu kapı kökteki yeni ölçüm testlerini veya güvenlik tarayıcılarını kapsamaz; bunların kanıtları ayrıdır. Arayüz davranışı değişmediği için yeni canlı tarayıcı koşumu yapılmadı.

   **YAN-ETKİ**
   M5 Yalnız geçici test veritabanı ve kanıt dosyaları üretildi; uygulama veritabanına migrasyon uygulanmadı, Spark modeli çalıştırılmadı.
