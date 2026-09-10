# Koşum raporu — 2026-09-10 · GitHub paylaşımı öncesi kaynak ve gizli dosya kontrolü

1. Sonuç: Kaynak paylaşımını engelleyen içerik bulunmadı — birim 0 başarılı /
   tarayıcı 0 başarılı / 115 dosya incelendi / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows, Git; `kt-vibecoding-python-web-v2`. Önceki uygulama testleri
   [ana rapordadır](README.md); bu koşumda tekrar çalıştırılmadı.

   | Kontrol | Gözlenen sonuç |
   | --- | --- |
   | Bağımsız yayın incelemesi | 115 aday dosya, yaklaşık 1,04 MB; gerçek sır, ham ses, model, veritabanı veya embedding dizisi bulunmadı. |
   | Kaynak/bağımlılık bağları | Git'in yayımlayacağı içerik üzerinden 45 SHA-256 bağı kontrol edildi. |
   | `scripts/check-dependency-admission.py` | 143 koordinat, kayıtlı envanterle aynı. |
   | `git ls-remote --heads origin refs/heads/main` | Uzak dal işlem öncesi yerel `3ddba94` ile aynı; token kalıcı Git ayarına yazılmadı. |
   | `git diff --cached --check` | Çıkış 2: 21 ham test çıktı dosyasında 157 satır sonu boşluk uyarısı. |
   | Kaynak ve biçimli belgelerin staged diff kontrolü | Yalnız yukarıdaki ham `.txt`/`.xml` çıktılar dışarıda tutularak çıkış 0; tüm dosyalar için başarı iddiası değildir. |

3. Maddeler:

   **KUSUR**

   M1 Bir artifact inceleme JSON'unun Windows satır sonları Git'te değişerek hash
   bağını bozuyordu; LF'ye çevrildi, JSON içeriği aynı kaldı ve bağ yenilendi.

   **TUZAK**

   M2 Ham test çıktılarındaki boşluklar korunmuştur; bu metinler kaynak biçim
   kontrolünden ayrı raporlanır, test sonuçları yeniden yazılmaz.

   **GÖZLEM**

   M3 CUDA varsayılanları ve Spark imaj/paket/Compose/SSH kaynakları korunur;
   CPU modu açık seçimdir. Gerçek `.env`, sesler, modeller ve veriler Git dışındadır.

   **AÇIK**

   M4 Fiziksel Mac, Gitleaks, PowerShell 7 ve QEMU kanıt sınırları ana raporda
   korunur; dar yayın incelemesi güvenlik taraması yerine geçmez.

   **YAN-ETKİ**

   M5 Dört değişen kaynak/belge ve bir inceleme JSON'u Git'in LF biçimine alındı;
   ilgili kaynak hashleri güncellendi, yayın raporu eklendi ve dosyalar stage edildi.
