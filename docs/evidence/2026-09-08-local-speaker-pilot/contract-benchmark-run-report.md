# Koşum raporu — 2026-09-09 · tenant sözleşmesi ve GPU ölçüm aracının hazırlığı

1. Sonuç: Tenant güvenlik sözleşmesi ve ölçüm aracının yerel kontrolleri başarılı — birim 16 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Komut / kapsam | Ortam | Sonuç |
   | --- | --- | --- |
   | `pytest -q tests/unit/test_api_baseline.py` | Kilitli Linux backend konteyneri | 10 başarılı; bütün bearer korumalı işlemlerde tenant header sözleşmesi doğrulandı. |
   | `pytest tests/test_local_benchmark.py -q` | Yerel araştırma Python ortamı | 6 başarılı; percentile hesabı, saat dilimi ve yalnız loopback hedef kısıtı. |
   | `scripts/export-openapi.sh` ve `--check` | Yerel Compose | Sözleşme yeniden üretildi; drift kontrolü başarılı. |
   | `scripts/generate-types.sh` ve `--check` | Node 22 konteyneri | Tipler yeniden üretildi; drift kontrolü başarılı. |
   | `npm run build` | Node 22 konteyneri | TypeScript ve Vite üretim build başarılı. |
   | Ölçüm aracı `--help` / Black / isort | Yerel Python | Başarılı; gerçek GPU ölçümü bu hazırlık sırasında çalıştırılmadı. |

3. Maddeler:

   **KUSUR**

   M1 OpenAPI export tenant zorunluluğunu yalnız `/auth/me` için yazıyordu; yeni başarısız regresyon testiyle gözlendi, bütün bearer korumalı işlemlere genellendi ve test geçti.

   **TUZAK**

   M2 Ölçüm aracı bir ısınma işini dışlar, ardından 20 tek denemeli CUDA işini sayar; yeniden denenmiş veya CPU sonucu ölçüm olarak kabul edilmez.

   M3 NVIDIA bellek alanı örneklenen toplam cihaz kullanımını içerir; başka süreçleri kapsar ve PyTorch allocator tepe belleği olarak adlandırılmaz.

   **GÖZLEM**

   M4 Önceki tam kalite kapısının 53 backend ve 21 frontend başarısı ayrı rapordadır; bu değişiklik sonrası kapsam export/test/aracı ve üretilen sözleşmelerdir.

   **AÇIK**

   M5 Gerçek 4060 ölçümü model hazır olduktan sonra çalıştırılmalıdır; bu rapor gecikme veya tanıma kalitesi sonucu içermez.

   **YAN-ETKİ**

   M6 `scripts/benchmark-local-pilot.py` ve altı testi eklendi; OpenAPI ve TypeScript sözleşmeleri mevcut üreticilerle yenilendi.
