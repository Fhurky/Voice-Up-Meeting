# Koşum raporu — 2026-09-11 · Atlanan taşıma ve Linux dosya sınırı vakalarının çalıştırılması

1. Sonuç: Seçilen ek gerçek ortam denetimleri geçti — birim/entegrasyon 14 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows/Python 3.12 ve Docker Desktop üzerinde `RUN_DOCKER_TRANSPORT=1 pytest tests/test_spark_transport_config.py` içindeki 13 Docker vakası → 13 başarılı, 57,417 saniye. Mevcut backend imajında Linux/Python 3.13 ile `pytest tests/test_spark_wheelhouse.py::test_symlink_target_and_destination_are_rejected` → 1 başarılı. Her iki gerçek çıkış kodu 0; ham log/XML `outputs/2026-09-11-accuracy-audit/docker-transport.*`, `linux-symlink.*`.
3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 Taşıma testleri geçici ağ/container ve loopback dinleyici kullanır; ana uygulama container'larını yeniden başlatmaz. Aktif model denemesinin galerisine dokunmaz.
   **GÖZLEM**
   M2 13 gerçek Docker denetimi aktif nginx yeniden yüklemesi, değişen upstream adresi, IPv4 kaynak doğrulaması, özel/relay gövde sınırları ve POST tekrar yapılmamasını kapsar; native Spark modeli çalıştırmaz.
   M3 Linux sembolik bağ testi mevcut imaj, salt okunur kaynak bağı, ağsız container ve ayrı geçici dosya sistemiyle çalıştı; hedef dışındaki dosyanın korunduğu doğrulandı.
   **AÇIK**
   M4 Windows'ta atlanan diğer `test_symlinked_model_is_rejected_before_docker` vakası bu ek Linux çağrısında çalıştırılmadı; tüm-kök-paket toplamında bir açık atlama kalır.
   **YAN-ETKİ**
   M5 Testlerin oluşturduğu geçici container/ağlar kendi cleanup akışlarıyla kaldırıldı; kalıcı ortam, model, ana veritabanı ve kaynak dosyaları değişmedi.
