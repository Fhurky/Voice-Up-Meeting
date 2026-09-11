# Koşum raporu — 2026-09-11 · Toplantı analiz ve hafıza uçlarının iki özel nginx üzerinden taşınması.

1. Sonuç: İki proxy'nin kesin uç, gövde sınırı ve başlık aktarımı doğrulandı — birim 13 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Taşıma L2; model/hafıza doğruluğu bu koşumun konusu değildir.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows Python 3.13, Docker Desktop, sabit nginx imajı ve iki ayrı geçici Linux x86_64 proxy konteyneri.

   | Komut / aşama | Sonuç |
   | --- | --- |
   | `pytest -q tests/test_spark_service_config.py -k 'meeting_proxy_routes or relay_has_fixed'` — RED | 3 başarısız; memory ucu ve analiz için ayrı 120 MiB sınırı eksikti. |
   | `pytest -q tests/test_spark_service_config.py` — GREEN | 11 başarılı; gerçek Compose parser'ı ve iki config'te kesin yollar/sınırlı ayarlar. |
   | `RUN_DOCKER_TRANSPORT=1 pytest -q tests/test_spark_transport_config.py -k nginx_live_transport_contract` | 2 başarılı, 29,863 saniye; özel bilgisayar proxy'si ve Spark relay config'i ayrı gerçek nginx süreçlerinde sınandı. |
   | `black` ve `ruff check` — iki test dosyası | Başarılı; `re.S` lint bulgusu `re.DOTALL` ile düzeltildi. |

3. Maddeler:

   **KUSUR**
   M1 Genel 51 MiB sınırı en büyük analiz örneğini engelliyordu; yalnız `/v1/meeting-chunks` için 120 MiB uygulandı. Her iki proxy'ye kesin POST `/v1/meeting-memory`, 36 MiB gövde ve 600 saniye aktarım zaman aşımı eklendi.
   M2 Özel proxy başlangıç şablonu dört upstream değişimini bekliyordu; yeni kesin uçla sayı beşe taşındı, fail-closed kontrol korundu.
   **TUZAK**
   M3 İki test upstream'i gerçek model yerine yalnız nonce HTTP yanıtı verir; authentication uygulaması çıkarım servisindedir. Buradaki kanıt iç anahtar, tenant/job başlıkları ve JSON byte aktarımıdır; model yetkilendirme veya kalite kabulü değildir.
   **GÖZLEM**
   M4 Her proxy'den 119.040.044 byte gerçek gövde geçti ve uzunluk/SHA-256 doğrulandı; 120 MiB+1 analiz, 36 MiB+1 hafıza ve 51 MiB+1 pilot uzunlukları upstream'e ulaşmadan 413 döndü.
   M5 GET/PUT hafıza isteği 405, fazla yol eki 404; `/meeting-ready` GET korundu. Gövde/anahtar loga düşmedi, upstream kapatılınca sınırlı sürede 502 görüldü ve POST kendiliğinden tekrar edilmedi.
   **AÇIK**
   M6 Gerçek Spark ARM64 imajı, Teams kaydı ve toplantılar arası doğru hafıza oluşturma bu testte çalıştırılmadı; bütün profil kapısı ana teslimde ayrıca koşulmalıdır.
   **YAN-ETKİ**
   M7 İki nginx config'i, şablon başlangıç sayacı, iki test dosyası ve plan güncellendi. Yalnız teste ait proxy'ler kaldırıldı; mevcut worker'ın ağları/ayarları değiştirilmedi. XML kanıtları Git dışı outputs altında tutulur.
