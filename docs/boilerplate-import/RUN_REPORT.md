# Koşum raporu — 2026-09-08 · Boilerplate aktarımı ve mevcut ses çekirdeği

1. Sonuç: Kopya ve statik kontroller başarılı; tam platform kapısı ortam nedeniyle başarısız — birim 208 başarılı / tarayıcı 0 başarılı / atlanan 0 pytest testi; karar bekleyen: yok.
2. Koşulan: Windows, yerel · doğrulama. Scaffold oluşturucusu Python 3.13.14 / kt-scaffold 0.3.0; mevcut ses testleri Python 3.12.10.

   | Komut veya kontrol | Gözlenen sonuç |
   | --- | --- |
   | Kaynak dosya SHA-256 karşılaştırması | 496/496 eşit |
   | Üretilen dosya SHA-256 karşılaştırması | 386/386 eşit; README ve .gitignore bilinçli uyarlama |
   | `kt-scaffold init` | Exit 0; 388 dosya; uyarı yok |
   | `tools/boilerplate/.venv/Scripts/python.exe scripts/check-governance-drift.py` | Exit 0; 93 yönerge + 4 inert agent dosyası güncel |
   | `tools/boilerplate/.venv/Scripts/python.exe scripts/check-config-sync.py` | Exit 0; 40 kaynak dosyası ve 16 tipli ayar kontrolü |
   | `tools/boilerplate/.venv/Scripts/python.exe scripts/check-dependency-admission.py` | Exit 0; 72 bağımlılık koordinatı; scaffold kabul envanteri değişmedi |
   | `uv run --no-sync pytest` | Exit 0; 208/208 başarılı, 0 atlanan; ses çekirdeği testleri |
   | Git Bash ile `scripts/quality-gate.sh all` | Exit 1; Docker Linux daemon bağlantısı yok; migrasyon adımında durdu |
   | `docker info` | Exit 1; `dockerDesktopLinuxEngine` named pipe bulunamadı |

3. Maddeler:

   **KUSUR**

   M1 Sağlanan kalite betiği Docker hatalarına rağmen `database-test-create` için başarılı marker üretti; veritabanı oluşturuldu kabul edilmedi. Betik bu aktarımda değiştirilmedi; owning template `tools/boilerplate/src/kt_scaffold/templates/common/scripts/quality-gate.sh`.

   **TUZAK**

   M2 Kök CPU PyTorch kilidi Spark CUDA kurulumu değildir; Python 3.13 Alpine web image'ına GPU bağımlılıkları eklenmemeli.
   M3 Önceki kapsamsız `models/` ignore kuralı `/models/` olarak düzeltildi; ürün domain modelleri Git'te görünür.

   **GÖZLEM**

   M4 Kaynak ve scaffold envanterleri hashleriyle korundu; gerçek model doğruluğu ve önceki örnek sonucu [VALIDATION.md](../VALIDATION.md) içinde değişmeden duruyor.
   M5 Agent Platform çıktıları inert kaldı; runtime conformance veya owner admission iddia edilmedi.

   **AÇIK**

   M6 Tam kapının PostgreSQL, migrasyon, backend/frontend, sözleşme, Helm ve browser sonuçları yok; Docker daemon erişilemedi, Helm de mevcut PATH'te bulunamadı.
   M7 Gerçek Spark kurulumu, model çıkarımı ve hız/doğruluk deneyleri yapılmadı; ses motoru platforma henüz bağlanmadı.

   **YAN-ETKİ**

   M8 496 kaynak ve 388 üretilen dosya aktarıldı; iki çakışan dosya yedeklendi/birleştirildi. Oluşturucu için ayrı yerel Python 3.13 sanal ortamı kuruldu; mevcut ses ortamı korundu.
