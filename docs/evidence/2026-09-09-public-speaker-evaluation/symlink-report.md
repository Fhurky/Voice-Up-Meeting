# Koşum raporu — 2026-09-09 · Windows'ta atlanan iki sembolik bağlantı sınırının Linux dosya sisteminde doğrulanması

1. Sonuç: Mevcut iki test gerçek Linux sembolik bağlantılarıyla geçti — birim 2 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve kapsam | Komut / kanıt | Sonuç |
   | --- | --- | --- |
   | Mevcut backend imajı; Linux x86_64, Python 3.13.15 / pytest 9.1.1 | `python -m pytest tests/test_spark_runtime_start.py::test_symlinked_model_is_rejected_before_docker tests/test_spark_wheelhouse.py::test_symlink_target_and_destination_are_rejected -o addopts= -p no:cacheprovider -ra --junitxml=/evidence/symlink-tests.xml` | 2 başarılı / 0 atlanan; 0,68 saniye; çıkış 0 |
   | Sınırlar ve araç kimlikleri | [Çıktı](symlink-tests.txt), [JUnit](symlink-tests.xml), [imaj, araç özetleri ve ortam](symlink-environment.json) | Ağ, GPU, Docker socket ve gerçek kimlik bilgisi bağı yok; kök ve kaynak bağları salt okunur |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**
   M1 Bu koşum Linux dosya sistemi eşdeğeridir; Windows hesabının sembolik bağlantı oluşturma iznini veya Windows işletim sistemi davranışını doğrulamaz. Önceki Windows atlamaları tarihsel kanıtta korunur.
   M2 Model testi mevcut `prepared` fixture'ında gerçek `docker compose config` çalıştırır; Docker CLI yalnız yapılandırma ayrıştırır. Sonraki Docker çağrılarına ulaşılmadığı mevcut testin denetimiyle kanıtlanır.

   **GÖZLEM**
   M3 [Model yolu testi](../../../tests/test_spark_runtime_start.py) sembolik bağlantıyı Docker işlemlerinden önce reddetti; [wheelhouse testi](../../../tests/test_spark_wheelhouse.py) hedef, üst dizin ve dosya bağlantılarını reddederek mevcut hedef içeriğini korudu.
   M4 Docker 29.6.1 ve Compose 5.3.0, zaten kurulu Docker Desktop'ın `docker-wsl-cli.iso` arşivinden alındı. İndirme, paket kurulumu, sürüm/pin değişikliği veya sahte CLI kullanılmadı.

   **AÇIK** — yok

   **YAN-ETKİ**
   M5 Yalnız `symlink-*` kanıtları kalıcıdır. İzole kapsayıcı ve doğrulanmış geçici dizindeki CLI kopyaları kaldırıldı; test fixture'ları kapsayıcının `/tmp` alanında kaldı ve kapsayıcıyla kaldırıldı.
   M6 Test ve kaynak dosyaları değiştirilmedi; çalışan VoiceUp servisleri, Spark modeli, GPU, uygulama verisi ve diğer projeler yeniden başlatılmadı veya değiştirilmedi.
