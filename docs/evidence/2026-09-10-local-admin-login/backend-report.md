# Koşum raporu — 2026-09-10 · Yerel Admin girişinin backend sınırları.

1. Sonuç: Son tam backend kapısı geçti — birim/entegrasyon 153 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows Python 3.13 sanal ortamında gerçek FastAPI ASGI uygulaması; statik kapı mevcut Linux backend konteynerindeki kanonik işlevle, PostgreSQL testleri ana ajanın tam kalite kapısındaki ayrı `_test` veritabanıyla çalıştı.

   | Koşum | Gözlenen sonuç | Kanıt |
   | --- | --- | --- |
   | Yeni config/Host/Origin/HTTP sözleşmesi, kırmızı | 32 başarısız, 0 başarılı | [JUnit](backend-red.xml), [çıktı](backend-red.txt) |
   | Yeni config/Host/Origin/HTTP sözleşmesi, yeşil | 32 başarılı; aşağıdaki 54'e dahildir | [JUnit](backend-focused-green.xml), [çıktı](backend-focused-green.txt) |
   | Tipli 404/503 OpenAPI sözleşmesi, kırmızı | 1 başarısız; 32 test bu dar seçimde koşulmadı | [JUnit](backend-error-contract-red.xml), [çıktı](backend-error-contract-red.txt) |
   | Yeni sınırlar ve hata sözleşmesi + mevcut API/JWT/parola/RBAC | 54 başarılı, 0 atlama | [JUnit](backend-auth-green.xml), [çıktı](backend-auth-green.txt) |
   | İlk tam backend kapısı | 152 başarılı/1 test ayarı izolasyon hatası; yeni PostgreSQL vakalarının 16/16'sı başarılı | [JUnit](quality-gate-first-backend.xml) |
   | Son tam kalite kapısı | Backend 153 başarılı/0 başarısız/0 atlama; yeni PostgreSQL 16/16 bu toplamın içindedir. Frontend 59 başarılı | [Backend JUnit](quality-gate-backend.xml), [frontend](quality-gate-frontend.json), [tam çıktı](quality-gate-final.txt) |
   | Kanonik `backend_static` | Ruff/Black/isort başarılı; 71 dosya biçimi, 55 kaynakta mypy başarılı | [Çıktı](backend-static.txt) |

   Odaklı komut: `app/backend/.venv/Scripts/python.exe -m pytest -q app/backend/tests/unit/test_local_admin_login.py app/backend/tests/unit/test_api_baseline.py app/backend/tests/unit/test_security.py app/backend/tests/unit/test_rbac.py --junitxml=docs/evidence/2026-09-10-local-admin-login/backend-auth-green.xml`; `PYTHONPATH` backend dizinini gösterdi. Kırmızı koşum yalnız yeni test dosyasını kullandı.

   Statik kontrol, `scripts/quality-gate.sh` dosyasının ilk `run_step configuration validate_configuration` çağrısından önceki işlevlerini alan sistem geçici dizinindeki `voiceup-local-admin-backend-static.sh` ile yalnız `backend_static` çağırdı. Git Bash'te `outputs/local-tools` PATH başında ve `MSYS2_ARG_CONV_EXCL=/tmp;/workspace` kullanıldı; geçici Linux kopyasındaki standart dosya izinleri kapının mevcut davranışıdır.

3. Maddeler:

   **KUSUR**
   M1 Varsayılan kapalı/dev-only config, güvenli yerel istek denetimi, options/yerel giriş, tek etkin home-tenant yöneticisi seçimi ve mevcut JWT yanıtının paylaşılması eklendi (DÜZELTİLDİ, yeni birim ve PostgreSQL testleri).
   **TUZAK**
   M2 İlk yeşil denemede 31 başarılı/1 test-fixture hatası görüldü; FastAPI variadic ayar yardımcısını query bağımlılığı saydı. Parametresiz dependency override ile düzeltildi.
   M3 Doğrudan Windows Ruff çalışma dizini import sınıflandırmasını değiştirdi; isort sırası korunup kanonik izole kapı kullanıldı. Regex tam sabit adı ve Black biçimi düzeltildikten sonra kapı geçti.
   M4 İlk tam kapıdaki tek hata Compose kullanıcı adının test varsayılanına sızmasıydı; conftest bayrağı ve kullanıcı adını sıfırlar. İki ayarın da dolu olduğu proses ortamıyla 54 kontrol tekrar geçti; çalışma ayarları korunur.
   **GÖZLEM**
   M5 Parola girişi, JWT imza/süre/issuer/audience, `/me`, merkezi RBAC ve tenant davranışları korunur. Yeni yollar istemciden hesap seçimi/parola almaz; yanıtları `no-store` taşır.
   M6 Ana ajanın son tam kalite kapısındaki 153 test ve yeni 16 PostgreSQL vakasının tamamı geçti; ayrı `_test` veritabanı kapı tarafından kaldırıldı. Bu rapor canlı tarayıcı veya Mac cihaz kabulü iddiası taşımaz.
   **AÇIK** — yok
   **YAN-ETKİ**
   M7 Backend kaynakları, örnek ayarlar ve testler yazıldı; üç PowerShell metin kaydının UTF-16 kodlaması içerik korunarak UTF-8'e çevrildi. Uygulama verisi, sır dosyaları ve servisler değiştirilmedi.
