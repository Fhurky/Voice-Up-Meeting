# Koşum raporu — 2026-09-09 · yerel konuşmacı pilotunun backend ve tam kalite kapısı

1. Sonuç: `kt-vibecoding-python-web-v2` tam kalite kapısı başarılı — birim 61 başarılı / PostgreSQL entegrasyon 13 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Komut / kapsam | Ortam | Gözlenen sonuç |
   | --- | --- | --- |
   | `scripts/quality-gate.sh all` | Docker Linux; kilitli Python 3.13, PostgreSQL 17 ve pgvector 0.8.6; Node 22 | Son çalışma exit 0; 53 pytest ve 21 Vitest başarılı. |
   | Backend pytest | 40 birim + 13 gerçek PostgreSQL/HTTP/dosya entegrasyonu | 53 başarılı, 0 atlanan; ham JUnit çıktısı bu dizindedir. |
   | Backend statik | Ruff, Black, isort, mypy | Başarılı; 54 uygulama kaynak dosyası tip kontrolünden geçti. |
   | Alembic | Kapının oluşturduğu benzersiz `_test` veritabanı | Platform ve `9486b1bc12a9` migrasyonları uygulandı; desired-state farkı yok, head doğrulandı; veritabanı düşürüldü. |
   | API ve istemci sözleşmesi | Çevrimdışı OpenAPI export ve üretilen TypeScript tipleri | İki drift kontrolü başarılı. |
   | Frontend | ESLint, TypeScript, Vite, Vitest | Üretim build ve 21 test başarılı. |
   | Konfigürasyon / bağımlılık / yönetişim / chart | Yerel CLI | 29 typed ayar; 107 kabul kaydı; 93 yönetişim ve 4 inert projeksiyon; 46 kaynak × 2 fixture başarılı. |
   | Önceki tam kapı denemeleri | Aynı yerel Compose | İlk deneme Windows dosya modlarında, ikinci deneme frontend kullanılmayan import kontrolünde durdu; her iki geçici veritabanı temizlendi. |
   | Hata öncesi testler | Python 3.13 yerel geliştirme ortamı | CRLF parola testinde yanlış son karakter ve chunked yükleme testinde 400/413 farkı gözlendi; düzeltmelerden sonra tam kapıda ikisi de başarılı. |

3. Maddeler:

   **KUSUR**

   M1 Windows CRLF girdisi bootstrap parolasına fazladan karakter ekliyordu; `app/scripts/create_super_admin.py` ve `tests/unit/test_bootstrap_input.py` ile düzeltildi.

   M2 FastAPI ara katmanında boyut hatası 400'e dönüşebiliyordu; sınırlı ve her çıkışta kapanan geçici spool ile 413 korundu, `test_chunked_multipart_limit_returns_typed_413` geçti.

   M3 Saklama sorgusunda ilk 100 referanslı kayıt temizliği engelleyebiliyordu; aktif referanslar SQL'de LIMIT öncesi dışlanıyor, 101 kaynaklı entegrasyon testi geçti.

   M4 Alembic'in varsayılan adlandırması bileşik unique constraint adlarını çakıştırdı; uygulanmadan önce authority ve üretilen migrasyon adları açıkça düzeltildi.

   **TUZAK**

   M5 Windows bind mount bütün Python dosyalarını executable gösteriyor; kapı aynı içeriğin geçici kopyasında dosya modlarını normalize ediyor, kaynak dosyalar chmod ile değiştirilmedi.

   M6 Host geliştirme venv'i Windows için authority dosyalarından kuruldu; teslim kanıtı Linux hash-lock bağımlılıklarını kullanan son tam kapıdır.

   **GÖZLEM**

   M7 Gerçek PostgreSQL testleri idempotency, tenant/model izolasyonu, iki sahiplenme arasında fencing, yanlış kişiyi ekleme reddi, silme yarışı, 20 örnek sınırı ve saklama yaşam döngüsünü kapsar.

   M8 PostgreSQL testleri sabit fixture vektörleriyle yazılım davranışını ölçer; bunlar ECAPA doğruluğu veya GPU performansı kanıtı değildir.

   **AÇIK**

   M9 Bu rapor GPU/browser/gerçek kişi deneyi sonucu üretmez; bu kanıtlar ilgili çıkarım ve tarayıcı raporlarında ayrıca değerlendirilir.

   M10 Beş kişiden farklı oturum kayıtları ve kayıtsız kişi sorguları olmadan kabuldeki tanıma kalitesi ölçülemez; bu veri deneyi tamamlandı sayılmadı.

   **YAN-ETKİ**

   M11 Yerel uygulama veritabanına eklemeli migrasyon ve dört izin kaydı uygulandı; testler yalnız kapıya ait geçici `_test` veritabanlarında çalıştı.

   M12 Testler geçici dizinlerde uygulamaya ait ses kopyaları ve fixture metadata oluşturdu; kullanıcı kayıtlarına veya başka uygulamanın veritabanına erişmedi.
