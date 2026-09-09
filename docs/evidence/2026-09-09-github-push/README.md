# Koşum raporu — 2026-09-09 · GitHub gönderimi öncesi kaynak kontrolü

1. Sonuç: Gönderim kapsamı ve sır dışlama kontrolleri geçti; iki ortam kapısı tamamlanamadı — doğrulama 7 başarılı / birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Kapsam | Ortam ve gözlenen sonuç |
   | --- | --- |
   | GitHub erişimi | Yetkili token yalnız alt süreç ortamında kullanıldı; hesap Fhurky, hedef özel depo Fhurky/Voice-Up-Meeting, yazma izni var. Token çıktıya veya remote URL'ye yazılmadı. |
   | Uzak geçmiş | `origin/main` başlangıç commit'i `9d6ef08181734ba20e0dac1f8accdf46fbd402b7`; yalnız başlangıç README'si vardı. Yerel dal bu geçmiş üzerine kuruldu, çalışma dosyaları korundu. |
   | Commit kapsamı | Git indeksindeki gerçek bloblar; yerel sırlarla birebir karşılaştırma ve sınırlı anahtar/token kalıpları, yasak yerel dosyalar, boyut ve çalışma bitleri. Yedi kontrol geçti. [İlk indeks anlık görüntüsü](staged-check.json); bu rapor dosyaları eklendikten sonra son indeks tekrar kontrol edilir. |
   | Tam kalite kapısı | `kt-vibecoding-python-web-v2`; `scripts/quality-gate.sh all`. Config/bağımlılık/config-sync geçti; Docker Desktop Linux engine kapalı olduğundan test veritabanı oluşturma exit 1 ile durdu. Veritabanı yaratılmadı. [Ham çıktı](quality-gate.txt). |
   | Güvenlik kapısı | `scripts/security-gate.sh`; yerel gitleaks bulunmadığından exit 2. [Ham çıktı](security-gate.txt). |
   | Önceki uygulama kanıtı | Son başarılı kaynak doğrulaması [veri hazırlık raporunda](../2026-09-09-dataset-readiness/README.md): 59 backend + 21 frontend; ayrı referans paketi 256 test. Bunlar yeni test koşumu sayılmadı. |

3. Maddeler:

   **KUSUR**

   M1 Windows ilk indeksinde kabuk betiklerinin çalıştırma bitleri eksikti; doğrudan kullanılabilmeleri için 32 `.sh` dosyası Git'te `100755` kaydedildi, LF kuralı korundu.

   M2 Genel `*.log` kuralı üç doğrulama kanıtını dışlıyordu; yalnız bu üç incelenmiş inference kanıtına açık istisna eklendi ve indeks sır taramasına dahil edildi.

   **TUZAK**

   M3 Özel anahtar kalıbı tek bir test dosyasında yalnız başlık literalini buldu; gövdesiz negatif fixture olduğu AST ile doğrulandı. Gerçek anahtar olarak işaretlenmedi, geniş bir tarama istisnası eklenmedi.

   M4 Git kodu eşitler; `.env`, modeller, sesler, yerel kullanıcı bilgileri ve PostgreSQL/volume verisi eşitlenmez. İkinci bilgisayarın kurulum önkoşulları [Git rehberinde](../../GIT_WORKFLOW.md).

   **GÖZLEM**

   M5 Token bellekteki GH_TOKEN ile GitHub'a verildi; remote yalnız normal HTTPS adresi içerir. Uygulama kaynak davranışı veya paket sürümleri bu gönderim hazırlığında değiştirilmedi.

   M6 Tarihsel kanıt dosyalarının bazıları yerel kullanıcı yolu ve makine adı içerir; özel depoda özgün ölçüm kaydı olarak korunur. Bunlar başka bilgisayardaki runtime ayarı değildir.

   **AÇIK**

   M7 Docker kapalı olduğundan bu tur tam uygulama testleri çalışmadı; gitleaks ve kabul edilmiş güvenlik tarayıcı ortamı yok. Sınırlı sır kontrolü tam güvenlik kapısının yerine geçmez.

   M8 Yeni bilgisayar kurulumu, gerçek kullanıcı sesleriyle doğruluk ve Spark uyumluluğu bu Git aktarımında sınanmadı; ilgili ürün kabul maddeleri açık kalır.

   **YAN-ETKİ**

   M9 Kullanıcının açık gönderim isteği kapsamında origin eklendi, mevcut uzak geçmiş korundu, dosyalar commit için seçildi; Git rehberi, README bağlantısı, üç log istisnası, çalıştırma bitleri ve bu rapor eklendi. Token/ses/veritabanı/model dosyaları kapsam dışında tutuldu.
