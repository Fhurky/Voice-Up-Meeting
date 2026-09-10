# Koşum raporu — 2026-09-10 · Yerel yönetici girişinin Compose ayarları ve kurulum belgeleri.

1. Sonuç: Sekiz yeni Compose sözleşmesi ve yapılandırma eşleştirmesi geçti; mevcut başlatıcı regresyonu eksik PowerShell 7 nedeniyle çalıştırılamadı — birim 15 başarılı / tarayıcı 0 başarılı / atlanan 0; başarısız 1; karar bekleyen: yok.
2. Koşulan:

   | Ortam | Komut veya sınır | Gözlenen sonuç |
   | --- | --- | --- |
   | Windows, varsayılan Python 3.12 | İlk `python -m pytest` çağrısı | Pytest kurulu olmadığından test toplanmadı; [çıktı](infra-runner-unavailable.txt). Profilin mevcut Python 3.13 ortamına geçildi. |
   | Windows, CPython 3.13.14 | `app/backend/.venv/Scripts/python.exe -B -m pytest tests/test_local_configuration.py -k real_compose_local_admin -q -p no:cacheprovider -o addopts=` | Kırmızı: 0 başarılı, yeni ayarlar eksik olduğundan 8 başarısız; [JUnit](infra-red.xml), [çıktı](infra-red.txt). |
   | Windows, CPython 3.13.14 ve gerçek Docker Compose yapılandırma çözümleyicisi | `tests/test_local_configuration.py`; CPU katmanının gerçek Compose testi; Spark tüketici ortamı ve yayımlanmayan port testleri | 15 başarılı, 1 çalıştırıcı hatası; yeni sekiz testin tamamı geçti. [JUnit](infra-green.xml), [çıktı](infra-green.txt). |
   | Windows, CPython 3.13.14 | `ruff check` ve `ruff format --check tests/test_local_configuration.py` | Başarılı; [çıktı](infra-lint.txt). |
   | Windows, CPython 3.13.14 | `app/backend/.venv/Scripts/python.exe -B scripts/check-config-sync.py` | Başarılı: 31 tipli ayar, 28 Compose anahtarı, 29 örnek atama, 55 kaynak dosyası ve tek Kubernetes Secret başvurusu; [çıktı](infra-config-sync.txt). |

3. Maddeler:

   **KUSUR**

   M1 DÜZELTİLDİ: Yerel Compose yeni yönetici giriş ayarlarını aktarmıyordu; varsayılan etkinlik, isteğe bağlı kullanıcı adı ve açıkça kapatma dört modda gerçek Compose çözümlemesiyle korunuyor (`tests/test_local_configuration.py`).

   **TUZAK**

   M2 Varsayılan `python` Python 3.12 ve pytest içermiyor; profil koşumu mevcut `app/backend/.venv/Scripts/python.exe` üzerinden Python 3.13.14 ile yapıldı.

   M3 Mevcut başlatıcı testi `pwsh` çağırıyor; bu ortamda yalnız Windows PowerShell bulunduğundan alt süreç oluşturulmadan durdu. Test veya ürün davranışı değiştirilmedi.

   **GÖZLEM**

   M4 Compose testleri geçici örnek `.env` dosyalarını kullandı; çözümlenmiş ortam değerleri çıktıya yazdırılmadı. Çalışan servisler, yerel `.env`, kimlik bilgileri ve model servisi korunmuştur.

   **AÇIK**

   M5 Canlı giriş, tam kalite kapısı ve güvenlik kapısı bu alt görevin koşumunda çalıştırılmadı; ana görev tarafından izleniyor. Mevcut başlatıcı regresyonunun tamamlanması PowerShell 7 gerektiriyor.

   **YAN-ETKİ**

   M6 Yerel Compose, altyapı örnek ayarları, Mac ve NVIDIA/Spark kurulum belgeleri güncellendi; mevcut test dosyasına sekiz Compose vakası eklendi. Geçici test dosyaları yalnız pytest çalışma dizininde oluşturuldu.

Seçili teknoloji profili `kt-vibecoding-python-web-v2`; kabul kaynağı [006 yerel yönetici girişi](../../../specs/speaker-identity/PRDs/006-local-admin-login/PRD.md).
