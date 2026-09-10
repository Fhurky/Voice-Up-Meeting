# Koşum raporu — 2026-09-09 · Konuşma kurtarma ve sözleşme kontrolleri

1. Sonuç: Çalıştırılabilen otomatik kontroller geçti — birim 552 başarılı / tarayıcı 0 başarılı / atlanan 2 ortam kapısı; karar bekleyen: yok. Tam L1 kabulü güvenlik kanıtı eksikliği nedeniyle verilmedi.
2. Koşulan: Sabit `kt-vibecoding-python-web-v2`; Linux Python 3.13.14 çıkarım imajı, mevcut Linux backend/PostgreSQL ve React/Vite; Windows veri hazırlama testleri.

   | Paket | Kanıt ve sayım |
   | --- | --- |
   | Çıkarım HTTP ve gerçek PCM sınırları | [96 başarılı](inference-green.xml); [çıktı](inference-green.txt). Bunun 27'si yeni kısa parça/karışım korumasıdır. |
   | Referans ve veri araçları | Linux'ta [349 başarılı, bir platform atlaması](reference-and-evaluation.xml); [çıktı](reference-and-evaluation.txt). |
   | Windows veri sınırları | [33 başarılı](fresh-dataset-windows-tests.xml); Linux'un junction atlaması burada geçti. 32 tekrar yeniden sayılmadı, benzersiz toplama yalnız bir vaka eklendi. |
   | Backend tam kapı | [85 başarılı](quality-gate-backend.xml): 66 birim, 19 gerçek PostgreSQL entegrasyonu. Dar metadata paketindeki 84 aynı testler tekrar eklenmedi. |
   | Frontend tam kapı | [21 başarılı](quality-gate-frontend.json). Derleme, lint ve üretilen tiplerin drift kontrolü de geçti. |
   | Tam kalite kapısı | `scripts/quality-gate.sh all`, [exit 0](quality-gate-result.json), [ham çıktı](quality-gate.txt): config, migration, lint/biçim/tip, OpenAPI, frontend, yönetişim ve chart kontrolleri geçti. |
   | Güvenlik | `scripts/security-gate.sh`, [exit 2](security-gate.txt): gerekli çevrimdışı `gitleaks` yok; sonraki tarayıcılar da çalıştırılmış sayılmadı. |
   | Kalıcı tarayıcı | `scripts/e2e.sh speaker-identity`, [exit 2](permanent-browser.txt): onaylı, platforma uygun çevrimdışı paket yok. |

   Benzersiz toplam: 96 + 349 + 1 + 85 + 21 = **552**. [Sayım kaydı](test-inventory.json). Ayrı [gerçek tarayıcı raporu](browser-report.md) 11 gözlenen akış içerir; bu sayıya eklenmedi.

   Son başlangıç kontrolünden sonra tam kapı tekrar geçti: [exit 0, 61,719 saniye](quality-gate-final-result.json), [çıktı](quality-gate-final.txt). Yine 85 backend ve 21 frontend testi başarılı; tekrarlar 552 toplamını artırmaz.

3. Maddeler:

   **KUSUR**
   M1 Kısa bölgeleri doğrudan birleştirmek dönüşümlü iki kişiyi tutarlı karışım gibi kabul ediyordu; özgün bölge koruması eklendi. [Dört beklenen kırmızı vaka](recovery-guard-red.txt), [27 yeşil sınır testi](recovery-guard-green.txt).
   M2 Yeni yol HTTP/iş sonucunda izlenmiyordu; üretici, tipli adaptör, kalıcı iş JSON'u ve sözleşmeler tamamlandı. [HTTP kırmızı](recovery-http-red.txt), [metadata kırmızı/yeşil](metadata-report.md).

   **TUZAK**
   M3 Deterministik vektörler yalnız sınır testlerinde kullanıldı; bu 552 test gerçek kişi tanıma doğruluğu değildir. Model ölçümleri ayrı raporlanır.
   M4 Geliştirme sırasında 27 PCM testi Windows Python 3.12 ile de geçti; sabit çıkarım profili kanıtı Linux Python 3.13'teki 96-test koşumudur.
   M5 İlk JUnit kopyalama çağrısında MSYS mutlak konteyner yolunu dönüştürdü; mevcut wrapper'ın `sh -lc` yoluyla gerçek çıktılar okundu. Test sonucu uydurulmadı veya yeniden sayılmadı.

   **GÖZLEM**
   M6 Çıkarım testi mevcut imaj ve kilitli saf Python test araçlarıyla, ağsız ve salt okunur dosya sistemiyle çalıştı; yeni paket kurulmadı. Starlette test istemcisinin iki kullanımdan kaldırma uyarısı çıktıda korundu.
   M7 Tam kapı ayrı `_test` PostgreSQL veritabanına migration uygulayıp sildi; uygulama veritabanına migration uygulanmadı. Model ağırlıkları ve bağımlılık pinleri değişmedi.

   **AÇIK**
   M8 Güvenlik ve kalıcı tarayıcı kapılarının onaylı çevrimdışı araçları eksik; bu kontroller başarılı olarak raporlanamaz.

   **YAN-ETKİ**
   M9 Korumalı çıkarım yardımcı modülü, uçtan uca sürüm alanı, üretilen OpenAPI/tipler, veri hazırlama/değerlendirme araçları ve koruyucu testler eklendi. Geri dönüş için önceki Spark imajı tutuldu.
